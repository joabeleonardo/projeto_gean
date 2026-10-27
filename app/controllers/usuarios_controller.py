from sqlmodel import Session, select
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Usuario
from modelos.schemas import UsuarioCreate

def inserir_usuario(usuario_in: UsuarioCreate, db: Session) -> Usuario:
    try:
        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {usuario_in.id_usuario_logado} - {usuario_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        usuario_insert = Usuario.model_validate(usuario_in, exclude={"id_usuario_logado", "nome_usuario_logado"})
        db.add(usuario_insert)
        db.commit()
        db.refresh(usuario_insert)
        return usuario_insert
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao inserir usuário (Login já existente).") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_usuarios(db: Session) -> list[Usuario]:
    try:
        statement = select(Usuario)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_usuario_por_id(id_usuario: int, db: Session) -> Usuario:
    try:
        usuario = db.get(Usuario, id_usuario)
        if not usuario:
            raise KeyError(f"Usuário de ID {id_usuario} não encontrado.")
        return usuario
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def atualizar_usuario(id_usuario: int, dados_atualizados: UsuarioCreate, db: Session) -> Usuario:
    try:
        usuario = db.get(Usuario, id_usuario)
        if not usuario:
            raise KeyError(f"Usuário de ID {id_usuario} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {dados_atualizados.id_usuario_logado} - {dados_atualizados.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        usuario_data = dados_atualizados.model_dump(exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"})
        for key, value in usuario_data.items():
            setattr(usuario, key, value)
        
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao atualizar usuário.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def deletar_usuario(id_usuario: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        usuario = db.get(Usuario, id_usuario)
        if not usuario:
            raise KeyError(f"Usuário de ID {id_usuario} não encontrado.")
        
        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {id_usuario_logado} - {nome_usuario_logado}'")
        db.execute(auditoria_sql)
        
        db.delete(usuario)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e