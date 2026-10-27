from sqlmodel import Session, select
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError
from entidades.entidades import Cliente
from modelos.schemas import ClienteCreate

def inserir_cliente(cliente_in: ClienteCreate, db: Session) -> Cliente:
    try:
        # REGRA CRÍTICA DE AUDITORIA
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {cliente_in.id_usuario_logado} - {cliente_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        cliente_insert = Cliente.model_validate(cliente_in)
        db.add(cliente_insert)
        db.commit()
        db.refresh(cliente_insert)
        return cliente_insert
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao inserir cliente.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_clientes(db: Session) -> list[Cliente]:
    try:
        statement = select(Cliente)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_cliente_por_id(id_cliente: int, db: Session) -> Cliente:
    try:
        cliente = db.get(Cliente, id_cliente)
        if not cliente:
            raise KeyError(f"Cliente de ID {id_cliente} não encontrado.")
        return cliente
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def atualizar_cliente(id_cliente: int, dados_atualizados: ClienteCreate, db: Session) -> Cliente:
    try:
        cliente = db.get(Cliente, id_cliente)
        if not cliente:
            raise KeyError(f"Cliente de ID {id_cliente} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {dados_atualizados.id_usuario_logado} - {dados_atualizados.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        cliente_data = dados_atualizados.model_dump(exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"})
        for key, value in cliente_data.items():
            setattr(cliente, key, value)
        
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao atualizar cliente.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def deletar_cliente(id_cliente: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        cliente = db.get(Cliente, id_cliente)
        if not cliente:
            raise KeyError(f"Cliente de ID {id_cliente} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {id_usuario_logado} - {nome_usuario_logado}'")
        db.execute(auditoria_sql)
        
        db.delete(cliente)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e