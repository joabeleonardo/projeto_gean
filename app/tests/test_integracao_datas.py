"""Teste de integração das datas: banco SQLite em memória, controllers reais.

Cobre o fluxo que falhava com SQLModel >= 0.0.45: entrada, consulta, dashboard,
saída com tarifa e relatórios por período (primeiro e último dia).
Não precisa de MySQL. As triggers de auditoria não existem aqui (o código as ignora fora do MySQL).
"""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import DateTime, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from controllers import dashboard_controller, movimentacao_controller, relatorios_controller
from entidades.entidades import (
    CategoriaEnum, Cliente, Movimentacao, Pagamento, Preco, StatusPagamentoEnum, TipoCobrancaEnum,
    TipoPagamentoEnum, TipoVagaEnum, Usuario, Vaga, Veiculo, StatusVagaEnum,
)
from modelos.schemas import FormaPagamentoEnum, MovimentacaoEntradaCreate, MovimentacaoSaidaUpdate
from servicos.datas import agora_local


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao


@pytest.fixture()
def cenario(db):
    """Um administrador, um cliente com um carro, uma vaga de horista e o preço da hora (R$ 8,00)."""
    admin = Usuario(nome="Admin Teste", login="admin", senha="x", perfil="Administrador")
    cliente = Cliente(nome="Maria Souza", cpf="529.982.247-25")
    db.add(admin)
    db.add(cliente)
    db.flush()
    veiculo = Veiculo(placa="ABC-1234", marca="Honda", modelo="Civic", id_cliente=cliente.id)
    vaga = Vaga(codigo_vaga="A01", tipo=TipoVagaEnum.Horista)
    db.add(veiculo)
    db.add(vaga)
    db.add(Preco(categoria=CategoriaEnum.Carro, tipo_cobranca=TipoCobrancaEnum.Horista, valor=8.0))
    db.commit()
    for obj in (admin, cliente, veiculo, vaga):
        db.refresh(obj)
    return {"admin": admin, "cliente": cliente, "veiculo": veiculo, "vaga": vaga}


def _entrada(c):
    return MovimentacaoEntradaCreate(
        id_veiculo=c["veiculo"].id, id_vaga=c["vaga"].id, id_usuario_entrada=c["admin"].id,
        id_usuario_logado=c["admin"].id, nome_usuario_logado=c["admin"].nome,
    )


def _saida(c, forma=FormaPagamentoEnum.Pix):
    return MovimentacaoSaidaUpdate(
        id_usuario_saida=c["admin"].id, id_usuario_logado=c["admin"].id,
        nome_usuario_logado=c["admin"].nome, forma_pagamento=forma,
    )


# ------------------------------------------------------------ tipo das colunas
def test_colunas_de_data_sao_datetime_sem_fuso():
    for coluna in (Movimentacao.__table__.c.data_entrada, Movimentacao.__table__.c.data_saida,
                   Pagamento.__table__.c.data_pagamento):
        assert isinstance(coluna.type, DateTime)
        assert coluna.type.timezone is False
        assert type(coluna.type).__name__ != "UTCDateTime"


# ------------------------------------------------------------------- entrada
def test_registrar_entrada_grava_horario_sem_fuso(db, cenario):
    mov = movimentacao_controller.registrar_entrada(_entrada(cenario), db)
    assert mov.id is not None
    assert mov.data_entrada.tzinfo is None
    assert abs(agora_local() - mov.data_entrada) < timedelta(minutes=1)
    assert db.get(Vaga, cenario["vaga"].id).status == StatusVagaEnum.Ocupada


def test_consultar_movimentacoes(db, cenario):
    movimentacao_controller.registrar_entrada(_entrada(cenario), db)
    lista = movimentacao_controller.buscar_movimentacoes(db)
    assert len(lista) == 1 and lista[0].data_saida is None


def test_mesma_placa_nao_entra_duas_vezes(db, cenario):
    movimentacao_controller.registrar_entrada(_entrada(cenario), db)
    with pytest.raises(ValueError):
        movimentacao_controller.registrar_entrada(_entrada(cenario), db)


