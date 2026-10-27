from sqlmodel import Session, select
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Veiculo
from modelos.schemas import VeiculoCreate

def inserir_veiculo(veiculo_in: VeiculoCreate, db: Session) -> Veiculo:
    try:
        # ⚠️ REGRA CRÍTICA DE AUDITORIA: Injeta a variável antes do DML[cite: 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {veiculo_in.id_usuario_logado} - {veiculo_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        veiculo_insert = Veiculo.model_validate(veiculo_in, exclude={"id_usuario_logado", "nome_usuario_logado"})
        db.add(veiculo_insert)
        db.commit()
        db.refresh(veiculo_insert)
        return veiculo_insert
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao inserir veículo (Placa duplicada ou Cliente inexistente).") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_veiculos(db: Session) -> list[Veiculo]:
    try:
        statement = select(Veiculo)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_veiculo_por_id(id_veiculo: int, db: Session) -> Veiculo:
    try:
        veiculo = db.get(Veiculo, id_veiculo)
        if not veiculo:
            raise KeyError(f"Veículo de ID {id_veiculo} não encontrado.")
        return veiculo
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def atualizar_veiculo(id_veiculo: int, dados_atualizados: VeiculoCreate, db: Session) -> Veiculo:
    try:
        veiculo = db.get(Veiculo, id_veiculo)
        if not veiculo:
            raise KeyError(f"Veículo de ID {id_veiculo} não encontrado.")
        
        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {dados_atualizados.id_usuario_logado} - {dados_atualizados.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        veiculo_data = dados_atualizados.model_dump(exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"})
        for key, value in veiculo_data.items():
            setattr(veiculo, key, value)
        
        db.add(veiculo)
        db.commit()
        db.refresh(veiculo)
        return veiculo
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao atualizar veículo.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def deletar_veiculo(id_veiculo: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        veiculo = db.get(Veiculo, id_veiculo)
        if not veiculo:
            raise KeyError(f"Veículo de ID {id_veiculo} não encontrado.")
        
        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {id_usuario_logado} - {nome_usuario_logado}'")
        db.execute(auditoria_sql)
        
        db.delete(veiculo)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e