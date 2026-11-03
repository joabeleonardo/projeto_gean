import pytest
from fastapi import FastAPI
<<<<<<< HEAD
from fastapi.testclient import TestClient as ClienteHttp
=======
from fastapi.testclient import TestClient
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
from unittest.mock import patch, MagicMock

from rotas.vagas_rotas import vagas_router
from entidades.entidades import Vaga, TipoVagaEnum, StatusVagaEnum
from dependencies.database import get_db
<<<<<<< HEAD
from dependencies.auth import get_usuario_atual
from entidades.entidades import Usuario as _Usuario, PerfilEnum as _Perfil
=======
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272

# Configura o app e rota de teste
app = FastAPI()
app.include_router(vagas_router)

# Mock da dependência do Banco de Dados
def override_get_db():
    yield MagicMock()

app.dependency_overrides[get_db] = override_get_db
<<<<<<< HEAD
app.dependency_overrides[get_usuario_atual] = lambda: _Usuario(
    id=1, nome="Admin Sistema", login="admin", senha="x", perfil=_Perfil.Administrador
)

# Faz chamada simulando rotas
client = ClienteHttp(app)
=======

# Faz chamada simulando rotas
client = TestClient(app)
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272

# ==========================================
# DADOS MOCKADOS
# ==========================================
MOCK_VAGA_PAYLOAD = {
    "codigo_vaga": "A-01",
    "tipo": "Horista",
    "status": "Livre",
    "id_usuario_logado": 1,
    "nome_usuario_logado": "Admin Sistema"
}

# Resposta simulada retornada pelo banco
MOCK_VAGA_RESPOSTA = Vaga(
    id=1,
    codigo_vaga="A-01",
    tipo=TipoVagaEnum.Horista,
    status=StatusVagaEnum.Livre
)

# Caminho do patch para o controller de vagas
CONTROLLER_PATH = "rotas.vagas_rotas.vagas_controller"

# ==========================================
# TESTES DA ROTA: POST /vagas/
# ==========================================
@patch(f"{CONTROLLER_PATH}.inserir_vaga")
def test_inserir_vaga_sucesso(mock_inserir):
    mock_inserir.return_value = MOCK_VAGA_RESPOSTA
    
    response = client.post("/vagas/", json=MOCK_VAGA_PAYLOAD)
    
    assert response.status_code == 201
    assert response.json()["codigo_vaga"] == "A-01"
    assert "id" in response.json()

@patch(f"{CONTROLLER_PATH}.inserir_vaga")
def test_inserir_vaga_erro_integridade(mock_inserir):
    mock_inserir.side_effect = ValueError("Erro de integridade ao inserir vaga.")
    
    response = client.post("/vagas/", json=MOCK_VAGA_PAYLOAD)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Erro de integridade ao inserir vaga."

# ==========================================
# TESTES DA ROTA: GET /vagas/
# ==========================================
@patch(f"{CONTROLLER_PATH}.buscar_vagas")
def test_listar_vagas_sucesso(mock_buscar):
    mock_buscar.return_value = [MOCK_VAGA_RESPOSTA]
    
    response = client.get("/vagas/")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

# ==========================================
# TESTES DA ROTA: GET /vagas/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.buscar_vaga_por_id")
def test_buscar_vaga_por_id_sucesso(mock_buscar_id):
    mock_buscar_id.return_value = MOCK_VAGA_RESPOSTA
    
    response = client.get("/vagas/1")
    
    assert response.status_code == 200
    assert response.json()["id"] == 1

@patch(f"{CONTROLLER_PATH}.buscar_vaga_por_id")
def test_buscar_vaga_por_id_nao_encontrada(mock_buscar_id):
    mock_buscar_id.side_effect = KeyError("Vaga de ID 999 não encontrada.")
    
    response = client.get("/vagas/999")
    
    assert response.status_code == 404
    assert "não encontrada" in response.json()["detail"]

# ==========================================
# TESTES DA ROTA: PUT /vagas/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.atualizar_vaga")
def test_atualizar_vaga_sucesso(mock_atualizar):
    mock_atualizar.return_value = MOCK_VAGA_RESPOSTA
    
    response = client.put("/vagas/1", json=MOCK_VAGA_PAYLOAD)
    
    assert response.status_code == 200
    assert response.json()["codigo_vaga"] == "A-01"

# ==========================================
# TESTES DA ROTA: DELETE /vagas/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.deletar_vaga")
def test_deletar_vaga_sucesso(mock_deletar):
    mock_deletar.return_value = None 
    
    response = client.delete("/vagas/1?id_usuario_logado=1&nome_usuario_logado=Admin")
    
    assert response.status_code == 204 

@patch(f"{CONTROLLER_PATH}.deletar_vaga")
def test_deletar_vaga_nao_encontrada(mock_deletar):
    mock_deletar.side_effect = KeyError("Vaga de ID 999 não encontrada.")
    
    response = client.delete("/vagas/999?id_usuario_logado=1&nome_usuario_logado=Admin")
    
    assert response.status_code == 404