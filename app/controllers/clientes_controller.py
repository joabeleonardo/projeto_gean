from sqlmodel import Session, select
from controllers.auditoria import aplicar_auditoria
from sqlalchemy.exc import OperationalError, IntegrityError
from entidades.entidades import Cliente
from modelos.schemas import ClienteCreate

def inserir_cliente(cliente_in: ClienteCreate, db: Session) -> Cliente:
    try:
        # REGRA CRÍTICA DE AUDITORIA
        aplicar_auditoria(db, cliente_in.id_usuario_logado, cliente_in.nome_usuario_logado)

        cliente_insert = Cliente.model_validate(cliente_in.model_dump(mode="json", exclude={"id_usuario_logado", "nome_usuario_logado"}))
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
        aplicar_auditoria(db, dados_atualizados.id_usuario_logado, dados_atualizados.nome_usuario_logado)

        cliente_data = dados_atualizados.model_dump(mode="json", exclude_unset=True, exclude={"id_usuario_logado", "nome_usuario_logado"})
        # CPF/CNPJ/passaporte não se altera pelo sistema (somente direto no banco)
        for campo in ("cpf", "tipo_documento"):
            novo = cliente_data.pop(campo, None)
            atual = getattr(cliente, campo)
            if novo is not None and str(getattr(atual, "value", atual)) != str(novo):
                raise ValueError("O CPF/CNPJ do cliente não pode ser alterado pelo sistema.")
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
        aplicar_auditoria(db, id_usuario_logado, nome_usuario_logado)
        
        db.delete(cliente)
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e

# ------------------------------------------------------------------ busca
from sqlalchemy import func, or_
from sqlmodel import col
from entidades.entidades import Veiculo


def _sem_mascara(coluna, caracteres: str):
    """Expressão SQL que remove pontuação da coluna (para comparar só os dígitos)."""
    expr = coluna
    for c in caracteres:
        expr = func.replace(expr, c, "")
    return expr


def pesquisar_clientes(termo: str, db: Session, limite: int = 200) -> list[Cliente]:
    """Busca por nome, CPF, telefone ou placa de algum veículo do cliente."""
    try:
        termo = (termo or "").strip()
        statement = select(Cliente)
        if termo:
            digitos = "".join(ch for ch in termo if ch.isdigit())
            condicoes = [col(Cliente.nome).like(f"%{termo}%")]
            if digitos:
                condicoes.append(_sem_mascara(Cliente.cpf, ".-/").like(f"%{digitos}%"))
                condicoes.append(_sem_mascara(Cliente.telefone, "()+ -").like(f"%{digitos}%"))
            placa = "".join(ch for ch in termo.upper() if ch.isalnum())
            if len(placa) >= 3:
                placas = select(Veiculo.id_cliente).where(
                    func.replace(func.upper(Veiculo.placa), "-", "").like(f"%{placa}%")
                )
                condicoes.append(col(Cliente.id).in_(placas))
            statement = statement.where(or_(*condicoes))
        statement = statement.order_by(Cliente.nome).limit(limite)
        return db.exec(statement).all()
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e



# ------------------------------------------------------- listagem paginada
from datetime import date as _date
from controllers.inadimplencia_controller import _pendentes_vencidas
from entidades.entidades import Mensalidade, Movimentacao, Pagamento, StatusPagamentoEnum, Vaga
from servicos.datas import hoje_local
from servicos.inadimplencia import resumir_atraso


def _planos_por_cliente(db: Session, ids: list[int], hoje: _date) -> dict:
    if not ids:
        return {}
    planos = db.exec(select(Mensalidade).where(col(Mensalidade.id_cliente).in_(ids), Mensalidade.ativa == True)).all()  # noqa: E712
    saida: dict = {}
    for p in planos:
        if p.data_fim is not None and p.data_fim < hoje:
            continue
        vaga = db.get(Vaga, p.id_vaga) if p.id_vaga else None
        saida.setdefault(p.id_cliente, []).append({
            "id": p.id, "categoria": getattr(p.categoria, "value", p.categoria), "cotas": p.cotas,
            "tipo_plano": getattr(p.tipo_plano, "value", p.tipo_plano), "data_inicio": p.data_inicio,
            "vigente": p.data_inicio <= hoje, "codigo_vaga": vaga.codigo_vaga if vaga else None,
        })
    return saida


def _atrasos_por_cliente(db: Session, ids: list[int], hoje: _date) -> dict:
    if not ids:
        return {}
    agrupado: dict = {}
    for p in db.exec(select(Pagamento).where(
        col(Pagamento.id_cliente).in_(ids), Pagamento.status == StatusPagamentoEnum.Pendente,
        col(Pagamento.data_vencimento).is_not(None), Pagamento.data_vencimento < hoje,
    )).all():
        agrupado.setdefault(p.id_cliente, []).append((p.data_vencimento, p.valor_total))
    return {i: resumir_atraso(c, hoje) for i, c in agrupado.items()}


