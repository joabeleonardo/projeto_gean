"""Plano de mensalista: adesão, cotas, vagas premium, capacidade, cobranças mensais e modo de entrada.

Dois tipos de plano:
  * Rotativo — o cliente tem N cotas e usa qualquer vaga de mensalista que estiver livre;
  * Premium  — o cliente reserva UMA vaga exclusiva (mais cara): só os veículos dele entram nela.
"""
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlmodel import Session, select, col
from sqlalchemy import func
from sqlalchemy.exc import OperationalError, IntegrityError

from controllers.auditoria import aplicar_auditoria
from entidades.entidades import (
    Cliente, Mensalidade, Movimentacao, Pagamento, Preco, Vaga, Veiculo,
    CategoriaEnum, PlanoEnum, StatusPagamentoEnum, TipoCobrancaEnum, TipoPagamentoEnum, TipoVagaEnum,
)
from modelos.schemas import MensalidadeEntrada
from servicos.caixa import calcular_troco, e_dinheiro
from servicos.datas import agora_local, hoje_local
from servicos.mensalidade import cabe_no_limite, plano_vigente, vencimentos_ate

CATEGORIAS = ("Carro", "Moto")


def _v(x) -> str:
    return str(getattr(x, "value", x))


def _premium(p: Mensalidade) -> bool:
    return _v(p.tipo_plano) == "Premium"


# ------------------------------------------------------------------ consultas
def _preco_mensal(db: Session, categoria: str, tipo_plano: str = "Rotativo") -> Optional[float]:
    tipo = TipoCobrancaEnum.Premium if tipo_plano == "Premium" else TipoCobrancaEnum.Mensalista
    p = db.exec(select(Preco).where(Preco.tipo_cobranca == tipo, Preco.categoria == CategoriaEnum(categoria))).first()
    return p.valor if p is not None and p.valor > 0 else None


def vagas_mensalista(db: Session, categoria: str) -> int:
    """Vagas de mensalista ROTATIVAS ativas da categoria (vaga inativa não conta)."""
    return int(db.exec(select(func.count()).select_from(Vaga).where(
        Vaga.tipo == TipoVagaEnum.Mensalista, Vaga.categoria == CategoriaEnum(categoria),
        Vaga.ativa == True,  # noqa: E712
    )).one() or 0)


def planos_ativos(db: Session, categoria: Optional[str] = None, id_cliente: Optional[int] = None) -> list[Mensalidade]:
    """Planos não cancelados e não encerrados (inclui os que ainda vão começar)."""
    hoje = hoje_local()
    stmt = select(Mensalidade).where(Mensalidade.ativa == True)  # noqa: E712
    if categoria:
        stmt = stmt.where(Mensalidade.categoria == CategoriaEnum(categoria))
    if id_cliente is not None:
        stmt = stmt.where(Mensalidade.id_cliente == id_cliente)
    return [p for p in db.exec(stmt).all() if p.data_fim is None or p.data_fim >= hoje]


def cotas_contratadas(db: Session, categoria: str, excluir_id: Optional[int] = None) -> int:
    """Cotas dos planos ROTATIVOS (plano premium não usa cota: tem vaga própria)."""
    return sum(p.cotas for p in planos_ativos(db, categoria) if p.id != excluir_id and not _premium(p))


def _vagas_premium_do_cliente(db: Session, id_cliente: int, categoria: str) -> list[Vaga]:
    vagas = []
    for p in planos_ativos(db, categoria, id_cliente):
        if _premium(p) and p.id_vaga:
            v = db.get(Vaga, p.id_vaga)
            if v is not None and v.ativa:
                vagas.append(v)
    return vagas


def vagas_premium_livres(db: Session, categoria: str) -> list[Vaga]:
    """Vagas premium ativas da categoria que ainda não foram reservadas por nenhum plano."""
    reservadas = {p.id_vaga for p in planos_ativos(db, categoria) if _premium(p) and p.id_vaga}
    vagas = db.exec(select(Vaga).where(
        Vaga.tipo == TipoVagaEnum.Premium, Vaga.categoria == CategoriaEnum(categoria), Vaga.ativa == True,  # noqa: E712
    ).order_by(Vaga.codigo_vaga)).all()
    return [v for v in vagas if v.id not in reservadas]


