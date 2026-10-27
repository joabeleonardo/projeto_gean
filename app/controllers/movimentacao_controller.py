from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Movimentacao, Vaga, StatusVagaEnum
from modelos.schemas import MovimentacaoEntradaCreate, MovimentacaoSaidaUpdate

def registrar_entrada(mov_in: MovimentacaoEntradaCreate, db: Session) -> Movimentacao:
    try:
        # REGRA CRÍTICA DE AUDITORIA: Injeta a variável antes do DML[cite: 1, 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {mov_in.id_usuario_logado} - {mov_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        # Verifica se a vaga existe e está livre
        vaga = db.get(Vaga, mov_in.id_vaga)
        if not vaga:
            raise KeyError(f"Vaga de ID {mov_in.id_vaga} não encontrada.")
        if vaga.status == StatusVagaEnum.Ocupada:
            raise ValueError(f"A vaga {vaga.codigo_vaga} já está ocupada.")

        # Cria a movimentação
        nova_movimentacao = Movimentacao(
            id_veiculo=mov_in.id_veiculo,
            id_vaga=mov_in.id_vaga,
            data_entrada=datetime.now(),
            id_usuario_entrada=mov_in.id_usuario_entrada
        )

        # Atualiza o status da vaga para Ocupada
        vaga.status = StatusVagaEnum.Ocupada
        db.add(vaga)

        db.add(nova_movimentacao)
        db.commit()
        db.refresh(nova_movimentacao)
        return nova_movimentacao
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao registrar entrada (Veículo ou Vaga inválidos).") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

def buscar_movimentacoes(db: Session) -> list[Movimentacao]:
    try:
        statement = select(Movimentacao)
        return db.exec(statement).all()
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

def registrar_saida(id_movimentacao: int, saida_in: MovimentacaoSaidaUpdate, db: Session) -> Movimentacao:
    try:
        mov = db.get(Movimentacao, id_movimentacao)
        if not mov:
            raise KeyError(f"Movimentação de ID {id_movimentacao} não encontrada.")
        if mov.data_saida is not None:
            raise ValueError("Esta movimentação já possui registro de saída.")

        # REGRA CRÍTICA DE AUDITORIA[cite: 1, 2]
        auditoria_sql = text(f"SET @usuario_logado = 'ID: {saida_in.id_usuario_logado} - {saida_in.nome_usuario_logado}'")
        db.execute(auditoria_sql)

        # Atualiza dados de saída
        mov.data_saida = datetime.now()
        mov.id_usuario_saida = saida_in.id_usuario_saida

        # Libera a vaga associada
        vaga = db.get(Vaga, mov.id_vaga)
        if vaga:
            vaga.status = StatusVagaEnum.Livre
            db.add(vaga)

        db.add(mov)
        db.commit()
        db.refresh(mov)
        return mov
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e