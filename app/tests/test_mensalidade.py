from datetime import date

import pytest

from servicos.mensalidade import cabe_no_limite, plano_vigente, somar_meses, vencimentos_ate


def test_somar_meses_mantem_o_dia_da_adesao():
    assert somar_meses(date(2026, 10, 5), 1) == date(2026, 11, 5)
    assert somar_meses(date(2026, 11, 20), 2) == date(2027, 1, 20)     # vira o ano


def test_somar_meses_ajusta_para_o_ultimo_dia_do_mes_curto():
    assert somar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert somar_meses(date(2026, 1, 31), 2) == date(2026, 3, 31)      # volta ao dia 31 quando o mês permite
    assert somar_meses(date(2028, 1, 31), 1) == date(2028, 2, 29)      # ano bissexto


def test_vencimentos_comecam_na_adesao_e_acompanham_os_meses():
    assert vencimentos_ate(date(2026, 8, 10), date(2026, 10, 22)) == [date(2026, 8, 10), date(2026, 9, 10), date(2026, 10, 10)]
    assert vencimentos_ate(date(2026, 10, 22), date(2026, 10, 22)) == [date(2026, 10, 22)]


def test_plano_que_ainda_nao_comecou_nao_gera_vencimento():
    assert vencimentos_ate(date(2026, 11, 5), date(2026, 10, 22)) == []


def test_vencimentos_param_no_fim_do_plano():
    assert vencimentos_ate(date(2026, 8, 10), date(2026, 10, 22), data_fim=date(2026, 9, 15)) == [date(2026, 8, 10), date(2026, 9, 10)]


@pytest.mark.parametrize("inicio,fim,ativa,esperado", [
    (date(2026, 10, 22), None, True, True),                  # começa hoje
    (date(2026, 10, 1), None, True, True),
    (date(2026, 10, 23), None, True, False),                 # só vale a partir da adesão
    (date(2026, 10, 1), date(2026, 10, 21), True, False),    # encerrado
    (date(2026, 10, 1), date(2026, 10, 22), True, True),     # último dia ainda vale
    (date(2026, 10, 1), None, False, False),                 # cancelado
])
def test_vigencia_do_plano(inicio, fim, ativa, esperado):
    assert plano_vigente(inicio, fim, ativa, date(2026, 10, 22)) is esperado


def test_limite_de_cotas_por_vagas_de_mensalista():
    assert cabe_no_limite(10, 8, 2) is True       # ocupa exatamente as 10 vagas
    assert cabe_no_limite(10, 9, 2) is False      # passaria do limite
    assert cabe_no_limite(0, 0, 1) is False       # sem vaga de mensalista, não há plano
