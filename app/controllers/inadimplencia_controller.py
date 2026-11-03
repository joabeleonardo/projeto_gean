from collections import defaultdict
from datetime import date
from typing import Optional

from sqlmodel import Session, select, col
from sqlalchemy.exc import OperationalError

from entidades.entidades import Cliente, Pagamento, StatusPagamentoEnum
from servicos.datas import hoje_local
from servicos.inadimplencia import resumir_atraso


def _pendentes_vencidas(db: Session, hoje: date, id_cliente: Optional[int] = None):
    stmt = select(Pagamento).where(
        Pagamento.status == StatusPagamentoEnum.Pendente,
        col(Pagamento.id_cliente).is_not(None),
        col(Pagamento.data_vencimento).is_not(None),
        Pagamento.data_vencimento < hoje,
    )
    if id_cliente is not None:
        stmt = stmt.where(Pagamento.id_cliente == id_cliente)
    return db.exec(stmt).all()


def situacao_do_cliente(db: Session, id_cliente: int, hoje: Optional[date] = None) -> Optional[dict]:
    """None se o cliente está em dia; senão dias de atraso, valor e quantidade."""
    hoje = hoje or hoje_local()
    cobrancas = [(p.data_vencimento, p.valor_total) for p in _pendentes_vencidas(db, hoje, id_cliente)]
    return resumir_atraso(cobrancas, hoje)


def listar_inadimplentes(db: Session) -> list[dict]:
    """Clientes com cobrança vencida, do maior atraso para o menor."""
    try:
        hoje = hoje_local()
        por_cliente = defaultdict(list)
        for p in _pendentes_vencidas(db, hoje):
            por_cliente[p.id_cliente].append((p.data_vencimento, p.valor_total))
        itens = []
        for id_cliente, cobrancas in por_cliente.items():
            resumo = resumir_atraso(cobrancas, hoje)
            cliente = db.get(Cliente, id_cliente)
            if resumo and cliente:
                itens.append({
                    "id": cliente.id, "nome": cliente.nome, "cpf": cliente.cpf,
                    "telefone": cliente.telefone, **resumo,
                })
        return sorted(itens, key=lambda i: (-i["dias_atraso"], i["nome"]))
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def listar_inadimplentes_pagina(db: Session, nome: str = "", documento: str = "", pagina: int = 1, por_pagina: int = 10) -> dict:
    """Inadimplentes (cobrança vencida e pendente), com filtro por nome/documento e paginação."""
    itens = listar_inadimplentes(db)
    if nome.strip():
        itens = [i for i in itens if nome.strip().lower() in i["nome"].lower()]
    if documento.strip():
        d = "".join(c for c in documento if c.isdigit())
        itens = [i for i in itens if (d and d in "".join(c for c in i["cpf"] if c.isdigit()))
                 or documento.strip().lower() in i["cpf"].lower()]
    pagina, por_pagina = max(1, pagina), min(max(5, por_pagina), 100)
    total = len(itens)
    ini = (pagina - 1) * por_pagina
    return {"itens": itens[ini:ini + por_pagina], "total": total, "pagina": pagina, "por_pagina": por_pagina,
            "paginas": max(1, -(-total // por_pagina)),
            "valor_em_aberto": round(sum(i["valor_em_aberto"] for i in itens), 2)}


def cobrancas_pendentes(db: Session, id_cliente: int) -> list[dict]:
    """Todas as cobranças pendentes do cliente (vencidas ou não), da mais antiga para a mais nova."""
    try:
        hoje = hoje_local()
        pend = db.exec(select(Pagamento).where(
            Pagamento.id_cliente == id_cliente, Pagamento.status == StatusPagamentoEnum.Pendente
        ).order_by(col(Pagamento.data_vencimento))).all()
        return [{
            "id": p.id, "valor_total": p.valor_total, "data_vencimento": p.data_vencimento,
            "dias_atraso": max(0, (hoje - p.data_vencimento).days) if p.data_vencimento else 0,
        } for p in pend]
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
