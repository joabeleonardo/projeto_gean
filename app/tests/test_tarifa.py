from datetime import datetime, timedelta

import pytest

from servicos.tarifa import calcular_valor_hora, minutos_permanencia

ENTRADA = datetime(2026, 10, 20, 10, 0, 0)


def cobrar(minutos, valor_hora=12.0, minimo=3.0, tempo_minimo=15, segundos=0):
    saida = ENTRADA + timedelta(minutes=minutos, seconds=segundos)
    return calcular_valor_hora(ENTRADA, saida, valor_hora, minimo, tempo_minimo)


@pytest.mark.parametrize("minutos,esperado", [
    (5, 3.00),      # proporcional R$ 1,00 -> cobra o mínimo
    (10, 3.00),     # proporcional R$ 2,00 -> cobra o mínimo
    (15, 3.00),     # proporcional R$ 3,00
    (30, 6.00),
    (45, 9.00),
    (60, 12.00),
    (90, 18.00),
    (120, 24.00),
])
def test_tabela_de_exemplo_do_cliente(minutos, esperado):
    assert cobrar(minutos) == esperado


def test_passando_de_uma_hora_cobra_a_fracao_proporcional():
    assert cobrar(65) == 13.00      # 1h05
    assert cobrar(70) == 14.00      # 1h10
    assert cobrar(75) == 15.00      # 1h15


def test_minutos_incompletos_nao_sao_cobrados():
    # 30 min e 40 s continua sendo 30 min completos (a mesma base mostrada na tela)
    assert cobrar(30, segundos=40) == 6.00


def test_sem_minimo_a_cobranca_e_somente_proporcional():
    assert cobrar(5, minimo=0.0, tempo_minimo=0) == 1.00
    assert cobrar(0, minimo=0.0, tempo_minimo=0) == 0.0


def test_tempo_minimo_maior_que_o_proporcional_do_minimo():
    # mínimo de R$ 5,00 cobre até 20 min; depois vale o proporcional (R$ 12/h = R$ 0,20/min)
    assert cobrar(20, minimo=5.0, tempo_minimo=20) == 5.00
    assert cobrar(30, minimo=5.0, tempo_minimo=20) == 6.00
    assert cobrar(21, minimo=5.0, tempo_minimo=20) == 5.00   # proporcional (4,20) menor que o mínimo


def test_valor_acompanha_preco_da_hora():
    assert cobrar(90, valor_hora=8.0, minimo=2.0, tempo_minimo=15) == 12.00


def test_minutos_de_permanencia():
    assert minutos_permanencia(ENTRADA, ENTRADA + timedelta(minutes=95, seconds=30)) == 95
    assert minutos_permanencia(ENTRADA, ENTRADA - timedelta(minutes=5)) == 0
