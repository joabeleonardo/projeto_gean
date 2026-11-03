"""Regra de cobrança por hora (sem dependência de banco ou FastAPI).

Cobrança PROPORCIONAL por minuto, com valor mínimo e tempo mínimo configuráveis
(por categoria, na tabela de preços):

    proporcional = valor_hora * minutos / 60

    * até `tempo_minimo_min` minutos  -> cobra o `valor_minimo`;
    * depois                          -> cobra o maior entre o proporcional e o `valor_minimo`.

Exemplo (R$ 12,00/h, mínimo R$ 3,00 até 15 min):
    5 min -> 3,00 | 15 min -> 3,00 | 30 min -> 6,00 | 1h -> 12,00 | 1h30 -> 18,00 | 2h -> 24,00
"""
from datetime import datetime

from servicos.datas import como_local_naive


def minutos_permanencia(entrada: datetime, saida: datetime) -> int:
    """Minutos completos entre a entrada e a saída (mesma base usada na cobrança e na tela)."""
    # como_local_naive: se algum dos horários vier com fuso, é convertido (não descartado)
    segundos = (como_local_naive(saida) - como_local_naive(entrada)).total_seconds()
    return max(0, int(segundos // 60))


def calcular_valor_hora(
    entrada: datetime,
    saida: datetime,
    valor_hora: float,
    valor_minimo: float = 0.0,
    tempo_minimo_min: int = 0,
) -> float:
    minutos = minutos_permanencia(entrada, saida)
    proporcional = round(valor_hora * minutos / 60, 2)
    valor_minimo = valor_minimo or 0.0
    if valor_minimo > 0 and minutos <= (tempo_minimo_min or 0):
        return round(valor_minimo, 2)
    return round(max(valor_minimo, proporcional), 2)