def placas_em_uso(db: Session, id_cliente: int, categoria: str, tipo: str = "Mensalista", ids_vagas: Optional[list] = None) -> list[str]:
    """Placas do cliente que estão no pátio ocupando vaga do tipo dado (uma cota/vaga cada)."""
    stmt = (
        select(Veiculo.placa)
        .join(Movimentacao, Movimentacao.id_veiculo == Veiculo.id)
        .join(Vaga, Movimentacao.id_vaga == Vaga.id)
        .where(
            Veiculo.id_cliente == id_cliente,
            col(Movimentacao.data_saida).is_(None),
            Vaga.tipo == TipoVagaEnum(tipo),
            Vaga.categoria == CategoriaEnum(categoria),
        )
    )
    if ids_vagas is not None:
        stmt = stmt.where(col(Vaga.id).in_(ids_vagas or [-1]))
    return list(db.exec(stmt).all())


# ------------------------------------------------------------------- limites
def _checar_capacidade(db: Session, categoria: str, novas: int, excluir_id: Optional[int] = None) -> None:
    vagas = vagas_mensalista(db, categoria)
    contratadas = cotas_contratadas(db, categoria, excluir_id)
    if not cabe_no_limite(vagas, contratadas, novas):
        livres = max(0, vagas - contratadas)
        raise ValueError(
            f"Limite de vagas de mensalista ({categoria.lower()}) atingido: {vagas} vaga(s) para {contratadas} cota(s) "
            f"já contratada(s), restam {livres}. Cadastre mais vagas de mensalista ou ajuste os planos."
        )


def checar_remocao_de_vaga_mensalista(db: Session, categoria: str) -> None:
    """Chamado antes de inativar, excluir ou trocar o tipo de uma vaga de mensalista rotativa ativa."""
    vagas = vagas_mensalista(db, categoria)
    contratadas = cotas_contratadas(db, categoria)
    if vagas - 1 < contratadas:
        raise ValueError(
            f"Há {contratadas} cota(s) de mensalista ({categoria.lower()}) contratada(s); sem esta vaga restariam "
            f"{vagas - 1}. Reduza ou cancele planos antes."
        )


def checar_vaga_premium_sem_plano(db: Session, vaga: Vaga) -> None:
    """Vaga premium reservada por um plano não pode ser inativada, excluída nem ter tipo/categoria alterados."""
    for p in planos_ativos(db, None):
        if _premium(p) and p.id_vaga == vaga.id:
            cliente = db.get(Cliente, p.id_cliente)
            raise ValueError(
                f"A vaga premium {vaga.codigo_vaga} está reservada para {cliente.nome if cliente else 'um cliente'}. "
                "Cancele o plano premium antes."
            )


def capacidade(db: Session) -> list[dict]:
    itens = []
    for cat in CATEGORIAS:
        vagas, contratadas = vagas_mensalista(db, cat), cotas_contratadas(db, cat)
        todas_premium = int(db.exec(select(func.count()).select_from(Vaga).where(
            Vaga.tipo == TipoVagaEnum.Premium, Vaga.categoria == CategoriaEnum(cat), Vaga.ativa == True,  # noqa: E712
        )).one() or 0)
        livres_premium = len(vagas_premium_livres(db, cat))
        itens.append({
            "categoria": cat, "vagas_mensalista": vagas, "cotas_contratadas": contratadas,
            "cotas_livres": max(0, vagas - contratadas),
            "vagas_premium": todas_premium, "premium_atribuidas": todas_premium - livres_premium,
            "premium_livres": livres_premium,
        })
    return itens


def listar_vagas_premium(db: Session) -> list[dict]:
    """Vagas premium, com o cliente que reservou (se houver)."""
    donos = {p.id_vaga: p for p in planos_ativos(db) if _premium(p) and p.id_vaga}
    saida = []
    for v in db.exec(select(Vaga).where(Vaga.tipo == TipoVagaEnum.Premium).order_by(Vaga.codigo_vaga)).all():
        plano = donos.get(v.id)
        cliente = db.get(Cliente, plano.id_cliente) if plano else None
        saida.append({
            "id": v.id, "codigo_vaga": v.codigo_vaga, "categoria": _v(v.categoria), "ativa": v.ativa,
            "status": _v(v.status), "id_plano": plano.id if plano else None,
            "reservada_para": cliente.nome if cliente else None,
        })
    return saida


