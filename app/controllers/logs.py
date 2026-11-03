"""Logs do sistema: quem fez o quê, quando (cadastros, edições, exclusões, entradas, saídas, pagamentos...).

Funciona por um gancho do SQLAlchemy (before_flush/after_flush): toda gravação feita pelos controllers
já gera o log, com campo, valor antigo e valor novo, sem precisar repetir código em cada função.
O usuário responsável vem de aplicar_auditoria(), que cada controller já chama antes de gravar.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import event, func, inspect, or_, select as sa_select
from sqlalchemy.orm import Session as _SASession
from sqlmodel import Session, col, select

from entidades.entidades import (
    Cliente, Endereco, LogSistema, Mensalidade, Movimentacao, Pagamento, Preco, Usuario, Vaga, Veiculo,
)
from servicos.datas import agora_local
from servicos.logs import formatar_valor, frase_alteracao, frase_criacao, frase_exclusao

_registrado = False


def _v(x):
    return getattr(x, "value", x)


# ------------------------------------------------------------ nomes legíveis
def _cliente(s, id_cliente) -> str:
    c = s.get(Cliente, id_cliente) if id_cliente else None
    return c.nome if c else f"#{id_cliente}"


def _placa(s, id_veiculo) -> str:
    v = s.get(Veiculo, id_veiculo) if id_veiculo else None
    return v.placa if v else f"#{id_veiculo}"


def _vaga(s, id_vaga) -> str:
    v = s.get(Vaga, id_vaga) if id_vaga else None
    return v.codigo_vaga if v else f"#{id_vaga}"


def _usuario(s, id_usuario) -> str:
    u = s.get(Usuario, id_usuario) if id_usuario else None
    return u.nome if u else f"#{id_usuario}"


def _ident_endereco(o, s) -> str:
    c = s.execute(sa_select(Cliente).where(Cliente.id_endereco == o.id)).scalars().first() if o.id else None
    return f"({c.nome})" if c else f"{o.logradouro}, {o.numero}"


CONFIG = {
    "Cliente": {
        "entidade": "Cliente", "rotulo": "o cadastro do cliente", "ident": lambda o, s: o.nome,
        "campos": {"nome": "nome", "cpf": "CPF/CNPJ", "tipo_documento": "tipo de documento", "pais": "país",
                   "telefone": "telefone", "telefone_whatsapp": "telefone é WhatsApp", "telefone2": "telefone 2",
                   "telefone2_whatsapp": "telefone 2 é WhatsApp", "id_endereco": "endereço"},
    },
    "Endereco": {
        "entidade": "Endereço", "rotulo": "o endereço do cliente", "ident": _ident_endereco,
        "campos": {"logradouro": "rua", "numero": "número", "complemento": "complemento", "bairro": "bairro",
                   "cidade": "cidade", "estado": "UF", "cep": "CEP"},
    },
    "Veiculo": {
        "entidade": "Veículo", "rotulo": "o veículo", "ident": lambda o, s: o.placa,
        "campos": {"placa": "placa", "marca": "marca", "modelo": "modelo", "cor": "cor",
                   "tipo_veiculo": "tipo (carro/moto)", "id_cliente": "proprietário (ID)"},
    },
    "Vaga": {
        "entidade": "Vaga", "rotulo": "a vaga", "ident": lambda o, s: o.codigo_vaga, "ignorar": {"status"},
        "campos": {"codigo_vaga": "código", "tipo": "tipo de uso", "categoria": "veículo (carro/moto)", "ativa": "ativa"},
    },
    "Preco": {
        "entidade": "Preço", "rotulo": "o preço", "ident": lambda o, s: f"{_v(o.tipo_cobranca)} ({_v(o.categoria)})",
        "campos": {"valor": "valor", "valor_minimo": "valor mínimo", "tempo_minimo_minutos": "tempo mínimo (min)",
                   "tipo_cobranca": "tipo de cobrança", "categoria": "veículo (carro/moto)"},
    },
    "Usuario": {
        "entidade": "Usuário", "rotulo": "o usuário", "ident": lambda o, s: o.login,
        "campos": {"nome": "nome", "login": "login", "perfil": "perfil", "senha": "senha",
                   "codigo_liberacao": "código de liberação"},
    },
    "Mensalidade": {
        "entidade": "Plano", "rotulo": "o plano de mensalista do cliente", "ident": lambda o, s: _cliente(s, o.id_cliente),
        "campos": {"cotas": "cotas", "categoria": "veículo (carro/moto)", "tipo_plano": "tipo de plano",
                   "id_vaga": "vaga premium (ID)", "data_inicio": "início", "data_fim": "fim", "ativa": "ativo"},
    },
    "Pagamento": {
        "entidade": "Pagamento", "rotulo": "o pagamento", "ident": lambda o, s: f"#{o.id}" if o.id else "",
        "campos": {"valor_total": "valor", "status": "situação", "forma_pagamento": "forma de pagamento",
                   "data_vencimento": "vencimento", "data_pagamento": "data do pagamento",
                   "valor_recebido": "valor recebido", "troco": "troco"},
    },
    "Movimentacao": {
        "entidade": "Movimentação", "rotulo": "a movimentação do veículo", "ident": lambda o, s: _placa(s, o.id_veiculo),
        "campos": {},
    },
}


def _linha(u, acao, entidade, descricao, obj=None, id_registro=None, campo=None, antigo=None, novo=None) -> dict:
    return {
        "id_usuario": u[0], "usuario": u[1], "acao": acao, "entidade": entidade, "id_registro": id_registro,
        "descricao": descricao, "campo": campo, "valor_antigo": antigo, "valor_novo": novo, "_obj": obj,
    }


def _mudancas(obj, ignorar=()) -> list:
    """[(campo, antigo, novo)] das colunas realmente alteradas (via histórico do SQLAlchemy)."""
    estado = inspect(obj)
    saida = []
    for attr in estado.mapper.column_attrs:
        if attr.key == "id" or attr.key in ignorar:
            continue
        hist = estado.attrs[attr.key].history
        if not hist.has_changes():
            continue
        antigo = hist.deleted[0] if hist.deleted else None
        novo = hist.added[0] if hist.added else None
        if antigo == novo:
            continue
        saida.append((attr.key, antigo, novo))
    return saida


def _dinheiro(x) -> str:
    return formatar_valor("valor", x)


# ------------------------------------------------------------ criação
def _log_criacao(s, obj, u) -> list:
    nome = type(obj).__name__
    cfg = CONFIG[nome]
    n = u[1]
    if nome == "Movimentacao":
        txt = f"{n} registrou a ENTRADA do veículo {_placa(s, obj.id_veiculo)} na vaga {_vaga(s, obj.id_vaga)}"
        if obj.id_usuario_liberacao:
            txt += (f" — liberada com código do administrador {_usuario(s, obj.id_usuario_liberacao)}"
                    + (f" ({obj.obs_liberacao})" if obj.obs_liberacao else ""))
        return [_linha(u, "ENTRADA", "Movimentação", txt, obj)]
    if nome == "Pagamento":
        quem = _cliente(s, obj.id_cliente) if obj.id_cliente else (
            _placa(s, s.get(Movimentacao, obj.id_movimentacao).id_veiculo) if obj.id_movimentacao and s.get(Movimentacao, obj.id_movimentacao) else "—")
        if _v(obj.status) == "Pago":
            extra = f" em {obj.forma_pagamento}" if obj.forma_pagamento else ""
            if obj.valor_recebido is not None:
                extra += f" (recebido {_dinheiro(obj.valor_recebido)}, troco {_dinheiro(obj.troco or 0)})"
            txt = f"{n} registrou o pagamento {_v(obj.tipo_cobranca)} de {quem}: {_dinheiro(obj.valor_total)}{extra}"
        else:
            venc = formatar_valor("data_vencimento", obj.data_vencimento)
            txt = f"{n} lançou cobrança {_v(obj.tipo_cobranca)} pendente de {_dinheiro(obj.valor_total)} para {quem}, vence em {venc}"
        return [_linha(u, "PAGAMENTO", "Pagamento", txt, obj)]
    if nome == "Mensalidade":
        vaga = f", vaga {_vaga(s, obj.id_vaga)}" if obj.id_vaga else f", {obj.cotas} cota(s)"
        txt = (f"{n} registrou adesão ao plano {_v(obj.tipo_plano)} ({_v(obj.categoria)}{vaga}) do cliente "
               f"{_cliente(s, obj.id_cliente)}, início em {formatar_valor('data_inicio', obj.data_inicio)}")
        return [_linha(u, "CRIAR", "Plano", txt, obj)]
    if nome == "Usuario":
        return [_linha(u, "CRIAR", "Usuário", f"{n} cadastrou o usuário {obj.login} ({obj.perfil})", obj)]
    return [_linha(u, "CRIAR", cfg["entidade"], frase_criacao(n, cfg["rotulo"], cfg["ident"](obj, s)), obj)]


# ------------------------------------------------------------ alteração
def _log_alteracao(s, obj, u) -> list:
    nome = type(obj).__name__
    cfg = CONFIG[nome]
    n = u[1]
    mud = _mudancas(obj, cfg.get("ignorar", ()))
    if not mud:
        return []
    mapa = {c: (a, b) for c, a, b in mud}
    ident = cfg["ident"](obj, s)

    if nome == "Movimentacao":
        if "data_saida" in mapa and mapa["data_saida"][0] is None:
            return [_linha(u, "SAIDA", "Movimentação",
                           f"{n} registrou a SAÍDA do veículo {ident} da vaga {_vaga(s, obj.id_vaga)}", obj)]
        return []
    if nome == "Pagamento" and "status" in mapa and _v(mapa["status"][1]) == "Pago":
        extra = f" em {obj.forma_pagamento}" if obj.forma_pagamento else ""
        if obj.valor_recebido is not None:
            extra += f" (recebido {_dinheiro(obj.valor_recebido)}, troco {_dinheiro(obj.troco or 0)})"
        quem = _cliente(s, obj.id_cliente) if obj.id_cliente else ident
        return [_linha(u, "PAGAMENTO", "Pagamento",
                       f"{n} deu baixa no pagamento {_v(obj.tipo_cobranca)} de {quem}: {_dinheiro(obj.valor_total)}{extra}", obj)]
    if nome == "Vaga" and "ativa" in mapa:
        txt = f"{n} {'ativou' if mapa['ativa'][1] else 'inativou'} a vaga {ident}"
        linhas = [_linha(u, "ALTERAR", "Vaga", txt, obj, campo="ativa",
                         antigo=formatar_valor("ativa", mapa["ativa"][0]), novo=formatar_valor("ativa", mapa["ativa"][1]))]
        mud = [m for m in mud if m[0] != "ativa"]
    elif nome == "Mensalidade" and "ativa" in mapa and mapa["ativa"][1] is False:
        return [_linha(u, "ALTERAR", "Plano", f"{n} cancelou o plano {_v(obj.tipo_plano)} ({_v(obj.categoria)}) do cliente {ident}", obj)]
    else:
        linhas = []

    for campo, antigo, novo in mud:
        rotulo_campo = cfg["campos"].get(campo, campo)
        a, b = formatar_valor(campo, antigo), formatar_valor(campo, novo)
        linhas.append(_linha(u, "ALTERAR", cfg["entidade"], frase_alteracao(n, cfg["rotulo"], ident, rotulo_campo, a, b),
                             obj, campo=rotulo_campo, antigo=a, novo=b))
    return linhas


# ------------------------------------------------------------ ganchos
def _antes_do_flush(session, flush_context, instances):
    if session.info.get("sem_logs"):
        return
    u = session.info.get("usuario_log") or (None, "Sistema")
    pend = session.info.setdefault("_logs_pendentes", [])
    with session.no_autoflush:
        for obj in list(session.new):
            if type(obj).__name__ in CONFIG:
                pend.extend(_log_criacao(session, obj, u))
        for obj in list(session.dirty):
            if type(obj).__name__ in CONFIG and session.is_modified(obj, include_collections=False):
                pend.extend(_log_alteracao(session, obj, u))
        for obj in list(session.deleted):
            nome = type(obj).__name__
            if nome in CONFIG:
                cfg = CONFIG[nome]
                pend.append(_linha(u, "EXCLUIR", cfg["entidade"],
                                   frase_exclusao(u[1], cfg["rotulo"], cfg["ident"](obj, session)), id_registro=getattr(obj, "id", None)))


def _depois_do_flush(session, flush_context):
    pend = session.info.pop("_logs_pendentes", None)
    if not pend:
        return
    agora = agora_local()
    linhas = []
    for l in pend:
        obj = l.pop("_obj", None)
        if l.get("id_registro") is None and obj is not None:
            l["id_registro"] = getattr(obj, "id", None)
        l["data_hora"] = agora
        linhas.append(l)
    session.connection().execute(LogSistema.__table__.insert(), linhas)


def registrar_hooks() -> None:
    """Liga o registro automático de logs (idempotente)."""
    global _registrado
    if _registrado:
        return
    event.listen(_SASession, "before_flush", _antes_do_flush)
    event.listen(_SASession, "after_flush", _depois_do_flush)
    # se a transação for desfeita, os logs pendentes dela também são descartados
    event.listen(_SASession, "after_soft_rollback", lambda sessao, anterior: sessao.info.pop("_logs_pendentes", None))
    _registrado = True


def registrar_log(db, id_usuario, nome_usuario, acao: str, entidade: str, descricao: str, id_registro=None) -> None:
    """Log explícito (ex.: login). Não faz commit: vai junto com a transação em andamento."""
    db.add(LogSistema(id_usuario=id_usuario, usuario=nome_usuario or "Sistema", acao=acao, entidade=entidade,
                      id_registro=id_registro, descricao=descricao))


# ------------------------------------------------------------ consulta
def listar_logs(db: Session, inicio: Optional[date] = None, fim: Optional[date] = None, id_usuario: Optional[int] = None,
                entidade: Optional[str] = None, acao: Optional[str] = None, q: Optional[str] = None,
                pagina: int = 1, por_pagina: int = 20) -> dict:
    from controllers.movimentacao_controller import limites_do_periodo   # evita ciclo de importação
    pagina, por_pagina = max(1, pagina), min(max(5, por_pagina), 5000)
    stmt = select(LogSistema)
    ini, fim_excl = limites_do_periodo(inicio, fim)
    if ini:
        stmt = stmt.where(LogSistema.data_hora >= ini)
    if fim_excl:
        stmt = stmt.where(LogSistema.data_hora < fim_excl)
    if id_usuario:
        stmt = stmt.where(LogSistema.id_usuario == id_usuario)
    if entidade:
        stmt = stmt.where(LogSistema.entidade == entidade)
    if acao:
        stmt = stmt.where(LogSistema.acao == acao)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(col(LogSistema.descricao).like(like), col(LogSistema.campo).like(like),
                              col(LogSistema.valor_antigo).like(like), col(LogSistema.valor_novo).like(like)))
    total = int(db.exec(select(func.count()).select_from(stmt.subquery())).one() or 0)
    itens = db.exec(stmt.order_by(col(LogSistema.data_hora).desc(), col(LogSistema.id).desc())
                    .offset((pagina - 1) * por_pagina).limit(por_pagina)).all()
    return {
        "itens": [i.model_dump() for i in itens], "total": total, "pagina": pagina, "por_pagina": por_pagina,
        "paginas": max(1, -(-total // por_pagina)),
    }
