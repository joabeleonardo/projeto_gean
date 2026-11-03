from sqlmodel import Session, select
from controllers.auditoria import aplicar_auditoria
from sqlalchemy.exc import OperationalError, IntegrityError

from entidades.entidades import Veiculo
from modelos.schemas import VeiculoCreate

def inserir_veiculo(veiculo_in: VeiculoCreate, db: Session) -> Veiculo:
    try:
        # ⚠️ REGRA CRÍTICA DE AUDITORIA: Injeta a variável antes do DML[cite: 2]
        aplicar_auditoria(db, veiculo_in.id_usuario_logado, veiculo_in.nome_usuario_logado)

        veiculo_insert = Veiculo.model_validate(veiculo_in.model_dump(mode="json", exclude={"id_usuario_logado", "nome_usuario_logado"}))
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
    """Corrige placa, marca, modelo, cor, tipo e proprietário do veículo."""
    try:
        veiculo = db.get(Veiculo, id_veiculo)
        if not veiculo:
            raise KeyError(f"Veículo de ID {id_veiculo} não encontrado.")

        veiculo_data = dados_atualizados.model_dump(
            mode="json", exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"}
        )
        # tipo (carro/moto) e proprietário definem vaga, cota e cobrança: não mudam com o veículo no pátio
        no_patio = db.exec(select(Movimentacao).where(
            Movimentacao.id_veiculo == id_veiculo, col(Movimentacao.data_saida).is_(None)
        )).first()
        mudou_tipo = "tipo_veiculo" in veiculo_data and veiculo_data["tipo_veiculo"] != str(getattr(veiculo.tipo_veiculo, "value", veiculo.tipo_veiculo))
        mudou_dono = "id_cliente" in veiculo_data and veiculo_data["id_cliente"] != veiculo.id_cliente
        if no_patio and (mudou_tipo or mudou_dono):
            raise ValueError("Veículo no pátio: registre a saída antes de alterar o tipo ou o proprietário.")
        if "placa" in veiculo_data:
            outro = db.exec(select(Veiculo).where(Veiculo.placa == veiculo_data["placa"], Veiculo.id != id_veiculo)).first()
            if outro:
                raise ValueError(f"Já existe outro veículo com a placa {veiculo_data['placa']}.")
        if "id_cliente" in veiculo_data and db.get(Cliente, veiculo_data["id_cliente"]) is None:
            raise KeyError(f"Cliente de ID {veiculo_data['id_cliente']} não encontrado.")

        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        aplicar_auditoria(db, dados_atualizados.id_usuario_logado, dados_atualizados.nome_usuario_logado)
        for key, value in veiculo_data.items():
            setattr(veiculo, key, value)

        db.add(veiculo)
        db.commit()
        db.refresh(veiculo)
        return veiculo
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Erro de integridade ao atualizar veículo (placa duplicada ou proprietário inexistente).") from e
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
    except (ValueError, KeyError):
        db.rollback()
        raise


def deletar_veiculo(id_veiculo: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session):
    try:
        veiculo = db.get(Veiculo, id_veiculo)
        if not veiculo:
            raise KeyError(f"Veículo de ID {id_veiculo} não encontrado.")
        
        # ⚠️ REGRA CRÍTICA DE AUDITORIA[cite: 2]
        aplicar_auditoria(db, id_usuario_logado, nome_usuario_logado)
        
        db.delete(veiculo)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

# ------------------------------------------------------------------ busca
from sqlalchemy import func, or_
from sqlmodel import col
from entidades.entidades import Cliente, Movimentacao


def pesquisar_veiculos(termo: str, db: Session, limite: int = 200) -> list[dict]:
    """Busca por placa, modelo, cor, nome ou CPF do dono. Sem termo, lista todos."""
    try:
        termo = (termo or "").strip()
        statement = select(Veiculo, Cliente).join(Cliente, Veiculo.id_cliente == Cliente.id)
        if termo:
            placa = "".join(ch for ch in termo.upper() if ch.isalnum())
            digitos = "".join(ch for ch in termo if ch.isdigit())
            condicoes = [
                col(Veiculo.modelo).like(f"%{termo}%"),
                col(Veiculo.marca).like(f"%{termo}%"),
                col(Veiculo.cor).like(f"%{termo}%"),
                col(Cliente.nome).like(f"%{termo}%"),
            ]
            if placa:
                condicoes.append(func.replace(func.upper(Veiculo.placa), "-", "").like(f"%{placa}%"))
            if digitos:
                cpf_digitos = func.replace(func.replace(Cliente.cpf, ".", ""), "-", "")
                condicoes.append(cpf_digitos.like(f"%{digitos}%"))
            statement = statement.where(or_(*condicoes))
        statement = statement.order_by(Veiculo.placa).limit(limite)
        return [
            {
                "id": v.id,
                "placa": v.placa,
                "marca": v.marca,
                "modelo": v.modelo,
                "cor": v.cor,
                "tipo_veiculo": getattr(v.tipo_veiculo, "value", v.tipo_veiculo),
                "id_cliente": v.id_cliente,
                "cliente_nome": c.nome,
                "cliente_cpf": c.cpf,
            }
            for v, c in db.exec(statement).all()
        ]
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


