from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlmodel import Session, select
from sqlalchemy.exc import OperationalError

from controllers.movimentacao_controller import listar_movimentacoes_detalhadas, limites_do_periodo
from controllers.pagamentos_controller import listar_pagamentos_detalhados
from entidades.entidades import Movimentacao, Pagamento, StatusPagamentoEnum
from servicos.datas import hoje_local


def _periodo_padrao(inicio: Optional[date], fim: Optional[date]):
    hoje = hoje_local()
    return inicio or hoje.replace(day=1), fim or hoje


def movimentacoes(db: Session, inicio, fim, placa, id_veiculo=None) -> dict:
    inicio, fim = _periodo_padrao(inicio, fim)
    itens = listar_movimentacoes_detalhadas(db, inicio, fim, placa, id_veiculo)
    return {
        "inicio": inicio, "fim": fim, "itens": itens,
        "totais": {
            "entradas": len(itens),
            "saidas": sum(1 for i in itens if i["data_saida"]),
            "no_patio": sum(1 for i in itens if not i["data_saida"]),
            "valor_cobrado": round(sum(i["valor_cobrado"] for i in itens), 2),
        },
    }


def por_veiculo(db: Session, inicio, fim) -> dict:
    """Uma linha por placa: quantas visitas, tempo total e quanto pagou."""
    inicio, fim = _periodo_padrao(inicio, fim)
    grupos = {}
    for i in listar_movimentacoes_detalhadas(db, inicio, fim, None):
        g = grupos.setdefault(i["placa"], {
            "placa": i["placa"], "marca": i.get("marca"), "modelo": i["modelo"], "cliente_nome": i["cliente_nome"],
            "visitas": 0, "minutos": 0, "valor_cobrado": 0.0,
        })
        g["visitas"] += 1
        g["minutos"] += i["permanencia_minutos"]
        g["valor_cobrado"] = round(g["valor_cobrado"] + i["valor_cobrado"], 2)
    itens = sorted(grupos.values(), key=lambda g: (-g["visitas"], g["placa"]))
    return {"inicio": inicio, "fim": fim, "itens": itens}


def agrupado(db: Session, periodo: str, inicio, fim) -> dict:
    """Entradas, saídas e receita por dia ou por mês."""
    try:
        inicio, fim = _periodo_padrao(inicio, fim)
        ini, fim_excl = limites_do_periodo(inicio, fim)
        chave = (lambda d: d.strftime("%Y-%m")) if periodo == "mes" else (lambda d: d.strftime("%Y-%m-%d"))
        linhas = defaultdict(lambda: {"entradas": 0, "saidas": 0, "receita": 0.0})
        for mov in db.exec(select(Movimentacao).where(
            (Movimentacao.data_entrada >= ini) & (Movimentacao.data_entrada < fim_excl)
        )).all():
            linhas[chave(mov.data_entrada)]["entradas"] += 1
        for mov in db.exec(select(Movimentacao).where(
            (Movimentacao.data_saida >= ini) & (Movimentacao.data_saida < fim_excl)
        )).all():
            linhas[chave(mov.data_saida)]["saidas"] += 1
        for pag in db.exec(select(Pagamento).where(
            Pagamento.status == StatusPagamentoEnum.Pago,
            Pagamento.data_pagamento >= ini, Pagamento.data_pagamento < fim_excl,
        )).all():
            linhas[chave(pag.data_pagamento)]["receita"] += pag.valor_total
        itens = [
            {"periodo": k, "entradas": v["entradas"], "saidas": v["saidas"], "receita": round(v["receita"], 2)}
            for k, v in sorted(linhas.items())
        ]
        return {
            "inicio": inicio, "fim": fim, "agrupado_por": periodo, "itens": itens,
            "totais": {
                "entradas": sum(i["entradas"] for i in itens),
                "saidas": sum(i["saidas"] for i in itens),
                "receita": round(sum(i["receita"] for i in itens), 2),
            },
        }
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e


