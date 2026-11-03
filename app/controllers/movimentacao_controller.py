from datetime import datetime, date, time, timedelta
from typing import Optional

from sqlmodel import Session, select, col
from sqlalchemy import func
from sqlalchemy.exc import OperationalError, IntegrityError

from controllers.auditoria import aplicar_auditoria, registrar_evento_auditoria
from controllers.inadimplencia_controller import situacao_do_cliente
from controllers.mensalidade_controller import modo_de_entrada
from controllers.usuarios_controller import autorizar_liberacao
from entidades.entidades import (
    Movimentacao, Vaga, Veiculo, Cliente, Preco, Pagamento, Usuario,
    StatusVagaEnum, CategoriaEnum, TipoCobrancaEnum, TipoPagamentoEnum, StatusPagamentoEnum,
)
from modelos.schemas import MovimentacaoEntradaCreate, MovimentacaoSaidaUpdate
from servicos.caixa import calcular_troco, e_dinheiro
from servicos.datas import agora_local
from servicos.excecoes import CotasEsgotadas, EntradaBloqueada
from servicos.limite_tentativas import limite_liberacao
from servicos.tarifa import calcular_valor_hora, minutos_permanencia


def _v(x) -> str:
    return str(getattr(x, "value", x))


def _preco_vigente(db: Session, tipo: TipoCobrancaEnum, categoria) -> Optional[Preco]:
    return db.exec(
        select(Preco).where(Preco.tipo_cobranca == tipo, Preco.categoria == CategoriaEnum(_v(categoria)))
    ).first()


def _eh_horista(vaga: Vaga) -> bool:
    return _v(vaga.tipo) == "Horista"


def _checar_inadimplencia(mov_in: MovimentacaoEntradaCreate, veiculo: Veiculo, db: Session):
    """Barra a entrada de cliente inadimplente, a menos que um administrador
    libere com o código dele. Devolve o administrador que liberou (ou None)."""
    situacao = situacao_do_cliente(db, veiculo.id_cliente)
    if not situacao:
        return None
    cliente = db.get(Cliente, veiculo.id_cliente)
    nome = cliente.nome if cliente else "Cliente"
    if not mov_in.codigo_liberacao:
        raise EntradaBloqueada(nome, situacao["dias_atraso"], situacao["valor_em_aberto"], situacao["cobrancas_vencidas"])

    chave = mov_in.id_usuario_logado
    espera = limite_liberacao.segundos_bloqueado(chave)
    if espera:
        raise ValueError(f"Muitas tentativas com código incorreto. Aguarde {max(1, espera // 60)} min e tente novamente.")
    administrador = autorizar_liberacao(mov_in.codigo_liberacao, db)
    if administrador is None:
        limite_liberacao.registrar_falha(chave)
        raise ValueError("Código do administrador incorreto.")
    limite_liberacao.limpar(chave)
    return administrador, situacao


