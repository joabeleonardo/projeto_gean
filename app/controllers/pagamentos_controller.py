<<<<<<< HEAD
from datetime import datetime, date
from typing import Optional

from sqlmodel import Session, select, col
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import OperationalError, IntegrityError

from controllers.auditoria import aplicar_auditoria
from controllers.movimentacao_controller import limites_do_periodo
from entidades.entidades import (
    Pagamento, Movimentacao, Veiculo, Cliente, Vaga, Preco, Usuario,
    StatusPagamentoEnum, TipoPagamentoEnum, TipoCobrancaEnum, CategoriaEnum,
)
from modelos.schemas import PagamentoCreate
from servicos.caixa import calcular_troco, e_dinheiro
from servicos.datas import agora_local
from servicos.tarifa import calcular_valor_hora


def _valor(x) -> str:
    return str(getattr(x, "value", x))


def _preco_linha(db: Session, tipo: TipoCobrancaEnum, categoria: str, nome: str) -> Preco:
    preco = db.exec(
        select(Preco).where(Preco.tipo_cobranca == tipo, Preco.categoria == CategoriaEnum(categoria))
    ).first()
    if preco is None or preco.valor <= 0:
        raise ValueError(
            f"O preço {nome} de {categoria.lower()} ainda não foi definido. Peça a um administrador para cadastrá-lo."
        )
    return preco


def _preco(db: Session, tipo: TipoCobrancaEnum, categoria: str, nome: str) -> float:
    return _preco_linha(db, tipo, categoria, nome).valor


def registrar_pagamento(pag_in: PagamentoCreate, db: Session) -> Pagamento:
    """O valor NUNCA vem do cliente: é calculado aqui com o preço vigente."""
    try:
        aplicar_auditoria(db, pag_in.id_usuario_logado, pag_in.nome_usuario_logado)
        pendente = _valor(pag_in.status) == "Pendente"
        tipo = _valor(pag_in.tipo_cobranca)

        if tipo == "Mensal":
            if not pag_in.id_cliente:
                raise ValueError("Informe o cliente para registrar uma mensalidade.")
            if not db.get(Cliente, pag_in.id_cliente):
                raise KeyError(f"Cliente de ID {pag_in.id_cliente} não encontrado.")
            valor = _preco(db, TipoCobrancaEnum.Mensalista, _valor(pag_in.categoria), "mensal")
            id_mov, id_cli = None, pag_in.id_cliente
        else:
            if not pag_in.id_movimentacao:
                raise ValueError("Informe a movimentação para registrar um pagamento por hora.")
            mov = db.get(Movimentacao, pag_in.id_movimentacao)
            if not mov:
                raise KeyError(f"Movimentação de ID {pag_in.id_movimentacao} não encontrada.")
            if mov.data_saida is None:
                raise ValueError("A saída do veículo ainda não foi registrada; o valor é calculado na saída.")
            if db.exec(select(Pagamento).where(Pagamento.id_movimentacao == mov.id)).first():
                raise ValueError("Esta movimentação já possui pagamento.")
            vaga = db.get(Vaga, mov.id_vaga)
            categoria = _valor(vaga.categoria) if vaga else "Carro"
            p = _preco_linha(db, TipoCobrancaEnum.Horista, categoria, "por hora")
            valor = calcular_valor_hora(mov.data_entrada, mov.data_saida, p.valor, p.valor_minimo or 0.0, p.tempo_minimo_minutos or 0)
            id_mov, id_cli = mov.id, None

        if pendente and not pag_in.data_vencimento:
            raise ValueError("Informe a data de vencimento para uma cobrança pendente.")
        if not pendente and not pag_in.forma_pagamento:
            raise ValueError("Informe a forma de pagamento (dinheiro, Pix, cartão...).")

        recebido = troco = None
        if not pendente and e_dinheiro(pag_in.forma_pagamento):
            troco = calcular_troco(valor, pag_in.valor_recebido)
            recebido = round(pag_in.valor_recebido, 2)

        novo = Pagamento(
            id_movimentacao=id_mov,
            id_cliente=id_cli,
            tipo_cobranca=TipoPagamentoEnum(tipo),
            valor_total=valor,
            data_vencimento=pag_in.data_vencimento,
            data_pagamento=None if pendente else agora_local(),
            status=StatusPagamentoEnum.Pendente if pendente else StatusPagamentoEnum.Pago,
            forma_pagamento=None if pendente else _valor(pag_in.forma_pagamento),
            valor_recebido=recebido, troco=troco,
            id_usuario_recebimento=None if pendente else pag_in.id_usuario_recebimento,
        )
        db.add(novo)
        db.commit()
        db.refresh(novo)
        return novo