def pagamentos(db: Session, inicio, fim, status, tipo, cliente=None, forma=None, id_usuario=None) -> dict:
    inicio, fim = _periodo_padrao(inicio, fim)
    itens = listar_pagamentos_detalhados(db, inicio, fim, status, tipo, cliente, forma, id_usuario)
    situacao = lambda i: str(getattr(i["status"], "value", i["status"]))
    pago = sum(i["valor_total"] for i in itens if situacao(i) == "Pago")
    pend = sum(i["valor_total"] for i in itens if situacao(i) == "Pendente")
    por_forma = defaultdict(float)
    for i in itens:
        if situacao(i) == "Pago":
            por_forma[i.get("forma_pagamento") or "Não informada"] += i["valor_total"]
    dinheiro = [i for i in itens if situacao(i) == "Pago" and i.get("forma_pagamento") == "Dinheiro"]
    return {
        "inicio": inicio, "fim": fim, "itens": itens,
        "totais": {
            "quantidade": len(itens), "total_pago": round(pago, 2), "total_pendente": round(pend, 2),
            "por_forma": {forma: round(valor, 2) for forma, valor in sorted(por_forma.items())},
            "dinheiro_recebido": round(sum(i.get("valor_recebido") or i["valor_total"] for i in dinheiro), 2),
            "troco_devolvido": round(sum(i.get("troco") or 0 for i in dinheiro), 2),
            "dinheiro_liquido": round(sum(i["valor_total"] for i in dinheiro), 2),
        },
    }


def recebimentos_por_cliente(db: Session, inicio, fim) -> dict:
    """Quanto cada cliente pagou no período (e de que forma)."""
    inicio, fim = _periodo_padrao(inicio, fim)
    grupos = {}
    for i in listar_pagamentos_detalhados(db, inicio, fim, "Pago", None):
        nome = i.get("cliente_nome") or "(sem cliente)"
        g = grupos.setdefault(nome, {"cliente": nome, "pagamentos": 0, "total_pago": 0.0, "formas": defaultdict(float), "ultimo_pagamento": None})
        g["pagamentos"] += 1
        g["total_pago"] = round(g["total_pago"] + i["valor_total"], 2)
        g["formas"][i.get("forma_pagamento") or "Não informada"] += i["valor_total"]
        if i.get("data_pagamento") and (g["ultimo_pagamento"] is None or i["data_pagamento"] > g["ultimo_pagamento"]):
            g["ultimo_pagamento"] = i["data_pagamento"]
    itens = []
    for g in sorted(grupos.values(), key=lambda g: -g["total_pago"]):
        g["formas"] = ", ".join(f"{f}: R$ {v:.2f}" for f, v in sorted(g["formas"].items()))
        itens.append(g)
    return {"inicio": inicio, "fim": fim, "itens": itens,
            "totais": {"clientes": len(itens), "total_pago": round(sum(g["total_pago"] for g in itens), 2)}}


def caixa(db: Session, inicio, fim) -> dict:
    """Fechamento de caixa: o que entrou no período, por quem recebeu e por forma de pagamento,
    com o dinheiro em espécie (valor entregue, troco devolvido e saldo líquido)."""
    inicio, fim = _periodo_padrao(inicio, fim)
    grupos = {}
    for i in listar_pagamentos_detalhados(db, inicio, fim, "Pago", None):
        chave = (i.get("recebido_por") or "(não informado)", i.get("forma_pagamento") or "Não informada")
        g = grupos.setdefault(chave, {"recebido_por": chave[0], "forma": chave[1], "pagamentos": 0, "total": 0.0, "entregue": 0.0, "troco": 0.0})
        g["pagamentos"] += 1
        g["total"] = round(g["total"] + i["valor_total"], 2)
        if chave[1] == "Dinheiro":
            g["entregue"] = round(g["entregue"] + (i.get("valor_recebido") or i["valor_total"]), 2)
            g["troco"] = round(g["troco"] + (i.get("troco") or 0), 2)
    itens = sorted(grupos.values(), key=lambda g: (g["recebido_por"], g["forma"]))
    dinheiro = [g for g in itens if g["forma"] == "Dinheiro"]
    return {"inicio": inicio, "fim": fim, "itens": itens, "totais": {
        "total_geral": round(sum(g["total"] for g in itens), 2),
        "dinheiro_entregue": round(sum(g["entregue"] for g in dinheiro), 2),
        "troco_devolvido": round(sum(g["troco"] for g in dinheiro), 2),
        "dinheiro_liquido": round(sum(g["total"] for g in dinheiro), 2),
    }}


