"""Regra de inadimplência (sem dependência de banco).

Cliente inadimplente = tem cobrança PENDENTE com vencimento anterior a hoje.
Os dias de atraso contam a partir do vencimento mais antigo em aberto.
"""
from datetime import date
from typing import Iterable, Optional, Tuple


def resumir_atraso(cobrancas_pendentes: Iterable[Tuple[Optional[date], float]], hoje: date) -> Optional[dict]:
    vencidas = [(venc, valor) for venc, valor in cobrancas_pendentes if venc is not None and venc < hoje]
    if not vencidas:
        return None
    return {
        "dias_atraso": (hoje - min(venc for venc, _ in vencidas)).days,
        "valor_em_aberto": round(sum(valor for _, valor in vencidas), 2),
        "cobrancas_vencidas": len(vencidas),
    }