def registrar_entrada(mov_in: MovimentacaoEntradaCreate, db: Session) -> Movimentacao:
    try:
        aplicar_auditoria(db, mov_in.id_usuario_logado, mov_in.nome_usuario_logado)

        veiculo = db.get(Veiculo, mov_in.id_veiculo)
        if not veiculo:
            raise KeyError(f"Veículo de ID {mov_in.id_veiculo} não encontrado.")

        liberacao = _checar_inadimplencia(mov_in, veiculo, db)

        ja_dentro = db.exec(
            select(Movimentacao).where(
                Movimentacao.id_veiculo == mov_in.id_veiculo,
                col(Movimentacao.data_saida).is_(None),
            )
        ).first()
        if ja_dentro:
            raise ValueError(f"O veículo {veiculo.placa} já está no pátio. Registre a saída antes de uma nova entrada.")

        # Identifica automaticamente se o cliente entra como mensalista (usa uma cota) ou horista.
        modo = modo_de_entrada(db, veiculo)
        if modo["tem_plano"] and modo["esgotado"] and not mov_in.como_horista:
            raise CotasEsgotadas(modo["cliente_nome"] or "Cliente", modo["cotas"], modo["placas_em_uso"])
        if modo["tem_plano"] and not modo["esgotado"]:
            tipo_esperado = "Premium" if modo["modo"] == "Premium" else "Mensalista"
        else:
            tipo_esperado = "Horista"

        # with_for_update trava a linha da vaga: evita dois operadores ocuparem a mesma vaga
        vaga = db.exec(select(Vaga).where(Vaga.id == mov_in.id_vaga).with_for_update()).first()
        if not vaga:
            raise KeyError(f"Vaga de ID {mov_in.id_vaga} não encontrada.")
        if not vaga.ativa:
            raise ValueError(f"A vaga {vaga.codigo_vaga} está inativa (indisponível). Escolha outra vaga.")
        if vaga.status == StatusVagaEnum.Ocupada:
            raise ValueError(f"A vaga {vaga.codigo_vaga} já está ocupada.")
        if _v(vaga.categoria) != _v(veiculo.tipo_veiculo):
            raise ValueError(
                f"A vaga {vaga.codigo_vaga} é de {_v(vaga.categoria).lower()} e o veículo {veiculo.placa} é {_v(veiculo.tipo_veiculo).lower()}. Escolha uma vaga compatível."
            )

        if tipo_esperado == "Premium":
            if vaga.id != modo["vaga_premium"]["id"]:
                raise ValueError(f"Este cliente tem plano Premium: use a vaga exclusiva {modo['vaga_premium']['codigo']}.")
        elif _v(vaga.tipo) == "Premium":
            raise ValueError(f"A vaga {vaga.codigo_vaga} é premium e exclusiva do cliente que a reservou.")
        elif _v(vaga.tipo) != tipo_esperado:
            raise ValueError(
                "Este cliente é mensalista: use uma vaga de mensalista."
                if tipo_esperado == "Mensalista"
                else "Esta entrada é como horista: use uma vaga de horista."
            )

        nova = Movimentacao(
            id_veiculo=mov_in.id_veiculo,
            id_vaga=mov_in.id_vaga,
            data_entrada=agora_local(),
            id_usuario_entrada=mov_in.id_usuario_entrada,
        )
        if liberacao:
            administrador, situacao = liberacao
            nova.id_usuario_liberacao = administrador.id
            nova.obs_liberacao = (
                f"cliente inadimplente há {situacao['dias_atraso']} dia(s), R$ {situacao['valor_em_aberto']:.2f} em aberto"
            )
        vaga.status = StatusVagaEnum.Ocupada
        db.add(vaga)
        db.add(nova)
        db.flush()

        if liberacao:
            administrador, situacao = liberacao
            registrar_evento_auditoria(
                db, "tb_movimentacao", "INSERT", nova.id,
                f"Entrada de {veiculo.placa} liberada por código do administrador {administrador.nome} "
                f"(ID {administrador.id}); cliente inadimplente há {situacao['dias_atraso']} dia(s), "
                f"R$ {situacao['valor_em_aberto']:.2f} em aberto.",
                f"ID: {mov_in.id_usuario_logado} - {mov_in.nome_usuario_logado}",
            )
        db.commit()
        db.refresh(nova)
        return nova
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao registrar entrada (Veículo ou Vaga inválidos).") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


def buscar_movimentacoes(db: Session) -> list[Movimentacao]:
    try:
        return db.exec(select(Movimentacao)).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def buscar_movimentacao_por_id(id_movimentacao: int, db: Session) -> Movimentacao:
    try:
        mov = db.get(Movimentacao, id_movimentacao)
        if not mov:
            raise KeyError(f"Movimentação de ID {id_movimentacao} não encontrada.")
        return mov
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def _valor_da_saida(mov: Movimentacao, vaga: Optional[Vaga], agora: datetime, db: Session):
    """Devolve (valor, preço usado). Vaga de mensalista não cobra por hora (None).
    O preço (hora, valor mínimo e tempo mínimo) depende da categoria da vaga (carro ou moto)."""
    if vaga is None or not _eh_horista(vaga):
        return None, None
    categoria = _v(vaga.categoria)
    preco = _preco_vigente(db, TipoCobrancaEnum.Horista, categoria)
    if preco is None or preco.valor <= 0:
        raise ValueError(
            f"O preço por hora de {categoria.lower()} ainda não foi definido. Peça a um administrador para cadastrá-lo."
        )
    valor = calcular_valor_hora(
        mov.data_entrada, agora, preco.valor, preco.valor_minimo or 0.0, preco.tempo_minimo_minutos or 0
    )
    return valor, preco


