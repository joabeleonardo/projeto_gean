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
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao registrar pagamento.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_pagamentos(db: Session) -> list[Pagamento]:
    try:
        statement = select(Pagamento)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_pagamento_por_id(id_pagamento: int, db: Session) -> Pagamento:
    try:
        pag = db.get(Pagamento, id_pagamento)
        if not pag:
            raise KeyError(f"Pagamento de ID {id_pagamento} não encontrado.")
        return pag
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def deletar_pagamento(id_pagamento: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        pag = db.get(Pagamento, id_pagamento)
        if not pag:
            raise KeyError(f"Pagamento de ID {id_pagamento} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {id_usuario_logado} - {nome_usuario_logado}'")
        db.execute(auditoria_sql)
        
        db.delete(pag)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e