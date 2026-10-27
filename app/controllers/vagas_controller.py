from sqlmodel import Session, select
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Vaga
from modelos.schemas import VagaCreate

def inserir_vaga(vaga_in: VagaCreate, db: Session) -> Vaga:
    try:
        # ⚠️ REGRA CRÍTICA DE AUDITORIA: Injeta a variável antes do DML[cite: 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {vaga_in.id_usuario_logado} - {vaga_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        vaga_insert = Vaga.model_validate(vaga_in, exclude={"id_usuario_logado", "nome_usuario_logado"})
        db.add(vaga_insert)
        db.commit()
        db.refresh(vaga_insert)
        return vaga_insert
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao inserir vaga (Código de vaga já existente).") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_vagas(db: Session) -> list[Vaga]:
    try:
        statement = select(Vaga)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_vaga_por_id(id_vaga: int, db: Session) -> Vaga:
    try:
        vaga = db.get(Vaga, id_vaga)
        if not vaga:
            raise KeyError(f"Vaga de ID {id_vaga} não encontrada.")
        return vaga
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def atualizar_vaga(id_vaga: int, dados_atualizados: VagaCreate, db: Session) -> Vaga:
    try:
        vaga = db.get(Vaga, id_vaga)
        if not vaga:
            raise KeyError(f"Vaga de ID {id_vaga} não encontrada.")
        
        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {dados_atualizados.id_usuario_logado} - {dados_atualizados.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        vaga_data = dados_atualizados.model_dump(exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"})
        for key, value in vaga_data.items():
            setattr(vaga, key, value)
        
        db.add(vaga)
        db.commit()
        db.refresh(vaga)
        return vaga
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao atualizar vaga.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def deletar_vaga(id_vaga: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        vaga = db.get(Vaga, id_vaga)
        if not vaga:
            raise KeyError(f"Vaga de ID {id_vaga} não encontrada.")
        
        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {id_usuario_logado} - {nome_usuario_logado}'")
        db.execute(auditoria_sql)
        
        db.delete(vaga)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e