"""Regras puras do plano de mensalista (sem banco): ciclos de cobrança, vigência e limite de cotas."""
import calendar
from datetime import date
from typing import List, Optional


def somar_meses(base: date, meses: int) -> date:
    """Soma meses mantendo o dia da adesão (ajusta para o último dia quando o mês é mais curto)."""
    indice = base.month - 1 + meses
    ano, mes = base.year + indice // 12, indice % 12 + 1
    return date(ano, mes, min(base.day, calendar.monthrange(ano, mes)[1]))


def vencimentos_ate(data_inicio: date, hoje: date, data_fim: Optional[date] = None, limite: int = 120) -> List[date]:
    """Datas de vencimento do plano que já chegaram: adesão, +1 mês, +2 meses... até hoje (ou até o fim do plano)."""
    datas = []
    for k in range(limite):
        d = somar_meses(data_inicio, k)
        if d > hoje or (data_fim is not None and d > data_fim):
            break
        datas.append(d)
    return datas


def plano_vigente(data_inicio: date, data_fim: Optional[date], ativa: bool, hoje: date) -> bool:
    """O plano vale a partir da data de adesão e até o cancelamento."""
    return bool(ativa) and data_inicio <= hoje and (data_fim is None or data_fim >= hoje)


def cabe_no_limite(vagas_mensalista: int, cotas_contratadas: int, novas_cotas: int) -> bool:
    """Nunca pode haver mais cotas de mensalista do que vagas de mensalista."""
    return cotas_contratadas + novas_cotas <= vagas_mensalista