# ----------------------------------------------------------------- dashboard
def test_dashboard_carrega_com_veiculo_no_patio(db, cenario):
    movimentacao_controller.registrar_entrada(_entrada(cenario), db)
    r = dashboard_controller.resumo(cenario["admin"], db)     # antes: TypeError (naive x aware)
    assert r["vagas"]["total"] == 1 and r["vagas"]["ocupadas"] == 1 and r["vagas"]["livres"] == 0
    assert r["hoje"]["entradas"] == 1
    ocupada = r["mapa_vagas"][0]
    assert ocupada["placa"] == "ABC-1234" and ocupada["permanencia_minutos"] >= 0
    assert r["ultimas_movimentacoes"][0]["tipo"] == "Entrada"


def test_dashboard_sem_movimentacoes(db, cenario):
    r = dashboard_controller.resumo(cenario["admin"], db)
    assert r["vagas"]["livres"] == 1 and r["hoje"]["entradas"] == 0


# ------------------------------------------------------------- saída e tarifa
def _entrada_ha(db, c, minutos):
    mov = movimentacao_controller.registrar_entrada(_entrada(c), db)
    mov.data_entrada = agora_local() - timedelta(minutes=minutos)
    db.add(mov)
    db.commit()
    return mov


def test_previa_e_saida_calculam_permanencia_e_tarifa(db, cenario):
    mov = _entrada_ha(db, cenario, 125)                       # 2h05 a R$ 8,00/h, proporcional por minuto
    previa = movimentacao_controller.previa_saida(mov.id, db)
    assert previa["permanencia_minutos"] == 125
    assert previa["valor_total"] == 16.67

    resposta = movimentacao_controller.registrar_saida(mov.id, _saida(cenario), db)
    assert resposta["valor_total"] == 16.67 and resposta["permanencia_minutos"] == 125
    assert resposta["data_saida"].tzinfo is None

    pagamento = db.exec(select(Pagamento)).one()
    assert pagamento.valor_total == 16.67 and pagamento.forma_pagamento == "Pix"
    assert pagamento.status == StatusPagamentoEnum.Pago and pagamento.data_pagamento.tzinfo is None
    assert db.get(Vaga, cenario["vaga"].id).status == StatusVagaEnum.Livre


def test_permanencia_curta_cobra_o_valor_minimo(db, cenario):
    preco = db.exec(select(Preco)).one()
    preco.valor_minimo, preco.tempo_minimo_minutos = 3.0, 15
    db.add(preco)
    db.commit()
    mov = _entrada_ha(db, cenario, 5)                          # 5 min: proporcional R$ 0,67 -> mínimo R$ 3,00
    resposta = movimentacao_controller.registrar_saida(mov.id, _saida(cenario), db)
    assert resposta["valor_total"] == 3.0
    assert db.exec(select(Pagamento)).one().valor_total == 3.0


def test_saida_exige_forma_de_pagamento_quando_ha_valor(db, cenario):
    mov = _entrada_ha(db, cenario, 125)
    with pytest.raises(ValueError):
        movimentacao_controller.registrar_saida(mov.id, _saida(cenario, forma=None), db)
    assert db.get(Movimentacao, mov.id).data_saida is None     # nada foi gravado


# ------------------------------------------- registros existentes continuam iguais
def test_horario_ja_gravado_no_banco_nao_e_deslocado(db, cenario):
    """Linha gravada como DATETIME 'puro' (como os registros antigos) volta com o mesmo horário."""
    db.execute(text(
        "INSERT INTO tb_movimentacao (id_veiculo, id_vaga, data_entrada, id_usuario_entrada) "
        "VALUES (:v, :g, '2026-10-20 10:00:00', :u)"
    ), {"v": cenario["veiculo"].id, "g": cenario["vaga"].id, "u": cenario["admin"].id})
    db.commit()
    mov = db.exec(select(Movimentacao)).one()
    assert mov.data_entrada == datetime(2026, 10, 20, 10, 0, 0)
    assert mov.data_entrada.tzinfo is None