=======
from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Pagamento, StatusPagamentoEnum
from modelos.schemas import PagamentoCreate

def registrar_pagamento(pag_in: PagamentoCreate, db: Session) -> Pagamento:
    try:
        # REGRA CRÍTICA DE AUDITORIA: Injeta a variável antes do DML[cite: 1, 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {pag_in.id_usuario_logado} - {pag_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        novo_pagamento = Pagamento(
            id_movimentacao=pag_in.id_movimentacao,
            id_cliente=pag_in.id_cliente,
            tipo_cobranca=pag_in.tipo_cobranca,
            valor_total=pag_in.valor_total,
            data_vencimento=pag_in.data_vencimento,
            data_pagamento=datetime.now(),
            status=StatusPagamentoEnum.Pago,
            id_usuario_recebimento=pag_in.id_usuario_recebimento
        )

        db.add(novo_pagamento)
        db.commit()
        db.refresh(novo_pagamento)
        return novo_pagamento
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao registrar pagamento.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
<<<<<<< HEAD
    except (ValueError, KeyError):
        db.rollback()
        raise


def baixar_pagamento(id_pagamento: int, forma_pagamento, usuario, db: Session, valor_recebido=None) -> Pagamento:
    """Marca uma cobrança pendente como paga, registrando a forma de pagamento."""
    try:
        pag = db.get(Pagamento, id_pagamento)
        if not pag:
            raise KeyError(f"Pagamento de ID {id_pagamento} não encontrado.")
        if _valor(pag.status) == "Pago":
            raise ValueError("Este pagamento já foi baixado.")
        if e_dinheiro(forma_pagamento):
            pag.troco = calcular_troco(pag.valor_total, valor_recebido)
            pag.valor_recebido = round(valor_recebido, 2)
        else:
            pag.troco = pag.valor_recebido = None
        aplicar_auditoria(db, usuario.id, usuario.nome)
        pag.status = StatusPagamentoEnum.Pago
        pag.data_pagamento = agora_local()
        pag.forma_pagamento = _valor(forma_pagamento)
        pag.id_usuario_recebimento = usuario.id
        db.add(pag)
        db.commit()
        db.refresh(pag)
        return pag
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


def buscar_pagamentos(db: Session) -> list[Pagamento]:
    try:
        return db.exec(select(Pagamento)).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


=======

def buscar_pagamentos(db: Session) -> list[Pagamento]:
    try:
        statement = select(Pagamento)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
def buscar_pagamento_por_id(id_pagamento: int, db: Session) -> Pagamento:
    try:
        pag = db.get(Pagamento, id_pagamento)
        if not pag:
            raise KeyError(f"Pagamento de ID {id_pagamento} não encontrado.")
        return pag
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

<<<<<<< HEAD

