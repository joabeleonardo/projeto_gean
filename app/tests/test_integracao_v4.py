"""Integração (SQLite em memória) da 4ª rodada: CNPJ/estrangeiro, vagas premium, troco, liberação por
código registrada, logs do sistema e paginação."""
from datetime import timedelta

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from controllers import (
    cadastro_controller, clientes_controller, logs, mensalidade_controller, movimentacao_controller,
    pagamentos_controller, relatorios_controller, vagas_controller,
)
from controllers.auditoria import aplicar_auditoria
from entidades.entidades import (
    CategoriaEnum, Cliente, LogSistema, Movimentacao, Pagamento, Preco, StatusPagamentoEnum, TipoCobrancaEnum,
    TipoPagamentoEnum, TipoVagaEnum, Usuario, Vaga, Veiculo,
)
from modelos.schemas import (
    CadastroCompletoCreate, ClienteAtualizar, ClienteEdicao, ClienteEntrada, FormaPagamentoEnum, MensalidadeCreate,
    MensalidadeEntrada, MovimentacaoEntradaCreate, MovimentacaoSaidaUpdate, VeiculoEntrada,
)
from servicos.datas import agora_local, hoje_local
from servicos.excecoes import CotasEsgotadas
from servicos.seguranca import gerar_hash_senha


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao


@pytest.fixture()
def base(db):
    """Admin (com código de liberação 1234), operador, preços e vagas: M01 mensalista, H01 horista, P01/P02 premium."""
    admin = Usuario(nome="Admin Teste", login="admin", senha="x", perfil="Administrador", codigo_liberacao=gerar_hash_senha("1234"))
    operador = Usuario(nome="Operador Teste", login="op", senha="x", perfil="Operador")
    db.add(admin)
    db.add(operador)
    for tipo, valor in ((TipoCobrancaEnum.Horista, 12.0), (TipoCobrancaEnum.Mensalista, 250.0), (TipoCobrancaEnum.Premium, 400.0)):
        db.add(Preco(categoria=CategoriaEnum.Carro, tipo_cobranca=tipo, valor=valor))
    vagas = {c: Vaga(codigo_vaga=c, tipo=t) for c, t in (
        ("M01", TipoVagaEnum.Mensalista), ("H01", TipoVagaEnum.Horista), ("H02", TipoVagaEnum.Horista),
        ("P01", TipoVagaEnum.Premium), ("P02", TipoVagaEnum.Premium))}
    for v in vagas.values():
        db.add(v)
    db.commit()
    for obj in [admin, operador, *vagas.values()]:
        db.refresh(obj)
    return {"admin": admin, "operador": operador, "vagas": vagas}


def _cadastro(nome, cpf, placa, mensalidade=None, **cliente):
    return CadastroCompletoCreate(
        cliente=ClienteEntrada(nome=nome, cpf=cpf, telefone="48999998888", **cliente),
        veiculo=VeiculoEntrada(placa=placa, marca="Honda", modelo="Civic") if placa else None,
        mensalidade=mensalidade,
    )


def _entrar(db, base, veiculo_id, vaga, usuario=None, **extra):
    u = usuario or base["admin"]
    return movimentacao_controller.registrar_entrada(MovimentacaoEntradaCreate(
        id_veiculo=veiculo_id, id_vaga=base["vagas"][vaga].id, id_usuario_entrada=u.id,
        id_usuario_logado=u.id, nome_usuario_logado=u.nome, **extra), db)


def _saida(base, forma=FormaPagamentoEnum.Pix, recebido=None):
    return MovimentacaoSaidaUpdate(
        id_usuario_saida=base["admin"].id, id_usuario_logado=base["admin"].id, nome_usuario_logado="Admin Teste",
        forma_pagamento=forma, valor_recebido=recebido)


def _entrada_ha(db, base, veiculo_id, vaga, minutos):
    mov = _entrar(db, base, veiculo_id, vaga)
    mov.data_entrada = agora_local() - timedelta(minutes=minutos)
    db.add(mov)
    db.commit()
    return mov


