from sqlmodel import Session, select
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Preco
from modelos.schemas import PrecoCreate

def inserir_preco(preco_in: PrecoCreate, db: Session) -> Preco:
    try:
        # REGRA CRÍTICA DE AUDITORIA
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {preco_in.id_usuario_logado} - {preco_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        preco_insert = Preco.model_validate(preco_in, exclude={"id_usuario_logado", "nome_usuario_logado"})
        db.add(preco_insert)
        db.commit()
        db.refresh(preco_insert)
        return preco_insert
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao inserir preço (Tipo de cobrança já existente).") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_precos(db: Session) -> list[Preco]:
    try:
        statement = select(Preco)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_preco_por_id(id_preco: int, db: Session) -> Preco:
    try:
        preco = db.get(Preco, id_preco)
        if not preco:
            raise KeyError(f"Preço de ID {id_preco} não encontrado.")
        return preco
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def atualizar_preco(id_preco: int, dados_atualizados: PrecoCreate, db: Session) -> Preco:
    try:
        preco = db.get(Preco, id_preco)
        if not preco:
            raise KeyError(f"Preço de ID {id_preco} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {dados_atualizados.id_usuario_logado} - {dados_atualizados.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        preco_data = dados_atualizados.model_dump(exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"})
        for key, value in preco_data.items():
            setattr(preco, key, value)
        
        db.add(preco)
        db.commit()
        db.refresh(preco)
        return preco
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao atualizar preço.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def deletar_preco(id_preco: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        preco = db.get(Preco, id_preco)
        if not preco:
            raise KeyError(f"Preço de ID {id_preco} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {id_usuario_logado} - {nome_usuario_logado}'")
        db.execute(auditoria_sql)
        
        db.delete(preco)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e