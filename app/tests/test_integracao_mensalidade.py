"""Integração (SQLite em memória): plano de mensalista, cotas, modo de entrada, vagas inativas,
edição de cadastros e cobrança mensal."""
from datetime import timedelta

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from controllers import cadastro_controller, mensalidade_controller, movimentacao_controller
from controllers import vagas_controller, veiculos_controller
from entidades.entidades import (
    CategoriaEnum, Cliente, Mensalidade, Movimentacao, Pagamento, Preco, StatusPagamentoEnum, TipoCobrancaEnum,
    TipoVagaEnum, Usuario, Vaga, Veiculo,
)
from modelos.schemas import (
    CadastroCompletoCreate, ClienteAtualizar, ClienteEdicao, ClienteEntrada, EnderecoEntrada, MensalidadeEntrada,
    MovimentacaoEntradaCreate, VagaCreate, VeiculoCreate, VeiculoEntrada,
)
from servicos.datas import hoje_local
from servicos.excecoes import CotasEsgotadas, EntradaBloqueada
from servicos.mensalidade import vencimentos_ate


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao


@pytest.fixture()
def base(db):
    """Admin, preços (hora R$ 12 e mensal R$ 250) e três vagas de carro: M01 mensalista, H01 e H02 horistas."""
    admin = Usuario(nome="Admin Teste", login="admin", senha="x", perfil="Administrador")
    db.add(admin)
    db.add(Preco(categoria=CategoriaEnum.Carro, tipo_cobranca=TipoCobrancaEnum.Horista, valor=12.0))
    db.add(Preco(categoria=CategoriaEnum.Carro, tipo_cobranca=TipoCobrancaEnum.Mensalista, valor=250.0))
    vagas = {
        "M01": Vaga(codigo_vaga="M01", tipo=TipoVagaEnum.Mensalista),
        "H01": Vaga(codigo_vaga="H01", tipo=TipoVagaEnum.Horista),
        "H02": Vaga(codigo_vaga="H02", tipo=TipoVagaEnum.Horista),
    }
    for v in vagas.values():
        db.add(v)
    db.commit()
    for obj in [admin, *vagas.values()]:
        db.refresh(obj)
    return {"admin": admin, "vagas": vagas}


def _cadastro(nome, cpf, placa, mensalidade=None):
    return CadastroCompletoCreate(
        cliente=ClienteEntrada(nome=nome, cpf=cpf, telefone="48999998888"),
        veiculo=VeiculoEntrada(placa=placa, marca="Honda", modelo="Civic"),
        mensalidade=mensalidade,
    )


def _mensalista(db, base, cotas=1, **extra):
    return cadastro_controller.cadastrar_completo(
        _cadastro("Maria Souza", "529.982.247-25", "ABC-1234", MensalidadeEntrada(cotas=cotas, **extra)),
        base["admin"], db,
    )


def _segundo_carro(db, cliente_id, placa="DEF-5678"):
    v = Veiculo(placa=placa, marca="Fiat", modelo="Uno", id_cliente=cliente_id)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _entrar(db, base, veiculo_id, vaga, **extra):
    return movimentacao_controller.registrar_entrada(MovimentacaoEntradaCreate(
        id_veiculo=veiculo_id, id_vaga=base["vagas"][vaga].id, id_usuario_entrada=base["admin"].id,
        id_usuario_logado=base["admin"].id, nome_usuario_logado="Admin", **extra), db)


# ------------------------------------------------------- adesão no cadastro
def test_cadastro_com_mensalidade_cria_plano_e_primeira_cobranca(db, base):
    r = _mensalista(db, base)
    assert r["mensalidade"]["cotas"] == 1 and r["mensalidade"]["categoria"] == "Carro"
    assert str(r["mensalidade"]["data_inicio"]) == hoje_local().isoformat()      # vale a partir da adesão
    pagamento = db.exec(select(Pagamento)).one()
    assert pagamento.valor_total == 250.0 and pagamento.status == StatusPagamentoEnum.Pendente
    assert pagamento.data_vencimento == hoje_local() and pagamento.id_cliente == r["cliente"]["id"]