# ---------------------------------------------------------- CNPJ e estrangeiro
def test_cliente_pessoa_juridica_com_cnpj(db, base):
    r = cadastro_controller.cadastrar_completo(
        _cadastro("Empresa Teste Ltda", "11222333000181", "ABC-1234", tipo_documento="CNPJ"), base["admin"], db)
    cliente = db.get(Cliente, r["cliente"]["id"])
    assert cliente.cpf == "11.222.333/0001-81" and cliente.tipo_documento.value == "CNPJ"
    with pytest.raises(ValueError, match="CNPJ inválido"):
        ClienteEntrada(nome="Empresa X", cpf="529.982.247-25", tipo_documento="CNPJ")


def test_cliente_estrangeiro_com_passaporte_e_telefone_internacional(db, base):
    r = cadastro_controller.cadastrar_completo(CadastroCompletoCreate(cliente=ClienteEntrada(
        nome="John Smith", tipo_documento="Passaporte", cpf="x1234567", pais="Estados Unidos",
        telefone="+1 305 555 0100", telefone_whatsapp=True)), base["admin"], db)
    cliente = db.get(Cliente, r["cliente"]["id"])
    assert cliente.cpf == "X1234567" and cliente.pais == "Estados Unidos" and cliente.telefone == "+13055550100"
    assert cliente.telefone_whatsapp is True
    estrangeiros = clientes_controller.listar_pagina(db, pais="estrangeiro")
    assert [c["nome"] for c in estrangeiros["itens"]] == ["John Smith"] and estrangeiros["itens"][0]["estrangeiro"] is True
    assert clientes_controller.listar_pagina(db, pais="brasil")["total"] == 0


def test_segundo_telefone_exige_o_primeiro_e_whatsapp_so_com_numero():
    with pytest.raises(ValueError, match="telefone principal"):
        ClienteEdicao(nome="Maria Souza", telefone2="48999998888")
    c = ClienteEdicao(nome="Maria Souza", telefone_whatsapp=True)       # marcou WhatsApp sem número
    assert c.telefone_whatsapp is False


# ------------------------------------------------------------------ vagas premium
def _premium(db, base, vaga="P01", nome="Maria Souza", cpf="529.982.247-25", placa="ABC-1234"):
    return cadastro_controller.cadastrar_completo(_cadastro(
        nome, cpf, placa, MensalidadeEntrada(tipo_plano="Premium", id_vaga=base["vagas"][vaga].id)), base["admin"], db)


def test_plano_premium_reserva_a_vaga_e_cobra_o_preco_premium(db, base):
    r = _premium(db, base)
    assert r["mensalidade"]["tipo_plano"] == "Premium" and r["mensalidade"]["cotas"] == 1
    assert db.exec(select(Pagamento)).one().valor_total == 400.0
    veiculo = db.exec(select(Veiculo)).one()
    modo = movimentacao_controller.consultar_modo_entrada(veiculo.id, db)
    assert modo["modo"] == "Premium" and modo["vaga_premium"]["codigo"] == "P01"
    with pytest.raises(ValueError, match="vaga exclusiva P01"):
        _entrar(db, base, veiculo.id, "H01")
    _entrar(db, base, veiculo.id, "P01")


def test_vaga_premium_nao_pode_ser_reservada_por_dois_clientes(db, base):
    _premium(db, base)
    with pytest.raises(ValueError, match="já está reservada"):
        _premium(db, base, vaga="P01", nome="Joao Lima", cpf="111.444.777-35", placa="XYZ-1A23")
    _premium(db, base, vaga="P02", nome="Joao Lima", cpf="111.444.777-35", placa="XYZ-1A23")


def test_vaga_premium_e_exclusiva_do_titular(db, base):
    _premium(db, base)                                           # P01 é da Maria
    outro = cadastro_controller.cadastrar_completo(_cadastro("Joao Lima", "111.444.777-35", "XYZ-1A23"), base["admin"], db)
    carro_do_joao = db.exec(select(Veiculo).where(Veiculo.placa == "XYZ1A23")).one()
    with pytest.raises(ValueError, match="premium e exclusiva"):
        _entrar(db, base, carro_do_joao.id, "P01")
    assert outro["cliente"]["id"] != 0