def previa_saida(id_movimentacao: int, db: Session) -> dict:
    """Mostra quanto será cobrado se o veículo sair agora (não grava nada)."""
    try:
        mov = buscar_movimentacao_por_id(id_movimentacao, db)
        if mov.data_saida is not None:
            raise ValueError("Esta movimentação já possui registro de saída.")
        agora = agora_local()
        vaga = db.get(Vaga, mov.id_vaga)
        veiculo = db.get(Veiculo, mov.id_veiculo)
        valor, preco = _valor_da_saida(mov, vaga, agora, db)
        return {
            "id": mov.id,
            "placa": veiculo.placa if veiculo else "-",
            "codigo_vaga": vaga.codigo_vaga if vaga else "-",
            "tipo_vaga": _v(vaga.tipo) if vaga else "-",
            "categoria": _v(vaga.categoria) if vaga else "Carro",
            "data_entrada": mov.data_entrada,
            "permanencia_minutos": minutos_permanencia(mov.data_entrada, agora),
            "valor_total": valor,
            "valor_hora": preco.valor if preco else None,
            "valor_minimo": (preco.valor_minimo or 0.0) if preco else 0.0,
            "tempo_minimo_minutos": (preco.tempo_minimo_minutos or 0) if preco else 0,
        }
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def registrar_saida(id_movimentacao: int, saida_in: MovimentacaoSaidaUpdate, db: Session) -> dict:
    """Registra a saída, libera a vaga e, em vaga de horista, calcula o valor e
    registra o pagamento (com a forma de pagamento) automaticamente."""
    try:
        mov = db.get(Movimentacao, id_movimentacao)
        if not mov:
            raise KeyError(f"Movimentação de ID {id_movimentacao} não encontrada.")
        if mov.data_saida is not None:
            raise ValueError("Esta movimentação já possui registro de saída.")

        aplicar_auditoria(db, saida_in.id_usuario_logado, saida_in.nome_usuario_logado)

        agora = agora_local()
        vaga = db.get(Vaga, mov.id_vaga)
        valor, _ = _valor_da_saida(mov, vaga, agora, db)  # antes de alterar qualquer coisa
        if valor and not saida_in.forma_pagamento:
            raise ValueError("Informe a forma de pagamento (dinheiro, Pix, cartão...).")
        recebido = troco = None
        if valor and e_dinheiro(saida_in.forma_pagamento):
            troco = calcular_troco(valor, saida_in.valor_recebido)       # recusa valor recebido menor que o total
            recebido = round(saida_in.valor_recebido, 2)

        mov.data_saida = agora
        mov.id_usuario_saida = saida_in.id_usuario_saida
        db.add(mov)
        if vaga:
            vaga.status = StatusVagaEnum.Livre
            db.add(vaga)
        if valor:
            db.add(Pagamento(
                id_movimentacao=mov.id,
                tipo_cobranca=TipoPagamentoEnum.Hora,
                valor_total=valor,
                data_pagamento=agora,
                status=StatusPagamentoEnum.Pago,
                forma_pagamento=_v(saida_in.forma_pagamento),
                valor_recebido=recebido, troco=troco,
                id_usuario_recebimento=saida_in.id_usuario_saida,
            ))
        db.commit()
        db.refresh(mov)
        resposta = mov.model_dump()
        resposta["permanencia_minutos"] = minutos_permanencia(mov.data_entrada, agora)
        resposta["valor_total"] = valor
        resposta["troco"] = troco
        return resposta
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao registrar a saída.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