def test_cota_multiplica_o_valor_da_mensalidade(db, base):
    db.add(Vaga(codigo_vaga="M02", tipo=TipoVagaEnum.Mensalista))
    db.commit()
    _mensalista(db, base, cotas=2)
    assert db.exec(select(Pagamento)).one().valor_total == 500.0


def test_primeira_mensalidade_paga_exige_forma_de_pagamento(db, base):
    with pytest.raises(ValueError):
        _mensalista(db, base, status_primeira_cobranca="Pago")
    assert db.exec(select(Cliente)).all() == []            # nada foi gravado
    r = _mensalista(db, base, status_primeira_cobranca="Pago", forma_pagamento="Pix")
    pagamento = db.exec(select(Pagamento)).one()
    assert pagamento.status == StatusPagamentoEnum.Pago and pagamento.forma_pagamento == "Pix"
    assert r["cliente"]["id"] == pagamento.id_cliente


def test_nao_cadastra_mais_cotas_do_que_vagas_de_mensalista(db, base):
    with pytest.raises(ValueError, match="Limite de vagas de mensalista"):
        _mensalista(db, base, cotas=2)                      # só existe 1 vaga de mensalista
    assert db.exec(select(Cliente)).all() == []
    _mensalista(db, base, cotas=1)
    with pytest.raises(ValueError, match="Limite de vagas de mensalista"):
        cadastro_controller.cadastrar_completo(
            _cadastro("Joao Lima", "111.444.777-35", "XYZ-1A23", MensalidadeEntrada(cotas=1)), base["admin"], db)


def test_data_de_adesao_no_passado_e_recusada(db, base):
    with pytest.raises(ValueError, match="anterior a hoje"):
        _mensalista(db, base, data_inicio=hoje_local() - timedelta(days=1))


# ------------------------------------------------------------ modo de entrada
def test_cliente_horista_entra_como_horista(db, base):
    r = cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    modo = movimentacao_controller.consultar_modo_entrada(db.exec(select(Veiculo)).one().id, db)
    assert modo["modo"] == "Horista" and modo["tem_plano"] is False
    veiculo_id = db.exec(select(Veiculo)).one().id
    with pytest.raises(ValueError, match="horista"):
        _entrar(db, base, veiculo_id, "M01")                # vaga de mensalista não serve
    _entrar(db, base, veiculo_id, "H01")


def test_mensalista_e_identificado_e_usa_vaga_de_mensalista(db, base):
    _mensalista(db, base)
    veiculo_id = db.exec(select(Veiculo)).one().id
    modo = movimentacao_controller.consultar_modo_entrada(veiculo_id, db)
    assert modo["modo"] == "Mensalista" and modo["cotas"] == 1 and modo["em_uso"] == 0 and not modo["esgotado"]
    with pytest.raises(ValueError, match="mensalista"):
        _entrar(db, base, veiculo_id, "H01")                # mensalista com cota livre deve usar vaga de mensalista
    mov = _entrar(db, base, veiculo_id, "M01")
    assert mov.id is not None


def test_segundo_veiculo_sem_cota_livre_pede_confirmacao_e_entra_como_horista(db, base):
    r = _mensalista(db, base)
    carro_a = db.exec(select(Veiculo)).one()
    carro_b = _segundo_carro(db, r["cliente"]["id"])
    _entrar(db, base, carro_a.id, "M01")

    modo = movimentacao_controller.consultar_modo_entrada(carro_b.id, db)
    assert modo["esgotado"] is True and modo["placas_em_uso"] == ["ABC-1234"]

    with pytest.raises(CotasEsgotadas) as erro:             # alerta: "deseja dar entrada como horista?"
        _entrar(db, base, carro_b.id, "H01")
    assert erro.value.cotas == 1 and erro.value.placas_em_uso == ["ABC-1234"]
    assert db.get(Vaga, base["vagas"]["H01"].id).status.value == "Livre"       # nada foi gravado

    _entrar(db, base, carro_b.id, "H01", como_horista=True)                     # operador confirmou
    assert len(db.exec(select(Movimentacao)).all()) == 2