# ------------------------------------------------------- listagem paginada
from entidades.entidades import Pagamento  # noqa: F401  (mantém o módulo coeso para futuras colunas)


def listar_pagina(
    db: Session, q: str = "", placa: str = "", veiculo: str = "", proprietario: str = "", documento: str = "",
    tipo: str = "", ordem: str = "placa", pagina: int = 1, por_pagina: int = 10,
) -> dict:
    """Uma página de veículos, com filtros por placa, marca/modelo, dono, documento e tipo."""
    try:
        pagina, por_pagina = max(1, pagina), min(max(5, por_pagina), 100)
        stmt = select(Veiculo, Cliente).join(Cliente, Veiculo.id_cliente == Cliente.id)
        if q.strip():
            t = q.strip()
            p = "".join(ch for ch in t.upper() if ch.isalnum())
            d = "".join(ch for ch in t if ch.isdigit())
            cond = [col(Veiculo.modelo).like(f"%{t}%"), col(Veiculo.marca).like(f"%{t}%"), col(Veiculo.cor).like(f"%{t}%"),
                    col(Cliente.nome).like(f"%{t}%")]
            if p:
                cond.append(func.replace(func.upper(Veiculo.placa), "-", "").like(f"%{p}%"))
            if d:
                cond.append(func.replace(func.replace(func.replace(Cliente.cpf, ".", ""), "-", ""), "/", "").like(f"%{d}%"))
            stmt = stmt.where(or_(*cond))
        if placa.strip():
            p = "".join(ch for ch in placa.upper() if ch.isalnum())
            stmt = stmt.where(func.replace(func.upper(Veiculo.placa), "-", "").like(f"%{p}%"))
        if veiculo.strip():
            t = veiculo.strip()
            stmt = stmt.where(or_(col(Veiculo.marca).like(f"%{t}%"), col(Veiculo.modelo).like(f"%{t}%"), col(Veiculo.cor).like(f"%{t}%")))
        if proprietario.strip():
            stmt = stmt.where(col(Cliente.nome).like(f"%{proprietario.strip()}%"))
        if documento.strip():
            d = "".join(ch for ch in documento if ch.isdigit())
            if d:
                stmt = stmt.where(func.replace(func.replace(func.replace(Cliente.cpf, ".", ""), "-", ""), "/", "").like(f"%{d}%"))
            else:
                stmt = stmt.where(func.upper(Cliente.cpf).like(f"%{documento.strip().upper()}%"))
        if tipo in ("Carro", "Moto"):
            stmt = stmt.where(Veiculo.tipo_veiculo == tipo)

        total = int(db.exec(select(func.count()).select_from(stmt.subquery())).one() or 0)
        ordenacao = {"marca": col(Veiculo.marca), "proprietario": col(Cliente.nome),
                     "recentes": col(Veiculo.id).desc()}.get(ordem, col(Veiculo.placa))
        linhas = db.exec(stmt.order_by(ordenacao).offset((pagina - 1) * por_pagina).limit(por_pagina)).all()
        no_patio = set(db.exec(select(Movimentacao.id_veiculo).where(
            col(Movimentacao.id_veiculo).in_([v.id for v, _ in linhas]), col(Movimentacao.data_saida).is_(None))).all()) if linhas else set()
        itens = [{
            "id": v.id, "placa": v.placa, "marca": v.marca, "modelo": v.modelo, "cor": v.cor,
            "tipo_veiculo": getattr(v.tipo_veiculo, "value", v.tipo_veiculo), "id_cliente": v.id_cliente,
            "cliente_nome": c.nome, "cliente_cpf": c.cpf, "no_patio": v.id in no_patio,
        } for v, c in linhas]
        return {"itens": itens, "total": total, "pagina": pagina, "por_pagina": por_pagina,
                "paginas": max(1, -(-total // por_pagina))}
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