# ------------------------------------------------------------ modo de entrada
def modo_de_entrada(db: Session, veiculo: Veiculo) -> dict:
    """Identifica automaticamente como o veículo entra: premium (vaga exclusiva), mensalista (usa uma cota)
    ou horista."""
    categoria = _v(veiculo.tipo_veiculo)
    hoje = hoje_local()
    cliente = db.get(Cliente, veiculo.id_cliente)
    planos = planos_ativos(db, categoria, veiculo.id_cliente)
    vigentes = [p for p in planos if plano_vigente(p.data_inicio, p.data_fim, p.ativa, hoje)]
    futuros = sorted(p.data_inicio for p in planos if p.data_inicio > hoje)
    base = {
        "cliente_nome": cliente.nome if cliente else None, "categoria": categoria,
        "inicio_futuro": futuros[0] if futuros else None, "vaga_premium": None,
    }
    rotativos = [p for p in vigentes if not _premium(p)]
    vagas_premium = [v for v in _vagas_premium_do_cliente(db, veiculo.id_cliente, categoria)
                     if any(p.id_vaga == v.id for p in vigentes)]
    cotas_rot = sum(p.cotas for p in rotativos)
    total_cotas = cotas_rot + len(vagas_premium)

    if total_cotas == 0:
        msg = (f"Plano de mensalista começa em {futuros[0].strftime('%d/%m/%Y')}: entrada como horista."
               if futuros else "Cliente horista.")
        return {**base, "modo": "Horista", "tem_plano": False, "cotas": 0, "em_uso": 0,
                "esgotado": False, "placas_em_uso": [], "mensagem": msg}

    usadas_rot = placas_em_uso(db, veiculo.id_cliente, categoria, "Mensalista")
    usadas_prem = placas_em_uso(db, veiculo.id_cliente, categoria, "Premium", [v.id for v in vagas_premium])
    usadas = usadas_prem + usadas_rot
    livre_premium = next((v for v in vagas_premium if _v(v.status) == "Livre"), None)

    if livre_premium is not None:
        msg = f"Plano Premium: vaga exclusiva {livre_premium.codigo_vaga}."
        return {**base, "modo": "Premium", "tem_plano": True, "cotas": total_cotas, "em_uso": len(usadas),
                "esgotado": False, "placas_em_uso": usadas, "mensagem": msg,
                "vaga_premium": {"id": livre_premium.id, "codigo": livre_premium.codigo_vaga}}
    if len(usadas_rot) < cotas_rot:
        return {**base, "modo": "Mensalista", "tem_plano": True, "cotas": total_cotas, "em_uso": len(usadas),
                "esgotado": False, "placas_em_uso": usadas,
                "mensagem": f"Mensalista: cota {len(usadas_rot) + 1} de {cotas_rot}."}
    return {**base, "modo": "Premium" if vagas_premium and not rotativos else "Mensalista", "tem_plano": True,
            "cotas": total_cotas, "em_uso": len(usadas), "esgotado": True, "placas_em_uso": usadas,
            "mensagem": f"Mensalista: todas as {total_cotas} cota(s)/vaga(s) em uso ({', '.join(usadas)})."}