def test_segundo_veiculo_do_titular_premium_com_vaga_ocupada_pergunta_se_entra_como_horista(db, base):
    r = _premium(db, base)
    carro_a = db.exec(select(Veiculo)).one()
    carro_b = Veiculo(placa="DEF-5678", marca="Fiat", modelo="Uno", id_cliente=r["cliente"]["id"])
    db.add(carro_b)
    db.commit()
    db.refresh(carro_b)
    _entrar(db, base, carro_a.id, "P01")
    with pytest.raises(CotasEsgotadas) as erro:
        _entrar(db, base, carro_b.id, "H01")
    assert erro.value.placas_em_uso == ["ABC-1234"]
    _entrar(db, base, carro_b.id, "H01", como_horista=True)


def test_premium_mais_rotativo_usa_a_vaga_exclusiva_primeiro_e_a_rotativa_depois(db, base):
    r = _premium(db, base)
    mensalidade_controller.aderir(MensalidadeCreate(
        id_cliente=r["cliente"]["id"], tipo_plano="Rotativo", cotas=1, id_usuario_logado=base["admin"].id,
        nome_usuario_logado="Admin"), base["admin"], db)
    carro_a = db.exec(select(Veiculo)).one()
    carro_b = Veiculo(placa="DEF-5678", marca="Fiat", modelo="Uno", id_cliente=r["cliente"]["id"])
    db.add(carro_b)
    db.commit()
    db.refresh(carro_b)
    _entrar(db, base, carro_a.id, "P01")
    assert movimentacao_controller.consultar_modo_entrada(carro_b.id, db)["modo"] == "Mensalista"
    _entrar(db, base, carro_b.id, "M01")


def test_vaga_premium_reservada_nao_pode_ser_inativada_ate_cancelar_o_plano(db, base):
    r = _premium(db, base)
    with pytest.raises(ValueError, match="reservada para Maria Souza"):
        vagas_controller.definir_situacao(base["vagas"]["P01"].id, False, base["admin"], db)
    mensalidade_controller.cancelar(r["mensalidade"]["id"], base["admin"], db)
    vagas_controller.definir_situacao(base["vagas"]["P01"].id, False, base["admin"], db)


def test_capacidade_informa_as_vagas_premium(db, base):
    _premium(db, base)
    carro = next(c for c in mensalidade_controller.capacidade(db) if c["categoria"] == "Carro")
    assert carro["vagas_premium"] == 2 and carro["premium_atribuidas"] == 1 and carro["premium_livres"] == 1


# ---------------------------------------------------------------------- troco
def test_saida_em_dinheiro_calcula_o_troco(db, base):
    cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    veiculo = db.exec(select(Veiculo)).one()
    mov = _entrada_ha(db, base, veiculo.id, "H01", 600)                        # 10 h x R$ 12 = R$ 120
    with pytest.raises(ValueError, match="menor"):
        movimentacao_controller.registrar_saida(mov.id, _saida(base, FormaPagamentoEnum.Dinheiro, 100.0), db)
    assert db.get(Movimentacao, mov.id).data_saida is None                      # nada foi gravado
    with pytest.raises(ValueError, match="valor recebido"):
        movimentacao_controller.registrar_saida(mov.id, _saida(base, FormaPagamentoEnum.Dinheiro, None), db)
    resposta = movimentacao_controller.registrar_saida(mov.id, _saida(base, FormaPagamentoEnum.Dinheiro, 200.0), db)
    assert resposta["valor_total"] == 120.0 and resposta["troco"] == 80.0
    pagamento = db.exec(select(Pagamento)).one()
    assert pagamento.valor_recebido == 200.0 and pagamento.troco == 80.0


def test_pagamento_por_pix_nao_tem_troco(db, base):
    cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    mov = _entrada_ha(db, base, db.exec(select(Veiculo)).one().id, "H01", 600)
    movimentacao_controller.registrar_saida(mov.id, _saida(base, FormaPagamentoEnum.Pix), db)
    pagamento = db.exec(select(Pagamento)).one()
    assert pagamento.troco is None and pagamento.valor_recebido is None


