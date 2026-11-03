"""Texto dos logs do sistema (sem banco): formatação de valores e frases legíveis."""
from datetime import date, datetime
from enum import Enum
from typing import Any

CAMPOS_SENSIVEIS = {"senha", "codigo_liberacao"}
CAMPOS_DINHEIRO = {"valor", "valor_minimo", "valor_total", "valor_recebido", "troco"}


def formatar_valor(campo: str, valor: Any) -> str:
    """Valor pronto para ler num log. Senhas e códigos nunca aparecem."""
    if campo in CAMPOS_SENSIVEIS:
        return "(alterado)" if valor not in (None, "") else "(vazio)"
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, Enum):
        valor = valor.value
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if campo in CAMPOS_DINHEIRO and isinstance(valor, (int, float)):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def frase_alteracao(usuario: str, rotulo: str, ident: str, campo: str, antigo: str, novo: str) -> str:
    return f"{usuario} alterou {rotulo} {ident}: campo {campo} de {antigo} para {novo}"


def frase_criacao(usuario: str, rotulo: str, ident: str) -> str:
    return f"{usuario} cadastrou {rotulo} {ident}"


def frase_exclusao(usuario: str, rotulo: str, ident: str) -> str:
    return f"{usuario} excluiu {rotulo} {ident}"
