from collections import defaultdict
from datetime import datetime, time, timedelta

from sqlmodel import Session, select, col
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from controllers import mensalidade_controller
from controllers.inadimplencia_controller import listar_inadimplentes
from dependencies.auth import eh_admin
from entidades.entidades import Cliente, Vaga, Movimentacao, Veiculo, Pagamento, Preco, StatusPagamentoEnum
from servicos.datas import agora_local
from servicos.tarifa import minutos_permanencia


def _v(x) -> str:
    return str(getattr(x, "value", x))


def _contagem():
    return {"total": 0, "ocupadas": 0, "livres": 0}


def resumo(usuario, db: Session) -> dict:
    """Números do painel inicial. Valores de receita só aparecem para administradores."""
    try:
        admin = eh_admin(usuario)
        agora = agora_local()
        hoje = agora.date()
        inicio_hoje = datetime.combine(hoje, time.min)
        inicio_serie = inicio_hoje - timedelta(days=6)
        inicio_mes = datetime.combine(hoje.replace(day=1), time.min)

        # ---- quem está em cada vaga agora
        vagas = db.exec(select(Vaga).order_by(Vaga.codigo_vaga)).all()
        abertas = db.exec(select(Movimentacao).where(col(Movimentacao.data_saida).is_(None))).all()
        por_vaga = {}
        for mov in abertas:
            veiculo = db.get(Veiculo, mov.id_veiculo)
            por_vaga[mov.id_vaga] = {
                "id_movimentacao": mov.id,
                "placa": veiculo.placa if veiculo else "-",
                "marca": veiculo.marca if veiculo else None,
                "modelo": veiculo.modelo if veiculo else "",
                "data_entrada": mov.data_entrada,
                "permanencia_minutos": minutos_permanencia(mov.data_entrada, agora),
            }

        # mensalidades vencidas ainda não lançadas (no máximo 1x por dia; nunca derruba o painel)
        try:
            mensalidade_controller.gerar_cobrancas_se_necessario(db)
        except Exception:
            db.rollback()

        donos_premium = {
            p.id_vaga: (db.get(Cliente, p.id_cliente).nome if db.get(Cliente, p.id_cliente) else None)
            for p in mensalidade_controller.planos_ativos(db) if _v(p.tipo_plano) == "Premium" and p.id_vaga
        }
        mapa = []
        inativas = 0
        total = _contagem()
        por_tipo = defaultdict(_contagem)          # Horista / Mensalista
        por_categoria = defaultdict(_contagem)     # Carro / Moto
        matriz = defaultdict(_contagem)            # (categoria, tipo)
        for vaga in vagas:
            tipo, categoria = _v(vaga.tipo), _v(vaga.categoria)
            if not vaga.ativa:
                # vaga inativa (reforma): aparece no mapa, mas não conta como disponível nem no total
                inativas += 1
                mapa.append({
                    "id": vaga.id, "codigo": vaga.codigo_vaga, "tipo": tipo, "categoria": categoria,
                    "status": "Inativa", "ativa": False, "id_movimentacao": None, "placa": None, "marca": None,
                    "modelo": None, "data_entrada": None, "permanencia_minutos": None,
                })
                continue
            ocupada = _v(vaga.status) == "Ocupada"
            for c in (total, por_tipo[tipo], por_categoria[categoria], matriz[(categoria, tipo)]):
                c["total"] += 1
                c["ocupadas" if ocupada else "livres"] += 1
            ocupante = por_vaga.get(vaga.id) if ocupada else None
            mapa.append({
                "id": vaga.id, "codigo": vaga.codigo_vaga, "tipo": tipo, "categoria": categoria,
                "status": _v(vaga.status), "ativa": True, "reservada_para": donos_premium.get(vaga.id),
                "id_movimentacao": ocupante["id_movimentacao"] if ocupante else None,
                "placa": ocupante["placa"] if ocupante else None,
                "marca": ocupante["marca"] if ocupante else None,
                "modelo": ocupante["modelo"] if ocupante else None,
                "data_entrada": ocupante["data_entrada"] if ocupante else None,
                "permanencia_minutos": ocupante["permanencia_minutos"] if ocupante else None,
            })

        # ---- movimentos dos últimos 7 dias (gráfico + lista de últimas movimentações)
        dias = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
        serie = {d: {"data": d.isoformat(), "entradas": 0, "saidas": 0, "receita": 0.0} for d in dias}
        movs = db.exec(select(Movimentacao).where(
            (Movimentacao.data_entrada >= inicio_serie) | (Movimentacao.data_saida >= inicio_serie)
        )).all()
        eventos = []
        for mov in movs:
            if mov.data_entrada and mov.data_entrada.date() in serie:
                serie[mov.data_entrada.date()]["entradas"] += 1
                eventos.append((mov.data_entrada, "Entrada", mov))
            if mov.data_saida and mov.data_saida.date() in serie:
                serie[mov.data_saida.date()]["saidas"] += 1
                eventos.append((mov.data_saida, "Saída", mov))
        eventos.sort(key=lambda e: e[0], reverse=True)
        ultimas = []
        for quando, tipo_evento, mov in eventos[:12]:
            veiculo = db.get(Veiculo, mov.id_veiculo)
            vaga = db.get(Vaga, mov.id_vaga)
            ultimas.append({
                "quando": quando, "tipo": tipo_evento,
                "placa": veiculo.placa if veiculo else "-",
                "veiculo": " ".join(x for x in [veiculo.marca if veiculo else None, veiculo.modelo if veiculo else None] if x),
                "vaga": vaga.codigo_vaga if vaga else "-",
            })

        # ---- receita (somente administrador)
        receita = None
        if admin:
            pagos = db.exec(select(Pagamento).where(
                Pagamento.status == StatusPagamentoEnum.Pago, Pagamento.data_pagamento >= inicio_mes
            )).all()
            receita_hoje = receita_mes = 0.0
            for pag in pagos:
                receita_mes += pag.valor_total
                if pag.data_pagamento.date() == hoje:
                    receita_hoje += pag.valor_total
                if pag.data_pagamento.date() in serie:
                    serie[pag.data_pagamento.date()]["receita"] += pag.valor_total
            qtd_pend = db.exec(select(func.count()).select_from(Pagamento).where(
                Pagamento.status == StatusPagamentoEnum.Pendente)).one()
            soma_pend = db.exec(select(func.coalesce(func.sum(Pagamento.valor_total), 0)).where(
                Pagamento.status == StatusPagamentoEnum.Pendente)).one()
            receita = {
                "hoje": round(receita_hoje, 2), "mes": round(receita_mes, 2),
                "pendentes_qtd": int(qtd_pend or 0), "pendentes_valor": round(float(soma_pend or 0), 2),
            }
        else:
            for d in serie.values():
                d["receita"] = None

        # ---- tabela de preços (todos os perfis consultam, para informar o cliente)
        precos = [
            {
                "categoria": _v(p.categoria), "tipo_cobranca": _v(p.tipo_cobranca), "valor": float(p.valor),
                "valor_minimo": float(p.valor_minimo or 0), "tempo_minimo_minutos": int(p.tempo_minimo_minutos or 0),
            }
            for p in db.exec(select(Preco)).all()
        ]

        inadimplentes = listar_inadimplentes(db)

        return {
            "vagas": {
                "total": total["total"], "ocupadas": total["ocupadas"], "livres": total["livres"],
                "inativas": inativas,
                "mensalistas": mensalidade_controller.capacidade(db),
                "por_tipo": dict(por_tipo),
                "por_categoria": dict(por_categoria),
                "matriz": [
                    {"categoria": cat, "tipo": tipo, **cont} for (cat, tipo), cont in sorted(matriz.items())
                ],
            },
            "mapa_vagas": mapa,
            "hoje": {"entradas": serie[hoje]["entradas"], "saidas": serie[hoje]["saidas"]},
            "receita": receita,
            "precos": precos,
            "inadimplentes": {
                "quantidade": len(inadimplentes),
                "valor_em_aberto": round(sum(i["valor_em_aberto"] for i in inadimplentes), 2),
                "itens": inadimplentes[:5],
            },
            "ultimas_movimentacoes": ultimas,
            "ultimos_7_dias": list(serie.values()),
        }
    except OperationalError as e:
        raise RuntimeError("Falha de comunicação com o banco de dados.") from e
