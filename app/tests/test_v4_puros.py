"""Regras puras da 4ª rodada: CNPJ/passaporte/telefone internacional, troco e texto dos logs."""
from datetime import date, datetime
from enum import Enum

import pytest

from modelos import validadores as v
from servicos.caixa import calcular_troco, e_dinheiro
from servicos.logs import formatar_valor, frase_alteracao, frase_criacao, frase_exclusao


# ----------------------------------------------------------------------- CNPJ
def test_cnpj_valido_e_formatacao():
    assert v.cnpj_valido("11.222.333/0001-81")
    assert v.formatar_cnpj("11222333000181") == "11.222.333/0001-81"


@pytest.mark.parametrize("cnpj", ["11.222.333/0001-82", "00.000.000/0000-00", "123", ""])
def test_cnpj_invalido(cnpj):
    assert not v.cnpj_valido(cnpj)
    with pytest.raises(ValueError):
        v.formatar_cnpj(cnpj)


def test_documento_conforme_o_tipo():
    assert v.formatar_documento("CPF", "52998224725") == "529.982.247-25"
    assert v.formatar_documento("CNPJ", "11222333000181") == "11.222.333/0001-81"
    assert v.formatar_documento("Passaporte", "ab-123456") == "AB123456"


def test_cpf_nao_vale_como_cnpj_e_vice_versa():
    with pytest.raises(ValueError):
        v.formatar_documento("CNPJ", "529.982.247-25")
    with pytest.raises(ValueError):
        v.formatar_documento("CPF", "11.222.333/0001-81")


def test_passaporte_exige_5_a_20_caracteres():
    with pytest.raises(ValueError):
        v.formatar_documento("Passaporte", "AB1")


# ------------------------------------------------------------------- telefone
def test_telefone_internacional_e_brasileiro():
    assert v.formatar_telefone("+55 48 99999-8888") == "+5548999998888"
    assert v.formatar_telefone("+1 (305) 555-0100") == "+13055550100"
    assert v.formatar_telefone("(48)99999-8888") == "(48) 99999-8888"
    with pytest.raises(ValueError):
        v.formatar_telefone("+12")
    with pytest.raises(ValueError):
        v.formatar_telefone("12345")


# ---------------------------------------------------------------------- troco
def test_troco_do_exemplo_do_cliente():
    assert calcular_troco(120.0, 200.0) == 80.0          # conta de R$ 120 paga com nota de R$ 200


def test_sem_troco_quando_paga_exato():
    assert calcular_troco(120.0, 120.0) == 0.0


def test_valor_recebido_menor_que_o_total_e_recusado():
    with pytest.raises(ValueError, match="menor"):
        calcular_troco(120.0, 100.0)


def test_dinheiro_exige_informar_o_valor_recebido():
    with pytest.raises(ValueError, match="valor recebido"):
        calcular_troco(120.0, None)


def test_troco_sem_erro_de_ponto_flutuante():
    assert calcular_troco(0.1 + 0.2, 1.0) == 0.7


def test_identifica_pagamento_em_dinheiro():
    assert e_dinheiro("Dinheiro") and not e_dinheiro("Pix") and not e_dinheiro(None)


# ----------------------------------------------------------------------- logs
class _Perfil(str, Enum):
    Operador = "Operador"


def test_formatacao_dos_valores_do_log():
    assert formatar_valor("valor", 12) == "R$ 12,00"
    assert formatar_valor("valor_minimo", 1234.5) == "R$ 1.234,50"
    assert formatar_valor("ativa", False) == "Não"
    assert formatar_valor("telefone", None) == "—"
    assert formatar_valor("perfil", _Perfil.Operador) == "Operador"
    assert formatar_valor("data_inicio", date(2026, 10, 23)) == "23/10/2026"
    assert formatar_valor("data_pagamento", datetime(2026, 10, 23, 9, 5)) == "23/10/2026 09:05"


def test_senha_e_codigo_nunca_aparecem_no_log():
    assert formatar_valor("senha", "pbkdf2_sha256$600000$abc$def") == "(alterado)"
    assert "pbkdf2" not in formatar_valor("codigo_liberacao", "pbkdf2_sha256$x")


def test_frases_do_log():
    assert frase_alteracao("Ana", "o preço", "Horista (Carro)", "valor", "R$ 12,00", "R$ 15,00") == \
        "Ana alterou o preço Horista (Carro): campo valor de R$ 12,00 para R$ 15,00"
    assert frase_criacao("Ana", "o veículo", "ABC-1234") == "Ana cadastrou o veículo ABC-1234"
    assert frase_exclusao("Ana", "a vaga", "A01") == "Ana excluiu a vaga A01"
