from datetime import date

from servicos.excecoes import EntradaBloqueada
from servicos.inadimplencia import resumir_atraso
from servicos.limite_tentativas import LimiteTentativas

HOJE = date(2026, 10, 22)


def test_em_dia_nao_e_inadimplente():
    assert resumir_atraso([], HOJE) is None
    # vence hoje ou no futuro ainda não está em atraso
    assert resumir_atraso([(HOJE, 100.0), (date(2026, 11, 5), 100.0)], HOJE) is None
    assert resumir_atraso([(None, 100.0)], HOJE) is None


def test_dias_contam_a_partir_do_vencimento_mais_antigo():
    r = resumir_atraso([(date(2026, 10, 12), 100.0), (date(2026, 10, 20), 150.0), (date(2026, 11, 1), 90.0)], HOJE)
    assert r["dias_atraso"] == 10
    assert r["valor_em_aberto"] == 250.0
    assert r["cobrancas_vencidas"] == 2


def test_um_dia_de_atraso():
    assert resumir_atraso([(date(2026, 10, 21), 80.0)], HOJE)["dias_atraso"] == 1


def test_mensagem_de_entrada_bloqueada():
    erro = EntradaBloqueada("Maria", 12, 300.0, 2)
    assert str(erro) == "Entrada bloqueada. Cliente inadimplente há 12 dias."
    assert EntradaBloqueada("Maria", 1, 80.0, 1).args[0].endswith("há 1 dia.")
    d = erro.detalhe()
    assert d["codigo"] == "CLIENTE_INADIMPLENTE" and d["dias_atraso"] == 12 and d["valor_em_aberto"] == 300.0


def test_limite_de_tentativas_bloqueia_e_libera():
    agora = [1000.0]
    limite = LimiteTentativas(maximo=3, janela_segundos=300, relogio=lambda: agora[0])
    assert limite.segundos_bloqueado("op1") == 0
    for _ in range(3):
        limite.registrar_falha("op1")
    assert limite.segundos_bloqueado("op1") > 0
    assert limite.segundos_bloqueado("op2") == 0       # outro operador não é afetado
    agora[0] += 301                                      # passou a janela
    assert limite.segundos_bloqueado("op1") == 0


def test_acerto_limpa_as_falhas():
    limite = LimiteTentativas(maximo=2, janela_segundos=300)
    limite.registrar_falha("op")
    limite.limpar("op")
    limite.registrar_falha("op")
    assert limite.segundos_bloqueado("op") == 0
