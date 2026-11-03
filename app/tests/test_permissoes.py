"""Garante que as regras de acesso valem na API (não só no frontend)."""
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient as ClienteHttp

from dependencies.auth import get_usuario_atual
from dependencies.database import get_db
from entidades.entidades import PerfilEnum, Usuario
from rotas.clientes_rotas import clientes_router
from rotas.mensalidades_rotas import mensalidades_router
from rotas.precos_rotas import precos_router
from rotas.relatorios_rotas import relatorios_router
from rotas.usuarios_rotas import usuarios_router
from rotas.vagas_rotas import vagas_router

app = FastAPI()
for r in (clientes_router, precos_router, relatorios_router, usuarios_router, vagas_router, mensalidades_router):
    app.include_router(r)
app.dependency_overrides[get_db] = lambda: MagicMock()
client = ClienteHttp(app)

PRECO = {"tipo_cobranca": "Horista", "valor": 10.0}


def logar_como(perfil):
    app.dependency_overrides[get_usuario_atual] = lambda: Usuario(
        id=2, nome="Fulano", login="fulano", senha="x", perfil=perfil
    )


def sair():
    app.dependency_overrides.pop(get_usuario_atual, None)


def test_sem_login_retorna_401():
    sair()
    assert client.get("/clientes/").status_code == 401
    assert client.get("/precos/").status_code == 401
    assert client.post("/precos/", json=PRECO).status_code == 401


def test_token_invalido_retorna_401():
    sair()
    resposta = client.get("/clientes/", headers={"Authorization": "Bearer token-falso"})
    assert resposta.status_code == 401


def test_operador_nao_altera_preco():
    logar_como(PerfilEnum.Operador)
    assert client.post("/precos/", json=PRECO).status_code == 403
    assert client.put("/precos/1", json=PRECO).status_code == 403
    assert client.delete("/precos/1").status_code == 403


@patch("rotas.precos_rotas.precos_controller")
def test_operador_pode_consultar_preco(mock_ctrl):
    logar_como(PerfilEnum.Operador)
    mock_ctrl.buscar_precos.return_value = []
    assert client.get("/precos/").status_code == 200


@patch("rotas.precos_rotas.precos_controller")
def test_admin_altera_preco(mock_ctrl):
    logar_como(PerfilEnum.Administrador)
    mock_ctrl.inserir_preco.return_value = {"id": 1, **PRECO}
    assert client.post("/precos/", json=PRECO).status_code == 201


def test_operador_nao_acessa_usuarios_nem_relatorios():
    logar_como(PerfilEnum.Operador)
    assert client.get("/usuarios/").status_code == 403
    assert client.get("/relatorios/pagamentos").status_code == 403


def test_operador_nao_exclui_cliente():
    logar_como(PerfilEnum.Operador)
    assert client.delete("/clientes/1").status_code == 403


@patch("rotas.clientes_rotas.clientes_controller")
def test_usuario_da_auditoria_vem_do_login_e_nao_do_corpo(mock_ctrl):
    logar_como(PerfilEnum.Operador)
    mock_ctrl.inserir_cliente.return_value = {"id": 1, "nome": "Maria Souza", "cpf": "529.982.247-25"}
    corpo = {
        "nome": "Maria Souza", "cpf": "529.982.247-25",
        "id_usuario_logado": 999, "nome_usuario_logado": "Impostor",
    }
    resposta = client.post("/clientes/", json=corpo)
    assert resposta.status_code == 201
    enviado = mock_ctrl.inserir_cliente.call_args[0][0]
    assert enviado.id_usuario_logado == 2
    assert enviado.nome_usuario_logado == "Fulano"


def test_cpf_invalido_e_rejeitado():
    logar_como(PerfilEnum.Operador)
    resposta = client.post("/clientes/", json={"nome": "Maria Souza", "cpf": "111.111.111-11"})
    assert resposta.status_code == 422


def test_operador_nao_inativa_nem_edita_vaga():
    logar_como(PerfilEnum.Operador)
    assert client.put("/vagas/1/situacao", json={"ativa": False}).status_code == 403
    assert client.put("/vagas/1", json={"codigo_vaga": "A01", "tipo": "Horista", "categoria": "Carro"}).status_code == 403


def test_operador_nao_altera_cotas_nem_cancela_plano_nem_gera_cobrancas():
    logar_como(PerfilEnum.Operador)
    assert client.put("/mensalidades/1/cotas", json={"cotas": 2}).status_code == 403
    assert client.put("/mensalidades/1/cancelar").status_code == 403
    assert client.post("/mensalidades/gerar-cobrancas").status_code == 403


@patch("rotas.vagas_rotas.vagas_controller")
def test_admin_inativa_vaga(mock_ctrl):
    logar_como(PerfilEnum.Administrador)
    mock_ctrl.definir_situacao.return_value = {"id": 1, "codigo_vaga": "A01", "tipo": "Horista", "categoria": "Carro", "status": "Livre", "ativa": False}
    r = client.put("/vagas/1/situacao", json={"ativa": False})
    assert r.status_code == 200 and r.json()["ativa"] is False
    assert mock_ctrl.definir_situacao.call_args[0][1] is False


@patch("rotas.mensalidades_rotas.mensalidade_controller")
def test_operador_pode_aderir_ao_plano(mock_ctrl):
    logar_como(PerfilEnum.Operador)
    from datetime import date
    from entidades.entidades import Mensalidade
    mock_ctrl.aderir.return_value = Mensalidade(id=1, id_cliente=3, categoria="Carro", cotas=2, data_inicio=date(2026, 10, 23))
    r = client.post("/mensalidades/", json={"id_cliente": 3, "cotas": 2})
    assert r.status_code == 201 and r.json()["cotas"] == 2
