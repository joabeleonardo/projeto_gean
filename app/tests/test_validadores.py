import pytest

from modelos import validadores as v


def test_cpf_valido_e_formatacao():
    assert v.cpf_valido("529.982.247-25")
    assert v.formatar_cpf("52998224725") == "529.982.247-25"


@pytest.mark.parametrize("cpf", ["111.111.111-11", "529.982.247-24", "123", ""])
def test_cpf_invalido(cpf):
    assert not v.cpf_valido(cpf)
    with pytest.raises(ValueError):
        v.formatar_cpf(cpf)


def test_telefone():
    assert v.formatar_telefone("48999998888") == "(48) 99999-8888"
    assert v.formatar_telefone("4833334444") == "(48) 3333-4444"
    assert v.formatar_telefone("") is None
    assert v.formatar_telefone(None) is None
    with pytest.raises(ValueError):
        v.formatar_telefone("12345")


def test_cep():
    assert v.formatar_cep("89580000") == "89580-000"
    with pytest.raises(ValueError):
        v.formatar_cep("123")


@pytest.mark.parametrize("entrada,esperado", [
    ("abc1234", "ABC-1234"),   # padrão antigo
    ("ABC-1234", "ABC-1234"),
    ("abc1d23", "ABC1D23"),    # Mercosul
])
def test_placa_valida(entrada, esperado):
    assert v.formatar_placa(entrada) == esperado


@pytest.mark.parametrize("placa", ["AB-1234", "1234ABC", "ABCDEFG", ""])
def test_placa_invalida(placa):
    with pytest.raises(ValueError):
        v.formatar_placa(placa)


def test_estado():
    assert v.formatar_estado("sc") == "SC"
    with pytest.raises(ValueError):
        v.formatar_estado("S")