def listar_pagina(
    db: Session, q: str = "", nome: str = "", documento: str = "", telefone: str = "", placa: str = "",
    tipo: str = "", pais: str = "", ordem: str = "nome", pagina: int = 1, por_pagina: int = 10,
) -> dict:
    """Uma página de clientes, com filtros e já com plano e inadimplência de cada um (só os da página)."""
    try:
        pagina, por_pagina = max(1, pagina), min(max(5, por_pagina), 100)
        hoje = hoje_local()
        stmt = select(Cliente)

        if q.strip():  # busca geral: mesma regra da busca rápida
            stmt = stmt.where(col(Cliente.id).in_(select(Cliente.id).where(_condicao_geral(q.strip()))))
        if nome.strip():
            stmt = stmt.where(col(Cliente.nome).like(f"%{nome.strip()}%"))
        if documento.strip():
            digitos = "".join(c for c in documento if c.isdigit())
            if digitos:
                stmt = stmt.where(_sem_mascara(Cliente.cpf, ".-/").like(f"%{digitos}%"))
            else:
                stmt = stmt.where(func.upper(Cliente.cpf).like(f"%{documento.strip().upper()}%"))
        if telefone.strip():
            d = "".join(c for c in telefone if c.isdigit())
            if d:
                stmt = stmt.where(or_(_sem_mascara(Cliente.telefone, "()+ -").like(f"%{d}%"),
                                      _sem_mascara(Cliente.telefone2, "()+ -").like(f"%{d}%")))
        if placa.strip():
            p = "".join(c for c in placa.upper() if c.isalnum())
            stmt = stmt.where(col(Cliente.id).in_(select(Veiculo.id_cliente).where(
                func.replace(func.upper(Veiculo.placa), "-", "").like(f"%{p}%"))))
        if pais == "brasil":
            stmt = stmt.where(func.lower(Cliente.pais).in_(["brasil", "brazil"]))
        elif pais == "estrangeiro":
            stmt = stmt.where(func.lower(Cliente.pais).not_in(["brasil", "brazil"]))

        ativos = select(Mensalidade.id_cliente).where(
            Mensalidade.ativa == True,  # noqa: E712
            or_(col(Mensalidade.data_fim).is_(None), Mensalidade.data_fim >= hoje))
        if tipo == "mensalista":
            stmt = stmt.where(col(Cliente.id).in_(ativos))
        elif tipo == "premium":
            stmt = stmt.where(col(Cliente.id).in_(ativos.where(Mensalidade.tipo_plano == "Premium")))
        elif tipo == "horista":
            stmt = stmt.where(col(Cliente.id).not_in(ativos))
        elif tipo == "inadimplente":
            stmt = stmt.where(col(Cliente.id).in_(select(Pagamento.id_cliente).where(
                Pagamento.status == StatusPagamentoEnum.Pendente, col(Pagamento.id_cliente).is_not(None),
                Pagamento.data_vencimento < hoje)))

        total = int(db.exec(select(func.count()).select_from(stmt.subquery())).one() or 0)
        ordenacao = {"documento": col(Cliente.cpf), "recentes": col(Cliente.id).desc()}.get(ordem, col(Cliente.nome))
        clientes = db.exec(stmt.order_by(ordenacao).offset((pagina - 1) * por_pagina).limit(por_pagina)).all()

        ids = [c.id for c in clientes]
        planos, atrasos = _planos_por_cliente(db, ids, hoje), _atrasos_por_cliente(db, ids, hoje)
        itens = []
        for c in clientes:
            d = c.model_dump(mode="json")
            d["planos"] = planos.get(c.id, [])
            atraso = atrasos.get(c.id)
            d["dias_atraso"] = atraso["dias_atraso"] if atraso else 0
            d["estrangeiro"] = str(c.pais or "").strip().lower() not in ("brasil", "brazil")
            itens.append(d)
        return {"itens": itens, "total": total, "pagina": pagina, "por_pagina": por_pagina,
                "paginas": max(1, -(-total // por_pagina))}
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def _condicao_geral(termo: str):
    """Mesma lógica da busca rápida (nome, documento, telefone, placa), como condição reutilizável."""
    digitos = "".join(ch for ch in termo if ch.isdigit())
    condicoes = [col(Cliente.nome).like(f"%{termo}%"), func.upper(Cliente.cpf).like(f"%{termo.upper()}%")]
    if digitos:
        condicoes.append(_sem_mascara(Cliente.cpf, ".-/").like(f"%{digitos}%"))
        condicoes.append(_sem_mascara(Cliente.telefone, "()+ -").like(f"%{digitos}%"))
        condicoes.append(_sem_mascara(Cliente.telefone2, "()+ -").like(f"%{digitos}%"))
    placa = "".join(ch for ch in termo.upper() if ch.isalnum())
    if len(placa) >= 3:
        condicoes.append(col(Cliente.id).in_(select(Veiculo.id_cliente).where(
            func.replace(func.upper(Veiculo.placa), "-", "").like(f"%{placa}%"))))
    return or_(*condicoes)
