"""Pagamento em dinheiro: valor recebido e troco (sem banco, sem FastAPI)."""
from typing import Optional


def calcular_troco(valor_total: float, valor_recebido: Optional[float]) -> float:
    if valor_recebido is None:
        raise ValueError("Pagamento em dinheiro: informe o valor recebido do cliente.")
    total, recebido = round(valor_total, 2), round(valor_recebido, 2)
    if recebido < total:
        raise ValueError(
            f"O valor recebido (R$ {recebido:.2f}) é menor que o total a pagar (R$ {total:.2f})."
        )
    return round(recebido - total, 2)


def e_dinheiro(forma: Optional[str]) -> bool:
    return str(getattr(forma, "value", forma) or "") == "Dinheiro"