# ------------------------------------------------------------ adesão e gestão
def criar_plano_e_cobranca(db: Session, id_cliente: int, entrada: MensalidadeEntrada, usuario) -> Mensalidade:
    """Cria o plano e a primeira cobrança (vencimento na data da adesão). Não faz commit."""
    if db.get(Cliente, id_cliente) is None:
        raise KeyError(f"Cliente de ID {id_cliente} não encontrado.")
    hoje = hoje_local()
    inicio = entrada.data_inicio or hoje
    if inicio < hoje:
        raise ValueError("A data de adesão não pode ser anterior a hoje.")
    categoria = _v(entrada.categoria)
    tipo_plano = _v(entrada.tipo_plano)
    cotas = entrada.cotas
    id_vaga = None

    if tipo_plano == "Premium":
        vaga = db.get(Vaga, entrada.id_vaga) if entrada.id_vaga else None
        if vaga is None:
            raise KeyError("Vaga premium não encontrada.")
        if _v(vaga.tipo) != "Premium" or _v(vaga.categoria) != categoria or not vaga.ativa:
            raise ValueError(f"Escolha uma vaga premium ativa de {categoria.lower()}.")
        if vaga.id not in {v.id for v in vagas_premium_livres(db, categoria)}:
            raise ValueError(f"A vaga premium {vaga.codigo_vaga} já está reservada para outro cliente.")
        id_vaga, cotas = vaga.id, 1
    else:
        if [p for p in planos_ativos(db, categoria, id_cliente) if not _premium(p)]:
            raise ValueError(f"Este cliente já possui plano de mensalista rotativo ativo ({categoria.lower()}). Altere as cotas do plano existente.")
        _checar_capacidade(db, categoria, cotas)

    preco = _preco_mensal(db, categoria, tipo_plano)
    if preco is None:
        nome_preco = "premium" if tipo_plano == "Premium" else "mensal"
        raise ValueError(f"O preço {nome_preco} de {categoria.lower()} ainda não foi definido. Peça a um administrador para cadastrá-lo.")
    valor = round(preco * cotas, 2)
    pago = _v(entrada.status_primeira_cobranca) == "Pago"
    if pago and not entrada.forma_pagamento:
        raise ValueError("Informe a forma de pagamento da primeira mensalidade.")
    recebido = troco = None
    if pago and e_dinheiro(entrada.forma_pagamento):
        troco = calcular_troco(valor, entrada.valor_recebido)
        recebido = round(entrada.valor_recebido, 2)

    plano = Mensalidade(id_cliente=id_cliente, categoria=CategoriaEnum(categoria), cotas=cotas,
                        tipo_plano=PlanoEnum(tipo_plano), id_vaga=id_vaga, data_inicio=inicio)
    db.add(plano)
    db.flush()
    db.add(Pagamento(
        id_cliente=id_cliente, tipo_cobranca=TipoPagamentoEnum.Mensal,
        valor_total=valor, data_vencimento=inicio,
        data_pagamento=agora_local() if pago else None,
        status=StatusPagamentoEnum.Pago if pago else StatusPagamentoEnum.Pendente,
        forma_pagamento=_v(entrada.forma_pagamento) if pago else None,
        valor_recebido=recebido, troco=troco,
        id_usuario_recebimento=usuario.id if pago else None,
    ))
    db.flush()
    return plano


def aderir(dados, usuario, db: Session) -> Mensalidade:
    try:
        aplicar_auditoria(db, usuario.id, usuario.nome)
        plano = criar_plano_e_cobranca(db, dados.id_cliente, dados, usuario)
        db.commit()
        db.refresh(plano)
        return plano
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao registrar o plano.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


def _detalhar(db: Session, p: Mensalidade, hoje: date) -> dict:
    cliente = db.get(Cliente, p.id_cliente)
    categoria = _v(p.categoria)
    preco = _preco_mensal(db, categoria, _v(p.tipo_plano))
    vaga = db.get(Vaga, p.id_vaga) if p.id_vaga else None
    if _premium(p):
        em_uso = 1 if vaga is not None and _v(vaga.status) == "Ocupada" else 0
    else:
        em_uso = len(placas_em_uso(db, p.id_cliente, categoria, "Mensalista"))
    return {
        "id": p.id, "id_cliente": p.id_cliente, "categoria": categoria, "cotas": p.cotas,
        "tipo_plano": _v(p.tipo_plano), "id_vaga": p.id_vaga, "codigo_vaga": vaga.codigo_vaga if vaga else None,
        "data_inicio": p.data_inicio, "data_fim": p.data_fim, "ativa": p.ativa,
        "cliente_nome": cliente.nome if cliente else None,
        "valor_mensal": round(preco * p.cotas, 2) if preco else None,
        "em_uso": em_uso, "vigente": plano_vigente(p.data_inicio, p.data_fim, p.ativa, hoje),
    }