def test_baixa_de_mensalidade_em_dinheiro_registra_troco(db, base):
    cadastro_controller.cadastrar_completo(_cadastro(
        "Maria Souza", "529.982.247-25", "ABC-1234", MensalidadeEntrada(cotas=1)), base["admin"], db)
    pendente = db.exec(select(Pagamento)).one()
    with pytest.raises(ValueError, match="valor recebido"):
        pagamentos_controller.baixar_pagamento(pendente.id, FormaPagamentoEnum.Dinheiro, base["admin"], db)
    pago = pagamentos_controller.baixar_pagamento(pendente.id, FormaPagamentoEnum.Dinheiro, base["admin"], db, 300.0)
    assert pago.troco == 50.0 and pago.valor_recebido == 300.0 and pago.status == StatusPagamentoEnum.Pago


def test_caixa_resume_dinheiro_entregue_troco_e_liquido(db, base):
    cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    mov = _entrada_ha(db, base, db.exec(select(Veiculo)).one().id, "H01", 600)
    movimentacao_controller.registrar_saida(mov.id, _saida(base, FormaPagamentoEnum.Dinheiro, 200.0), db)
    r = relatorios_controller.caixa(db, hoje_local(), hoje_local())
    assert r["totais"]["dinheiro_entregue"] == 200.0 and r["totais"]["troco_devolvido"] == 80.0
    assert r["totais"]["dinheiro_liquido"] == 120.0 and r["itens"][0]["recebido_por"] == "Admin Teste"


# ------------------------------------------------- liberação por código registrada
def test_liberacao_por_codigo_fica_registrada_na_movimentacao_e_no_relatorio(db, base):
    r = cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    db.add(Pagamento(id_cliente=r["cliente"]["id"], tipo_cobranca=TipoPagamentoEnum.Mensal, valor_total=250.0,
                     data_vencimento=hoje_local() - timedelta(days=12), status=StatusPagamentoEnum.Pendente))
    db.commit()
    veiculo = db.exec(select(Veiculo)).one()
    mov = _entrar(db, base, veiculo.id, "H01", usuario=base["operador"], codigo_liberacao="1234")
    assert mov.id_usuario_liberacao == base["admin"].id and "inadimplente há 12 dia(s)" in mov.obs_liberacao

    itens = relatorios_controller.movimentacoes(db, hoje_local(), hoje_local(), None)["itens"]
    assert itens[0]["entrada_por"] == "Operador Teste" and itens[0]["liberado_por"] == "Admin Teste"
    assert itens[0]["saida_por"] is None


# ---------------------------------------------------------------------- logs
def _descricoes(db):
    return [l.descricao for l in db.exec(select(LogSistema)).all()]


def test_log_registra_quem_alterou_o_telefone_do_cliente_e_de_quanto_para_quanto(db, base):
    r = cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    cadastro_controller.atualizar_cliente_completo(r["cliente"]["id"], ClienteAtualizar(
        cliente=ClienteEdicao(nome="Maria Souza", telefone="(48) 3333-4444")), base["operador"], db)
    registro = next(l for l in db.exec(select(LogSistema)).all() if l.campo == "telefone")
    assert registro.usuario == "Operador Teste" and registro.acao == "ALTERAR"
    assert registro.valor_antigo == "(48) 99999-8888" and registro.valor_novo == "(48) 3333-4444"
    assert "Operador Teste alterou o cadastro do cliente Maria Souza: campo telefone de (48) 99999-8888 para (48) 3333-4444" in _descricoes(db)


def test_log_do_preco_mostra_valor_antigo_e_novo(db, base):
    preco = db.exec(select(Preco).where(Preco.tipo_cobranca == TipoCobrancaEnum.Horista)).one()
    aplicar_auditoria(db, base["admin"].id, base["admin"].nome)
    preco.valor = 15.0
    db.add(preco)
    db.commit()
    assert "Admin Teste alterou o preço Horista (Carro): campo valor de R$ 12,00 para R$ 15,00" in _descricoes(db)