def test_duas_cotas_permitem_dois_veiculos_ao_mesmo_tempo(db, base):
    db.add(Vaga(codigo_vaga="M02", tipo=TipoVagaEnum.Mensalista))
    db.commit()
    base["vagas"]["M02"] = db.exec(select(Vaga).where(Vaga.codigo_vaga == "M02")).one()
    r = _mensalista(db, base, cotas=2)
    carro_a = db.exec(select(Veiculo)).one()
    carro_b = _segundo_carro(db, r["cliente"]["id"])
    _entrar(db, base, carro_a.id, "M01")
    assert movimentacao_controller.consultar_modo_entrada(carro_b.id, db)["esgotado"] is False
    _entrar(db, base, carro_b.id, "M02")
    carro_c = _segundo_carro(db, r["cliente"]["id"], "GHI-9012")
    with pytest.raises(CotasEsgotadas):
        _entrar(db, base, carro_c.id, "H01")


def test_plano_que_comeca_no_futuro_ainda_entra_como_horista(db, base):
    _mensalista(db, base, data_inicio=hoje_local() + timedelta(days=5))
    veiculo_id = db.exec(select(Veiculo)).one().id
    modo = movimentacao_controller.consultar_modo_entrada(veiculo_id, db)
    assert modo["modo"] == "Horista" and modo["inicio_futuro"] == hoje_local() + timedelta(days=5)
    _entrar(db, base, veiculo_id, "H01")


# ------------------------------------------------------------ vagas inativas
def test_vaga_inativa_nao_recebe_entrada(db, base):
    r = cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    vaga = base["vagas"]["H01"]
    vagas_controller.definir_situacao(vaga.id, False, base["admin"], db)
    with pytest.raises(ValueError, match="inativa"):
        _entrar(db, base, db.exec(select(Veiculo)).one().id, "H01")
    vagas_controller.definir_situacao(vaga.id, True, base["admin"], db)
    _entrar(db, base, db.exec(select(Veiculo)).one().id, "H01")


def test_nao_inativa_vaga_ocupada(db, base):
    cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    _entrar(db, base, db.exec(select(Veiculo)).one().id, "H01")
    with pytest.raises(ValueError, match="ocupada"):
        vagas_controller.definir_situacao(base["vagas"]["H01"].id, False, base["admin"], db)


def test_nao_inativa_vaga_de_mensalista_que_sustenta_cotas_contratadas(db, base):
    _mensalista(db, base)
    with pytest.raises(ValueError, match="cota"):
        vagas_controller.definir_situacao(base["vagas"]["M01"].id, False, base["admin"], db)


# ------------------------------------------------------------------- edições
def test_editar_cliente_telefone_e_endereco(db, base):
    r = cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    novo = ClienteAtualizar(
        cliente=ClienteEdicao(nome="Maria Souza Lima", telefone="(48) 3333-4444", telefone2="48999990000", telefone2_whatsapp=True),
        endereco=EnderecoEntrada(logradouro="Rua das Flores", numero="10", bairro="Centro", cidade="Joinville", estado="sc", cep="89201000"),
    )
    r2 = cadastro_controller.atualizar_cliente_completo(r["cliente"]["id"], novo, base["admin"], db)
    assert r2["cliente"]["nome"] == "Maria Souza Lima" and r2["cliente"]["telefone"] == "(48) 3333-4444"
    assert r2["cliente"]["telefone2"] == "(48) 99999-0000" and r2["cliente"]["telefone2_whatsapp"] is True
    assert r2["cliente"]["cpf"] == "529.982.247-25"                  # o documento não mudou
    assert r2["endereco"]["cep"] == "89201-000" and r2["endereco"]["estado"] == "SC"
    # mudou de endereço de novo: atualiza o mesmo registro em vez de criar outro
    novo.endereco.numero = "99"
    r3 = cadastro_controller.atualizar_cliente_completo(r["cliente"]["id"], novo, base["admin"], db)
    assert r3["endereco"]["numero"] == "99" and r3["endereco"]["id"] == r2["endereco"]["id"]
    assert len(r3["veiculos"]) == 1


