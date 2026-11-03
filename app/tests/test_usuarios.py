import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient as ClienteHttp
from unittest.mock import patch, MagicMock

from rotas.usuarios_rotas import usuarios_router
from entidades.entidades import Usuario, PerfilEnum
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual
from entidades.entidades import Usuario as _Usuario, PerfilEnum as _Perfil

app = FastAPI()
app.include_router(usuarios_router)

def override_get_db():
    yield MagicMock()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_usuario_atual] = lambda: _Usuario(
    id=1, nome="Admin Sistema", login="admin", senha="x", perfil=_Perfil.Administrador
)
client = ClienteHttp(app)

MOCK_USUARIO_PAYLOAD = {
    "nome": "Operador Teste",
    "login": "operador.teste",
    "perfil": "Operador",
    "senha": "senha123",
    "id_usuario_logado": 1,
    "nome_usuario_logado": "Admin Sistema"
}

MOCK_USUARIO_RESPOSTA = Usuario(
    id=1,
    nome="Operador Teste",
    login="operador.teste",
    perfil=PerfilEnum.Operador,
    senha="hashed_password"
)

CONTROLLER_PATH = "rotas.usuarios_rotas.usuarios_controller"

@patch(f"{CONTROLLER_PATH}.inserir_usuario")
def test_inserir_usuario_sucesso(mock_inserir):
    mock_inserir.return_value = MOCK_USUARIO_RESPOSTA
    response = client.post("/usuarios/", json=MOCK_USUARIO_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["login"] == "operador.teste"

@patch(f"{CONTROLLER_PATH}.buscar_usuarios")
def test_listar_usuarios_sucesso(mock_buscar):
    mock_buscar.return_value = [MOCK_USUARIO_RESPOSTA]
    response = client.get("/usuarios/")
    assert response.status_code == 200
    assert len(response.json()) > 0

@patch(f"{CONTROLLER_PATH}.buscar_usuario_por_id")
def test_buscar_usuario_por_id_sucesso(mock_buscar_id):
    mock_buscar_id.return_value = MOCK_USUARIO_RESPOSTA
    response = client.get("/usuarios/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

@patch(f"{CONTROLLER_PATH}.deletar_usuario")
def test_deletar_usuario_sucesso(mock_deletar):
    mock_deletar.return_value = None
    response = client.delete("/usuarios/1?id_usuario_logado=1&nome_usuario_logado=Admin")
    assert response.status_code == 204