def listar_ativas(db: Session, id_cliente: Optional[int] = None) -> list[dict]:
    try:
        hoje = hoje_local()
        return [_detalhar(db, p, hoje) for p in planos_ativos(db, None, id_cliente)]
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def alterar_cotas(id_plano: int, cotas: int, usuario, db: Session) -> Mensalidade:
    try:
        plano = db.get(Mensalidade, id_plano)
        if not plano:
            raise KeyError(f"Plano de ID {id_plano} não encontrado.")
        if not plano.ativa:
            raise ValueError("Este plano foi cancelado.")
        if _premium(plano):
            raise ValueError("O plano premium tem uma única vaga exclusiva e não possui cotas.")
        categoria = _v(plano.categoria)
        _checar_capacidade(db, categoria, cotas, excluir_id=plano.id)
        usadas = placas_em_uso(db, plano.id_cliente, categoria, "Mensalista")
        if len(usadas) > cotas:
            raise ValueError(f"Há {len(usadas)} veículo(s) deste cliente em vaga de mensalista no pátio ({', '.join(usadas)}). Registre a saída antes de reduzir as cotas.")
        aplicar_auditoria(db, usuario.id, usuario.nome)
        plano.cotas = cotas
        db.add(plano)
        db.commit()
        db.refresh(plano)
        return plano
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


def cancelar(id_plano: int, usuario, db: Session) -> Mensalidade:
    try:
        plano = db.get(Mensalidade, id_plano)
        if not plano:
            raise KeyError(f"Plano de ID {id_plano} não encontrado.")
        if not plano.ativa:
            raise ValueError("Este plano já foi cancelado.")
        if _premium(plano) and plano.id_vaga:
            vaga = db.get(Vaga, plano.id_vaga)
            if vaga is not None and _v(vaga.status) == "Ocupada":
                raise ValueError(f"A vaga premium {vaga.codigo_vaga} está ocupada. Registre a saída antes de cancelar o plano.")
        aplicar_auditoria(db, usuario.id, usuario.nome)
        plano.ativa = False
        plano.data_fim = hoje_local()
        db.add(plano)
        db.commit()
        db.refresh(plano)
        return plano
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


# ------------------------------------------------------- cobranças mensais
def gerar_cobrancas(db: Session) -> dict:
    """Cria (como PENDENTES) as mensalidades cujo vencimento já chegou e que ainda não existem.
    É idempotente: rodar de novo não duplica nada."""
    try:
        hoje = hoje_local()
        necessarias = defaultdict(list)
        for p in planos_ativos(db):
            for d in vencimentos_ate(p.data_inicio, hoje, p.data_fim):
                necessarias[(p.id_cliente, d)].append(p)
        criadas = sem_preco = 0
        for (id_cliente, venc), planos in necessarias.items():
            existentes = int(db.exec(select(func.count()).select_from(Pagamento).where(
                Pagamento.id_cliente == id_cliente, Pagamento.tipo_cobranca == TipoPagamentoEnum.Mensal,
                Pagamento.data_vencimento == venc,
            )).one() or 0)
            faltam = len(planos) - existentes
            for p in (planos[len(planos) - faltam:] if faltam > 0 else []):
                preco = _preco_mensal(db, _v(p.categoria), _v(p.tipo_plano))
                if preco is None:
                    sem_preco += 1
                    continue
                db.add(Pagamento(
                    id_cliente=id_cliente, tipo_cobranca=TipoPagamentoEnum.Mensal,
                    valor_total=round(preco * p.cotas, 2), data_vencimento=venc,
                    status=StatusPagamentoEnum.Pendente,
                ))
                criadas += 1
        if criadas:
            aplicar_auditoria(db, 0, "Sistema (cobranças mensais automáticas)")
            db.commit()
        return {"criadas": criadas, "sem_preco": sem_preco}
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


_ultima_geracao: Optional[date] = None


def gerar_cobrancas_se_necessario(db: Session) -> Optional[dict]:
    """Roda a geração no máximo uma vez por dia (por processo). Idempotente."""
    global _ultima_geracao
    hoje = hoje_local()
    if _ultima_geracao == hoje:
        return None
    resultado = gerar_cobrancas(db)
    _ultima_geracao = hoje
    return resultado