def listar_no_patio(db: Session) -> list[dict]:
    """Veículos que estão no pátio agora, já com placa, cliente e vaga."""
    try:
        agora = agora_local()
        abertas = db.exec(
            select(Movimentacao).where(col(Movimentacao.data_saida).is_(None)).order_by(Movimentacao.data_entrada)
        ).all()
        itens = []
        for mov in abertas:
            veiculo = db.get(Veiculo, mov.id_veiculo)
            cliente = db.get(Cliente, veiculo.id_cliente) if veiculo else None
            vaga = db.get(Vaga, mov.id_vaga)
            itens.append({
                "id": mov.id,
                "placa": veiculo.placa if veiculo else "-",
                "marca": veiculo.marca if veiculo else None,
                "modelo": veiculo.modelo if veiculo else "-",
                "cliente_nome": cliente.nome if cliente else None,
                "codigo_vaga": vaga.codigo_vaga if vaga else "-",
                "tipo_vaga": _v(vaga.tipo) if vaga else "-",
                "categoria": _v(vaga.categoria) if vaga else "Carro",
                "data_entrada": mov.data_entrada,
                "permanencia_minutos": minutos_permanencia(mov.data_entrada, agora),
            })
        return itens
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def limites_do_periodo(inicio: Optional[date], fim: Optional[date]):
    """Converte datas (inclusivas) no intervalo [início 00:00, dia seguinte 00:00).

    O limite final é EXCLUSIVO (início do dia seguinte): assim o último dia entra inteiro,
    inclusive 23:59:59. Os horários são sem fuso, como as colunas DATETIME do banco."""
    ini = datetime.combine(inicio, time.min) if inicio else None
    fim_exclusivo = datetime.combine(fim, time.min) + timedelta(days=1) if fim else None
    return ini, fim_exclusivo


def listar_movimentacoes_detalhadas(
    db: Session, inicio: Optional[date] = None, fim: Optional[date] = None, placa: Optional[str] = None,
    id_veiculo: Optional[int] = None,
) -> list[dict]:
    """Movimentações com placa, cliente, vaga e valor cobrado (para relatórios)."""
    try:
        ini, fim_excl = limites_do_periodo(inicio, fim)
        stmt = select(Movimentacao, Veiculo).join(Veiculo, Movimentacao.id_veiculo == Veiculo.id)
        if ini:
            stmt = stmt.where(Movimentacao.data_entrada >= ini)
        if fim_excl:
            stmt = stmt.where(Movimentacao.data_entrada < fim_excl)
        if id_veiculo:
            stmt = stmt.where(Movimentacao.id_veiculo == id_veiculo)
        if placa:
            p = "".join(ch for ch in placa.upper() if ch.isalnum())
            if p:
                stmt = stmt.where(func.replace(func.upper(Veiculo.placa), "-", "").like(f"%{p}%"))
        stmt = stmt.order_by(col(Movimentacao.data_entrada).desc())
        agora = agora_local()
        itens = []
        for mov, veiculo in db.exec(stmt).all():
            cliente = db.get(Cliente, veiculo.id_cliente)
            vaga = db.get(Vaga, mov.id_vaga)
            pagos = db.exec(
                select(func.coalesce(func.sum(Pagamento.valor_total), 0)).where(Pagamento.id_movimentacao == mov.id)
            ).one()
            def nome_usuario(id_usuario):
                u = db.get(Usuario, id_usuario) if id_usuario else None
                return u.nome if u else None

            itens.append({
                "id": mov.id,
                "entrada_por": nome_usuario(mov.id_usuario_entrada),
                "saida_por": nome_usuario(mov.id_usuario_saida),
                "liberado_por": nome_usuario(mov.id_usuario_liberacao),
                "obs_liberacao": mov.obs_liberacao,
                "placa": veiculo.placa,
                "marca": veiculo.marca,
                "modelo": veiculo.modelo,
                "cliente_nome": cliente.nome if cliente else None,
                "codigo_vaga": vaga.codigo_vaga if vaga else "-",
                "data_entrada": mov.data_entrada,
                "data_saida": mov.data_saida,
                "permanencia_minutos": minutos_permanencia(mov.data_entrada, mov.data_saida or agora),
                "valor_cobrado": float(pagos or 0),
            })
        return itens
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def consultar_modo_entrada(id_veiculo: int, db: Session) -> dict:
    """Como este veículo entraria agora (mensalista ou horista). Não grava nada."""
    try:
        veiculo = db.get(Veiculo, id_veiculo)
        if not veiculo:
            raise KeyError(f"Veículo de ID {id_veiculo} não encontrado.")
        return modo_de_entrada(db, veiculo)
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
