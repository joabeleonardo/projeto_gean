"""Datas e horários: convenção única (relógio local, sem fuso) e cálculo de permanência."""
import os
from datetime import datetime, timedelta, timezone

from servicos import datas
from servicos.tarifa import calcular_valor_hora, minutos_permanencia


def _com_fuso(nome, funcao):
    """Roda a função com FUSO_HORARIO definido e restaura o ambiente depois."""
    anterior = os.environ.get("FUSO_HORARIO")
    os.environ["FUSO_HORARIO"] = nome
    try:
        return funcao()
    finally:
        if anterior is None:
            os.environ.pop("FUSO_HORARIO", None)
        else:
            os.environ["FUSO_HORARIO"] = anterior


def test_agora_local_nao_tem_fuso():
    assert datas.agora_local().tzinfo is None
    assert datas.hoje_local() == datas.agora_local().date()


def test_horario_sem_fuso_nao_e_alterado():
    d = datetime(2026, 10, 22, 10, 30)
    assert datas.como_local_naive(d) == d


def test_horario_com_fuso_e_convertido_e_nao_apenas_descartado():
    # 13:00 UTC é 10:00 em Brasília (UTC-3): o horário muda, o instante é o mesmo
    utc = datetime(2026, 10, 22, 13, 0, tzinfo=timezone.utc)
    resultado = _com_fuso("America/Sao_Paulo", lambda: datas.como_local_naive(utc))
    assert resultado == datetime(2026, 10, 22, 10, 0)
    assert resultado.tzinfo is None


def test_agora_local_respeita_fuso_configurado():
    sp = _com_fuso("America/Sao_Paulo", datas.agora_local)
    utc = datetime.now(timezone.utc).replace(tzinfo=None)
    # São Paulo está 3h atrás de UTC (sem horário de verão desde 2019); tolerância de 1 min
    assert abs((utc - sp) - timedelta(hours=3)) < timedelta(minutes=1)


def test_fuso_invalido_cai_no_fuso_do_sistema_sem_quebrar():
    d = _com_fuso("Nao/Existe", datas.agora_local)
    assert d.tzinfo is None


def test_permanencia_com_entrada_naive_e_saida_naive():
    e = datetime(2026, 10, 22, 10, 0)
    assert minutos_permanencia(e, e + timedelta(minutes=95, seconds=30)) == 95


def test_permanencia_mistura_horario_com_fuso_e_sem_fuso_nao_levanta_erro():
    # reproduz o erro original: "can't subtract offset-naive and offset-aware datetimes"
    def calcular():
        entrada_aware = datetime(2026, 10, 22, 13, 0, tzinfo=timezone.utc)   # 10:00 em Brasília
        agora_naive = datetime(2026, 10, 22, 11, 25)                          # relógio local
        return minutos_permanencia(entrada_aware, agora_naive)
    assert _com_fuso("America/Sao_Paulo", calcular) == 85


def test_tarifa_com_horarios_misturados_mantem_a_regra():
    def calcular():
        entrada = datetime(2026, 10, 22, 13, 0, tzinfo=timezone.utc)          # 10:00 local
        saida = datetime(2026, 10, 22, 12, 5)                                  # 2h05 depois
        return calcular_valor_hora(entrada, saida, 12.0, 3.0, 15)
    assert _com_fuso("America/Sao_Paulo", calcular) == 25.0                    # 125 min x R$ 12/h proporcional


def test_permanencia_nunca_e_negativa():
    e = datetime(2026, 10, 22, 10, 0)
    assert minutos_permanencia(e, e - timedelta(minutes=5)) == 0