# ---------------------------------------------------------- relatórios / filtros
def _movs_nas_bordas(db, c):
    """Entradas: 30/09 23:59:59 (fora), 01/10 00:00:00 (dentro), 22/10 23:59:59 (dentro), 23/10 00:00:00 (fora)."""
    for quando in (datetime(2026, 9, 30, 23, 59, 59), datetime(2026, 10, 1, 0, 0, 0),
                   datetime(2026, 10, 22, 23, 59, 59), datetime(2026, 10, 23, 0, 0, 0)):
        db.add(Movimentacao(id_veiculo=c["veiculo"].id, id_vaga=c["vaga"].id, id_usuario_entrada=c["admin"].id,
                            data_entrada=quando, data_saida=quando + timedelta(hours=1)))
    db.commit()


def test_relatorio_movimentacoes_inclui_primeiro_e_ultimo_dia(db, cenario):
    _movs_nas_bordas(db, cenario)
    r = relatorios_controller.movimentacoes(db, date(2026, 10, 1), date(2026, 10, 22), None)
    entradas = sorted(i["data_entrada"] for i in r["itens"])
    assert entradas == [datetime(2026, 10, 1, 0, 0, 0), datetime(2026, 10, 22, 23, 59, 59)]
    assert r["totais"]["entradas"] == 2


def test_relatorio_de_um_unico_dia(db, cenario):
    _movs_nas_bordas(db, cenario)
    r = relatorios_controller.movimentacoes(db, date(2026, 10, 22), date(2026, 10, 22), None)
    assert [i["data_entrada"] for i in r["itens"]] == [datetime(2026, 10, 22, 23, 59, 59)]


def test_relatorio_agrupado_por_dia(db, cenario):
    _movs_nas_bordas(db, cenario)
    r = relatorios_controller.agrupado(db, "dia", date(2026, 10, 1), date(2026, 10, 22))
    assert r["totais"]["entradas"] == 2
    assert r["totais"]["saidas"] == 2      # saídas em 01/10 00:59:59 e 01/10 01:00:00
    assert {i["periodo"] for i in r["itens"]} == {"2026-10-01", "2026-10-22"}


def test_relatorio_por_veiculo_e_pagamentos_por_periodo(db, cenario):
    _movs_nas_bordas(db, cenario)
    c = cenario["cliente"]
    db.add(Pagamento(tipo_cobranca=TipoPagamentoEnum.Mensal, id_cliente=c.id, valor_total=100.0,
                     status=StatusPagamentoEnum.Pago, forma_pagamento="Pix",
                     data_pagamento=datetime(2026, 10, 22, 23, 59, 59)))           # dentro (último dia)
    db.add(Pagamento(tipo_cobranca=TipoPagamentoEnum.Mensal, id_cliente=c.id, valor_total=100.0,
                     status=StatusPagamentoEnum.Pago, forma_pagamento="Pix",
                     data_pagamento=datetime(2026, 10, 23, 0, 0, 0)))              # fora
    db.add(Pagamento(tipo_cobranca=TipoPagamentoEnum.Mensal, id_cliente=c.id, valor_total=50.0,
                     status=StatusPagamentoEnum.Pendente, data_vencimento=date(2026, 10, 1)))   # dentro (1º dia)
    db.commit()

    por_veiculo = relatorios_controller.por_veiculo(db, date(2026, 10, 1), date(2026, 10, 22))
    assert por_veiculo["itens"][0]["visitas"] == 2

    pag = relatorios_controller.pagamentos(db, date(2026, 10, 1), date(2026, 10, 22), None, None)
    assert pag["totais"]["quantidade"] == 2
    assert pag["totais"]["total_pago"] == 100.0 and pag["totais"]["total_pendente"] == 50.0
    assert pag["totais"]["por_forma"] == {"Pix": 100.0}