def test_log_de_entrada_e_saida_e_sem_ruido_de_status_da_vaga(db, base):
    cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    mov = _entrada_ha(db, base, db.exec(select(Veiculo)).one().id, "H01", 600)
    movimentacao_controller.registrar_saida(mov.id, _saida(base, FormaPagamentoEnum.Pix), db)
    textos = _descricoes(db)
    assert any("registrou a ENTRADA do veículo ABC-1234 na vaga H01" in t for t in textos)
    assert any("registrou a SAÍDA do veículo ABC-1234 da vaga H01" in t for t in textos)
    assert any("registrou o pagamento Hora" in t and "R$ 120,00" in t and "Pix" in t for t in textos)
    assert not any(l.campo == "status" for l in db.exec(select(LogSistema)).all())     # status da vaga é automático


def test_log_nunca_mostra_senha(db, base):
    aplicar_auditoria(db, base["admin"].id, base["admin"].nome)
    base["operador"].senha = "novo-hash-secreto"
    db.add(base["operador"])
    db.commit()
    linha = next(l for l in db.exec(select(LogSistema)).all() if l.campo == "senha")
    assert linha.valor_novo == "(alterado)" and all("novo-hash-secreto" not in d for d in _descricoes(db))


def test_consulta_de_logs_filtra_e_pagina(db, base):
    for i in range(12):
        logs.registrar_log(db, base["admin"].id, "Admin Teste", "LOGIN", "Usuário", f"Admin Teste entrou no sistema ({i})")
    logs.registrar_log(db, base["operador"].id, "Operador Teste", "LOGIN", "Usuário", "Operador Teste entrou no sistema")
    db.commit()
    pagina = logs.listar_logs(db, id_usuario=base["admin"].id, pagina=1, por_pagina=5)
    assert pagina["total"] == 12 and len(pagina["itens"]) == 5 and pagina["paginas"] == 3
    assert logs.listar_logs(db, id_usuario=base["operador"].id)["total"] == 1
    assert logs.listar_logs(db, q="(7)")["total"] == 1


# ------------------------------------------------------------------- paginação
def test_clientes_paginados_e_filtrados(db, base):
    for i in range(23):
        db.add(Cliente(nome=f"Cliente {i:02d}", cpf=f"000.000.000-{i:02d}"))
    db.commit()
    p1 = clientes_controller.listar_pagina(db, pagina=1, por_pagina=10)
    p3 = clientes_controller.listar_pagina(db, pagina=3, por_pagina=10)
    assert p1["total"] == 23 and len(p1["itens"]) == 10 and p1["paginas"] == 3 and len(p3["itens"]) == 3
    assert p1["itens"][0]["nome"] == "Cliente 00"
    assert [c["nome"] for c in clientes_controller.listar_pagina(db, nome="Cliente 2")["itens"]] == ["Cliente 20", "Cliente 21", "Cliente 22"]
    assert clientes_controller.listar_pagina(db, documento="000000000-05")["total"] in (0, 1)
    assert clientes_controller.listar_pagina(db, documento="00000000005")["itens"][0]["nome"] == "Cliente 05"


def test_filtro_de_clientes_por_tipo_mensalista_horista_e_premium(db, base):
    _premium(db, base)
    cadastro_controller.cadastrar_completo(_cadastro("Joao Lima", "111.444.777-35", "XYZ-1A23"), base["admin"], db)
    assert [c["nome"] for c in clientes_controller.listar_pagina(db, tipo="mensalista")["itens"]] == ["Maria Souza"]
    assert [c["nome"] for c in clientes_controller.listar_pagina(db, tipo="premium")["itens"]] == ["Maria Souza"]
    assert [c["nome"] for c in clientes_controller.listar_pagina(db, tipo="horista")["itens"]] == ["Joao Lima"]
    plano = clientes_controller.listar_pagina(db, tipo="mensalista")["itens"][0]["planos"][0]
    assert plano["tipo_plano"] == "Premium" and plano["codigo_vaga"] == "P01"
