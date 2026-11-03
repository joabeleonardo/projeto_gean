import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient as ClienteHttp
from unittest.mock import patch, MagicMock
from datetime import datetime

from rotas.movimentacao_rotas import movimentacao_router
from entidades.entidades import Movimentacao
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual
from entidades.entidades import Usuario as _Usuario, PerfilEnum as _Perfil

app = FastAPI()
app.include_router(movimentacao_router)

def override_get_db():
    yield MagicMock()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_usuario_atual] = lambda: _Usuario(
    id=1, nome="Admin Sistema", login="admin", senha="x", perfil=_Perfil.Administrador
)
client = ClienteHttp(app)

MOCK_ENTRADA_PAYLOAD = {
    "id_veiculo": 1,
    "id_vaga": 1,
    "id_usuario_entrada": 1,
    "id_usuario_logado": 1,
    "nome_usuario_logado": "Admin Sistema"
}

MOCK_SAIDA_PAYLOAD = {
    "id_usuario_saida": 1,
    "id_usuario_logado": 1,
    "nome_usuario_logado": "Admin Sistema"
}

MOCK_MOVIMENTACAO_RESPOSTA = Movimentacao(
    id=1,
    id_veiculo=1,
    id_vaga=1,
    data_entrada=datetime.now(),
    id_usuario_entrada=1,
    data_saida=None,
    id_usuario_saida=None
)

CONTROLLER_PATH = "rotas.movimentacao_rotas.movimentacao_controller"

@patch(f"{CONTROLLER_PATH}.registrar_entrada")
def test_registrar_entrada_sucesso(mock_entrada):
    mock_entrada.return_value = MOCK_MOVIMENTACAO_RESPOSTA
    response = client.post("/movimentacoes/entrada", json=MOCK_ENTRADA_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["id_veiculo"] == 1

@patch(f"{CONTROLLER_PATH}.buscar_movimentacoes")
def test_listar_movimentacoes_sucesso(mock_buscar):
    mock_buscar.return_value = [MOCK_MOVIMENTACAO_RESPOSTA]
    response = client.get("/movimentacoes/")
    assert response.status_code == 200
    assert len(response.json()) > 0

@patch(f"{CONTROLLER_PATH}.buscar_movimentacao_por_id")
def test_buscar_movimentacao_por_id_sucesso(mock_buscar_id):
    mock_buscar_id.return_value = MOCK_MOVIMENTACAO_RESPOSTA
    response = client.get("/movimentacoes/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

@patch(f"{CONTROLLER_PATH}.registrar_saida")
def test_registrar_saida_sucesso(mock_saida):
    mov_fechada = Movimentacao(
        id=1,
        id_veiculo=1,
        id_vaga=1,
        data_entrada=datetime.now(),
        id_usuario_entrada=1,
        data_saida=datetime.now(),
        id_usuario_saida=1
    )
    mock_saida.return_value = mov_fechada
    response = client.put("/movimentacoes/1/saida", json=MOCK_SAIDA_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["data_saida"] is not None