def test_documento_do_cliente_nao_pode_ser_alterado(db, base):
    r = cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    from controllers import clientes_controller
    from modelos.schemas import ClienteCreate
    with pytest.raises(ValueError, match="não pode ser alterado"):
        clientes_controller.atualizar_cliente(r["cliente"]["id"], ClienteCreate(
            nome="Maria Souza", cpf="111.444.777-35", id_usuario_logado=1, nome_usuario_logado="x"), db)
    assert db.get(Cliente, r["cliente"]["id"]).cpf == "529.982.247-25"


def test_editar_vaga_codigo_tipo_e_categoria(db, base):
    vaga = base["vagas"]["H02"]
    editada = vagas_controller.atualizar_vaga(vaga.id, VagaCreate(
        codigo_vaga="MOTO-1", tipo="Horista", categoria="Moto", id_usuario_logado=1, nome_usuario_logado="x"), db)
    assert editada.codigo_vaga == "MOTO-1" and editada.categoria.value == "Moto"
    assert editada.status.value == "Livre"                     # a edição não mexe na situação


def test_nao_edita_tipo_de_vaga_ocupada(db, base):
    cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    _entrar(db, base, db.exec(select(Veiculo)).one().id, "H01")
    with pytest.raises(ValueError, match="ocupada"):
        vagas_controller.atualizar_vaga(base["vagas"]["H01"].id, VagaCreate(
            codigo_vaga="H01", tipo="Mensalista", categoria="Carro", id_usuario_logado=1, nome_usuario_logado="x"), db)


def test_editar_veiculo_corrige_dados_mas_nao_o_tipo_com_veiculo_no_patio(db, base):
    r = cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    veiculo = db.exec(select(Veiculo)).one()
    corrigido = veiculos_controller.atualizar_veiculo(veiculo.id, VeiculoCreate(
        placa="ABC-1235", marca="Toyota", modelo="Corolla", id_cliente=r["cliente"]["id"],
        id_usuario_logado=1, nome_usuario_logado="x"), db)
    assert corrigido.placa == "ABC-1235" and corrigido.marca == "Toyota"

    _entrar(db, base, veiculo.id, "H01")
    with pytest.raises(ValueError, match="pátio"):
        veiculos_controller.atualizar_veiculo(veiculo.id, VeiculoCreate(
            placa="ABC-1235", marca="Toyota", modelo="Corolla", tipo_veiculo="Moto", id_cliente=r["cliente"]["id"],
            id_usuario_logado=1, nome_usuario_logado="x"), db)


# ------------------------------------------------------------ cobranças mensais
def test_gerar_cobrancas_cria_as_vencidas_sem_duplicar_e_gera_inadimplencia(db, base):
    r = cadastro_controller.cadastrar_completo(_cadastro("Maria Souza", "529.982.247-25", "ABC-1234"), base["admin"], db)
    hoje = hoje_local()
    inicio = hoje - timedelta(days=70)
    db.add(Mensalidade(id_cliente=r["cliente"]["id"], categoria=CategoriaEnum.Carro, cotas=1, data_inicio=inicio))
    db.commit()
    esperado = len(vencimentos_ate(inicio, hoje))

    primeira = mensalidade_controller.gerar_cobrancas(db)
    assert primeira["criadas"] == esperado
    assert len(db.exec(select(Pagamento)).all()) == esperado
    assert mensalidade_controller.gerar_cobrancas(db)["criadas"] == 0          # idempotente

    # a cobrança mais antiga está vencida e pendente: o cliente fica inadimplente e a entrada é bloqueada
    with pytest.raises(EntradaBloqueada):
        _entrar(db, base, db.exec(select(Veiculo)).one().id, "H01")
