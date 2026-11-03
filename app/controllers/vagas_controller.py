from sqlmodel import Session, select
<<<<<<< HEAD
from controllers.auditoria import aplicar_auditoria
from sqlalchemy.exc import OperationalError, IntegrityError

from controllers.mensalidade_controller import checar_remocao_de_vaga_mensalista, checar_vaga_premium_sem_plano
from entidades.entidades import Vaga


def _v(x) -> str:
    return str(getattr(x, "value", x))

=======
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Vaga
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
from modelos.schemas import VagaCreate

def inserir_vaga(vaga_in: VagaCreate, db: Session) -> Vaga:
    try:
        # ⚠️ REGRA CRÍTICA DE AUDITORIA: Injeta a variável antes do DML[cite: 2]
<<<<<<< HEAD
        aplicar_auditoria(db, vaga_in.id_usuario_logado, vaga_in.nome_usuario_logado)

        vaga_insert = Vaga.model_validate(vaga_in.model_dump(mode="json", exclude={"id_usuario_logado", "nome_usuario_logado"}))
=======
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {vaga_in.id_usuario_logado} - {vaga_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        vaga_insert = Vaga.model_validate(vaga_in, exclude={"id_usuario_logado", "nome_usuario_logado"})
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
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
<<<<<<< HEAD
    """Edita código, tipo (horista/mensalista) e categoria (carro/moto) da vaga.
    A situação (livre/ocupada) é controlada pelas entradas e saídas, e a ativação por definir_situacao."""
=======
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
    try:
        vaga = db.get(Vaga, id_vaga)
        if not vaga:
            raise KeyError(f"Vaga de ID {id_vaga} não encontrada.")
<<<<<<< HEAD

        vaga_data = dados_atualizados.model_dump(
            mode="json", exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado", "status"}
        )
        novo_tipo = vaga_data.get("tipo", _v(vaga.tipo))
        nova_categoria = vaga_data.get("categoria", _v(vaga.categoria))
        mudou = novo_tipo != _v(vaga.tipo) or nova_categoria != _v(vaga.categoria)
        if mudou and _v(vaga.status) == "Ocupada":
            raise ValueError("Vaga ocupada: registre a saída do veículo antes de alterar o tipo ou o veículo da vaga.")
        # deixando de ser vaga de mensalista ativa? precisa sobrar vaga para as cotas já contratadas
        if mudou and vaga.ativa and _v(vaga.tipo) == "Mensalista":
            checar_remocao_de_vaga_mensalista(db, _v(vaga.categoria))
        if mudou and _v(vaga.tipo) == "Premium":
            checar_vaga_premium_sem_plano(db, vaga)    # vaga reservada por plano premium não muda de tipo

        aplicar_auditoria(db, dados_atualizados.id_usuario_logado, dados_atualizados.nome_usuario_logado)
        for key, value in vaga_data.items():
            setattr(vaga, key, value)

=======
        
        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {dados_atualizados.id_usuario_logado} - {dados_atualizados.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        vaga_data = dados_atualizados.model_dump(exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"})
        for key, value in vaga_data.items():
            setattr(vaga, key, value)
        
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
        db.add(vaga)
        db.commit()
        db.refresh(vaga)
        return vaga
    except IntegrityError as e:
        db.rollback()
<<<<<<< HEAD
        raise ValueError("Já existe outra vaga com este código.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


def definir_situacao(id_vaga: int, ativa: bool, usuario, db: Session) -> Vaga:
    """Ativa ou inativa a vaga (ex.: reforma). Vaga inativa não aparece como disponível e não recebe entradas."""
    try:
        vaga = db.get(Vaga, id_vaga)
        if not vaga:
            raise KeyError(f"Vaga de ID {id_vaga} não encontrada.")
        if vaga.ativa == ativa:
            return vaga
        if not ativa:
            if _v(vaga.status) == "Ocupada":
                raise ValueError("Vaga ocupada: registre a saída do veículo antes de inativá-la.")
            if _v(vaga.tipo) == "Mensalista":
                checar_remocao_de_vaga_mensalista(db, _v(vaga.categoria))
            if _v(vaga.tipo) == "Premium":
                checar_vaga_premium_sem_plano(db, vaga)
        aplicar_auditoria(db, usuario.id, usuario.nome)
        vaga.ativa = ativa
        db.add(vaga)
        db.commit()
        db.refresh(vaga)
        return vaga
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise

=======
        raise ValueError("Erro de integridade ao atualizar vaga.") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272

def deletar_vaga(id_vaga: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        vaga = db.get(Vaga, id_vaga)
        if not vaga:
            raise KeyError(f"Vaga de ID {id_vaga} não encontrada.")
        
<<<<<<< HEAD
        if _v(vaga.status) == "Ocupada":
            raise ValueError("Vaga ocupada: registre a saída do veículo antes de excluí-la.")
        if vaga.ativa and _v(vaga.tipo) == "Mensalista":
            checar_remocao_de_vaga_mensalista(db, _v(vaga.categoria))
        if _v(vaga.tipo) == "Premium":
            checar_vaga_premium_sem_plano(db, vaga)

        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        aplicar_auditoria(db, id_usuario_logado, nome_usuario_logado)
=======
        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {id_usuario_logado} - {nome_usuario_logado}'")
        db.execute(auditoria_sql)
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
        
        db.delete(vaga)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e