import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from rotas.precos_rotas import precos_router
from entidades.entidades import Preco, TipoCobrancaEnum
from dependencies.database import get_db

app = FastAPI()
app.include_router(precos_router)

def override_get_db():
    yield MagicMock()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

MOCK_PRECO_PAYLOAD = {
    "tipo_cobranca": "Horista",
    "valor": 15.00,
    "id_usuario_logado": 1,
    "nome_usuario_logado": "Admin Sistema"
}

MOCK_PRECO_RESPOSTA = Preco(
    id=1,
    tipo_cobranca=TipoCobrancaEnum.Horista,
    valor=15.00
)

CONTROLLER_PATH = "rotas.precos_rotas.precos_controller"

@patch(f"{CONTROLLER_PATH}.inserir_preco")
def test_inserir_preco_sucesso(mock_inserir):
    mock_inserir.return_value = MOCK_PRECO_RESPOSTA
    response = client.post("/precos/", json=MOCK_PRECO_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["valor"] == 15.00

@patch(f"{CONTROLLER_PATH}.buscar_precos")
def test_listar_precos_sucesso(mock_buscar):
    mock_buscar.return_value = [MOCK_PRECO_RESPOSTA]
    response = client.get("/precos/")
    assert response.status_code == 200
    assert len(response.json()) > 0

@patch(f"{CONTROLLER_PATH}.buscar_preco_por_id")
def test_buscar_preco_por_id_sucesso(mock_buscar_id):
    mock_buscar_id.return_value = MOCK_PRECO_RESPOSTA
    response = client.get("/precos/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

@patch(f"{CONTROLLER_PATH}.deletar_preco")
def test_deletar_preco_sucesso(mock_deletar):
    mock_deletar.return_value = None
    response = client.delete("/precos/1?id_usuario_logado=1&nome_usuario_logado=Admin")
    assert response.status_code == 204