"""Validação e padronização de CPF, telefone, CEP e placa."""
import re
from typing import Optional


def so_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def cpf_valido(cpf: str) -> bool:
    d = so_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(d[tamanho]):
            return False
    return True


def formatar_cpf(cpf: str) -> str:
    d = so_digitos(cpf)
    if not cpf_valido(d):
        raise ValueError("CPF inválido.")
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def formatar_telefone(telefone: Optional[str]) -> Optional[str]:
    """Telefone brasileiro (DDD + 10 ou 11 dígitos) ou internacional (começa com + e tem DDI)."""
    if telefone is None or not telefone.strip():
        return None
    bruto = telefone.strip()
    d = so_digitos(bruto)
    if bruto.startswith("+"):
        if 8 <= len(d) <= 15:
            return "+" + d
        raise ValueError("Telefone internacional inválido: use + e o número com DDI (8 a 15 dígitos).")
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    raise ValueError("Telefone inválido: informe DDD + número (10 ou 11 dígitos) ou + e o DDI para número do exterior.")


def formatar_cep(cep: str) -> str:
    d = so_digitos(cep)
    if len(d) != 8:
        raise ValueError("CEP inválido: informe 8 dígitos.")
    return f"{d[:5]}-{d[5:]}"


_PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")


def formatar_placa(placa: str) -> str:
    """Aceita o padrão antigo (ABC-1234) e o Mercosul (ABC1D23)."""
    p = re.sub(r"[^A-Za-z0-9]", "", placa or "").upper()
    if not _PLACA.match(p):
        raise ValueError("Placa inválida: use ABC-1234 ou ABC1D23.")
    # padrão antigo tem número na 5ª posição e leva hífen
    return f"{p[:3]}-{p[3:]}" if p[4].isdigit() else p


def formatar_estado(uf: str) -> str:
    u = (uf or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", u):
        raise ValueError("Estado inválido: use a sigla com 2 letras (ex.: SC).")
    return u


# ----------------------------------------------------------------- CNPJ / documento
def cnpj_valido(cnpj: str) -> bool:
    d = so_digitos(cnpj)
    if len(d) != 14 or d == d[0] * 14:
        return False
    for tamanho in (12, 13):
        pesos = ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if tamanho == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
        soma = sum(int(d[i]) * pesos[i] for i in range(tamanho))
        digito = 0 if soma % 11 < 2 else 11 - soma % 11
        if digito != int(d[tamanho]):
            return False
    return True


def formatar_cnpj(cnpj: str) -> str:
    d = so_digitos(cnpj)
    if not cnpj_valido(d):
        raise ValueError("CNPJ inválido.")
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def formatar_passaporte(doc: str) -> str:
    p = re.sub(r"[^A-Za-z0-9]", "", doc or "").upper()
    if not 5 <= len(p) <= 20:
        raise ValueError("Documento estrangeiro inválido: informe de 5 a 20 letras e números.")
    return p


def formatar_documento(tipo: str, valor: str) -> str:
    """Valida e padroniza o documento conforme o tipo: CPF, CNPJ ou Passaporte."""
    if tipo == "CNPJ":
        return formatar_cnpj(valor)
    if tipo == "Passaporte":
        return formatar_passaporte(valor)
    return formatar_cpf(valor)