def _stmt_pagamentos(db: Session, inicio, fim, status, tipo, cliente=None, forma=None, id_usuario=None):
    """Consulta de pagamentos com todos os filtros (usada na lista paginada e nos relatórios)."""
    ini, fim_excl = limites_do_periodo(inicio, fim)
    stmt = select(Pagamento)
    if status:
        stmt = stmt.where(Pagamento.status == StatusPagamentoEnum(status))
    if tipo:
        stmt = stmt.where(Pagamento.tipo_cobranca == TipoPagamentoEnum(tipo))
    if forma:
        stmt = stmt.where(Pagamento.forma_pagamento == forma)
    if id_usuario:
        stmt = stmt.where(Pagamento.id_usuario_recebimento == id_usuario)
    if cliente and cliente.strip():
        ids = select(Cliente.id).where(col(Cliente.nome).like(f"%{cliente.strip()}%"))
        movs = select(Movimentacao.id).join(Veiculo, Movimentacao.id_veiculo == Veiculo.id).where(col(Veiculo.id_cliente).in_(ids))
        stmt = stmt.where(or_(col(Pagamento.id_cliente).in_(ids), col(Pagamento.id_movimentacao).in_(movs)))
    if ini or fim_excl:
        pago, venc = [], []
        if ini:
            pago.append(Pagamento.data_pagamento >= ini)
            venc.append(Pagamento.data_vencimento >= ini.date())
        if fim_excl:
            pago.append(Pagamento.data_pagamento < fim_excl)
            venc.append(Pagamento.data_vencimento < fim_excl.date())
        stmt = stmt.where(or_(
            and_(col(Pagamento.data_pagamento).is_not(None), *pago),
            and_(col(Pagamento.data_pagamento).is_(None), *venc),
        ))
    return stmt.order_by(col(Pagamento.id).desc())


def _detalhar(db: Session, p: Pagamento) -> dict:
    cliente, placa = None, None
    if p.id_movimentacao:
        mov = db.get(Movimentacao, p.id_movimentacao)
        veiculo = db.get(Veiculo, mov.id_veiculo) if mov else None
        placa = veiculo.placa if veiculo else None
        cliente = db.get(Cliente, veiculo.id_cliente) if veiculo else None
    if p.id_cliente:
        cliente = db.get(Cliente, p.id_cliente)
    recebedor = db.get(Usuario, p.id_usuario_recebimento) if p.id_usuario_recebimento else None
    item = p.model_dump()
    item["cliente_nome"] = cliente.nome if cliente else None
    item["placa"] = placa
    item["recebido_por"] = recebedor.nome if recebedor else None
    return item


def listar_pagamentos_detalhados(
    db: Session, inicio: Optional[date] = None, fim: Optional[date] = None, status: Optional[str] = None,
    tipo: Optional[str] = None, cliente: Optional[str] = None, forma: Optional[str] = None, id_usuario: Optional[int] = None,
) -> list[dict]:
    """Todos os pagamentos do filtro, com cliente, placa e quem recebeu (relatórios). O período usa a data
    do pagamento (ou o vencimento, nas cobranças ainda pendentes)."""
    try:
        return [_detalhar(db, p) for p in db.exec(_stmt_pagamentos(db, inicio, fim, status, tipo, cliente, forma, id_usuario)).all()]
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def listar_pagamentos_pagina(
    db: Session, inicio=None, fim=None, status=None, tipo=None, cliente=None, forma=None, pagina: int = 1, por_pagina: int = 10,
) -> dict:
    """Uma página de pagamentos (a consulta só traz as linhas da página)."""
    try:
        pagina, por_pagina = max(1, pagina), min(max(5, por_pagina), 100)
        stmt = _stmt_pagamentos(db, inicio, fim, status, tipo, cliente, forma)
        total = int(db.exec(select(func.count()).select_from(stmt.order_by(None).subquery())).one() or 0)
        linhas = db.exec(stmt.offset((pagina - 1) * por_pagina).limit(por_pagina)).all()
        return {"itens": [_detalhar(db, p) for p in linhas], "total": total, "pagina": pagina,
                "por_pagina": por_pagina, "paginas": max(1, -(-total // por_pagina))}
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


=======
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
def deletar_pagamento(id_pagamento: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        pag = db.get(Pagamento, id_pagamento)
        if not pag:
            raise KeyError(f"Pagamento de ID {id_pagamento} não encontrado.")
<<<<<<< HEAD

        aplicar_auditoria(db, id_usuario_logado, nome_usuario_logado)

=======
        
        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {id_usuario_logado} - {nome_usuario_logado}'")
        db.execute(auditoria_sql)
        
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
        db.delete(pag)
        db.commit()
    except OperationalError as e:
        db.rollback()
<<<<<<< HEAD
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
=======
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
