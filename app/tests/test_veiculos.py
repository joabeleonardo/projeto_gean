import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from rotas.veiculos_rotas import veiculos_router
from entidades.entidades import Veiculo
from dependencies.database import get_db

# Configura o app e rota de teste
app = FastAPI()
app.include_router(veiculos_router)

# Mock da dependência do Banco de Dados
def override_get_db():
    yield MagicMock()

app.dependency_overrides[get_db] = override_get_db

# Faz chamada simulando rotas
client = TestClient(app)

# ==========================================
# DADOS MOCKADOS
# ==========================================
MOCK_VEICULO_PAYLOAD = {
    "placa": "ABC-1234",
    "modelo": "Honda Civic",
    "cor": "Prata",
    "id_cliente": 1,
    "id_usuario_logado": 1,
    "nome_usuario_logado": "Admin Sistema"
}

# Resposta simulada retornada pelo banco
MOCK_VEICULO_RESPOSTA = Veiculo(
    id=1,
    placa="ABC-1234",
    modelo="Honda Civic",
    cor="Prata",
    id_cliente=1
)

# Caminho do patch para o controller de veículos
CONTROLLER_PATH = "rotas.veiculos_rotas.veiculos_controller"

# ==========================================
# TESTES DA ROTA: POST /veiculos/
# ==========================================
@patch(f"{CONTROLLER_PATH}.inserir_veiculo")
def test_inserir_veiculo_sucesso(mock_inserir):
    mock_inserir.return_value = MOCK_VEICULO_RESPOSTA
    
    response = client.post("/veiculos/", json=MOCK_VEICULO_PAYLOAD)
    
    assert response.status_code == 201
    assert response.json()["placa"] == "ABC-1234"
    assert "id" in response.json()

@patch(f"{CONTROLLER_PATH}.inserir_veiculo")
def test_inserir_veiculo_erro_integridade(mock_inserir):
    mock_inserir.side_effect = ValueError("Erro de integridade ao inserir veículo.")
    
    response = client.post("/veiculos/", json=MOCK_VEICULO_PAYLOAD)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Erro de integridade ao inserir veículo."

# ==========================================
# TESTES DA ROTA: GET /veiculos/
# ==========================================
@patch(f"{CONTROLLER_PATH}.buscar_veiculos")
def test_listar_veiculos_sucesso(mock_buscar):
    mock_buscar.return_value = [MOCK_VEICULO_RESPOSTA]
    
    response = client.get("/veiculos/")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

# ==========================================
# TESTES DA ROTA: GET /veiculos/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.buscar_veiculo_por_id")
def test_buscar_veiculo_por_id_sucesso(mock_buscar_id):
    mock_buscar_id.return_value = MOCK_VEICULO_RESPOSTA
    
    response = client.get("/veiculos/1")
    
    assert response.status_code == 200
    assert response.json()["id"] == 1

@patch(f"{CONTROLLER_PATH}.buscar_veiculo_por_id")
def test_buscar_veiculo_por_id_nao_encontrado(mock_buscar_id):
    mock_buscar_id.side_effect = KeyError("Veículo de ID 999 não encontrado.")
    
    response = client.get("/veiculos/999")
    
    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"]

# ==========================================
# TESTES DA ROTA: PUT /veiculos/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.atualizar_veiculo")
def test_atualizar_veiculo_sucesso(mock_atualizar):
    mock_atualizar.return_value = MOCK_VEICULO_RESPOSTA
    
    response = client.put("/veiculos/1", json=MOCK_VEICULO_PAYLOAD)
    
    assert response.status_code == 200
    assert response.json()["placa"] == "ABC-1234"

# ==========================================
# TESTES DA ROTA: DELETE /veiculos/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.deletar_veiculo")
def test_deletar_veiculo_sucesso(mock_deletar):
    mock_deletar.return_value = None 
    
    response = client.delete("/veiculos/1?id_usuario_logado=1&nome_usuario_logado=Admin")
    
    assert response.status_code == 204 

@patch(f"{CONTROLLER_PATH}.deletar_veiculo")
def test_deletar_veiculo_nao_encontrado(mock_deletar):
    mock_deletar.side_effect = KeyError("Veículo de ID 999 não encontrado.")
    
    response = client.delete("/veiculos/999?id_usuario_logado=1&nome_usuario_logado=Admin")
    
    assert response.status_code == 404