def clientes_cadastrados(db: Session, tipo: str = "", pais: str = "", nome: str = "", documento: str = "") -> dict:
    """Todos os clientes (até 5000) com documento, contatos, plano, veículos e inadimplência."""
    from controllers.clientes_controller import listar_pagina
    from entidades.entidades import Endereco, Veiculo
    pagina = listar_pagina(db, nome=nome, documento=documento, tipo=tipo, pais=pais, ordem="nome", pagina=1, por_pagina=100)
    itens = list(pagina["itens"])
    for n in range(2, pagina["paginas"] + 1):
        if len(itens) >= 5000:
            break
        itens.extend(listar_pagina(db, nome=nome, documento=documento, tipo=tipo, pais=pais, ordem="nome", pagina=n, por_pagina=100)["itens"])
    ids = [c["id"] for c in itens]
    placas = defaultdict(list)
    if ids:
        for v in db.exec(select(Veiculo).where(Veiculo.id_cliente.in_(ids)).order_by(Veiculo.placa)).all():
            placas[v.id_cliente].append(v.placa)
    saida = []
    for c in itens:
        end = db.get(Endereco, c["id_endereco"]) if c.get("id_endereco") else None
        plano = "; ".join(
            f"{p['tipo_plano']} {p['categoria']}" + (f" vaga {p['codigo_vaga']}" if p.get("codigo_vaga") else f" {p['cotas']} cota(s)")
            for p in c["planos"]) or "Horista"
        saida.append({
            "nome": c["nome"], "documento": c["cpf"], "tipo_documento": c["tipo_documento"], "pais": c["pais"],
            "estrangeiro": c["estrangeiro"], "telefone": c["telefone"], "telefone_whatsapp": c["telefone_whatsapp"],
            "telefone2": c["telefone2"], "telefone2_whatsapp": c["telefone2_whatsapp"], "plano": plano,
            "dias_atraso": c["dias_atraso"], "veiculos": ", ".join(placas.get(c["id"], [])),
            "cidade": f"{end.cidade}/{end.estado}" if end else "",
        })
    return {"itens": saida, "totais": {
        "clientes": pagina["total"], "mensalistas": sum(1 for c in saida if c["plano"] != "Horista"),
        "inadimplentes": sum(1 for c in saida if c["dias_atraso"]), "estrangeiros": sum(1 for c in saida if c["estrangeiro"])}}


def veiculos_cadastrados(db: Session, tipo: str = "", q: str = "") -> dict:
    from controllers.veiculos_controller import listar_pagina
    pagina = listar_pagina(db, q=q, tipo=tipo, pagina=1, por_pagina=100)
    itens = list(pagina["itens"])
    for n in range(2, pagina["paginas"] + 1):
        if len(itens) >= 5000:
            break
        itens.extend(listar_pagina(db, q=q, tipo=tipo, pagina=n, por_pagina=100)["itens"])
    return {"itens": itens, "totais": {
        "veiculos": pagina["total"], "carros": sum(1 for v in itens if v["tipo_veiculo"] == "Carro"),
        "motos": sum(1 for v in itens if v["tipo_veiculo"] == "Moto"), "no_patio": sum(1 for v in itens if v["no_patio"])}}


def inadimplentes(db: Session) -> dict:
    from controllers.inadimplencia_controller import listar_inadimplentes
    itens = listar_inadimplentes(db)
    return {"itens": itens, "totais": {"clientes": len(itens), "valor_em_aberto": round(sum(i["valor_em_aberto"] for i in itens), 2)}}
