import pytest
from fastapi import FastAPI
<<<<<<< HEAD
from fastapi.testclient import TestClient as ClienteHttp
=======
from fastapi.testclient import TestClient
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
from unittest.mock import patch, MagicMock

# Importações do projeto ajustadas sem o prefixo 'app.'
from rotas.clientes_rotas import clientes_router
from entidades.entidades import Cliente
from dependencies.database import get_db
<<<<<<< HEAD
from dependencies.auth import get_usuario_atual
from entidades.entidades import Usuario as _Usuario, PerfilEnum as _Perfil
=======
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272

# Configura o app e rota de teste
app = FastAPI()
app.include_router(clientes_router)

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
MOCK_CLIENTE_PAYLOAD = {
    "nome": "Carlos Silva",
<<<<<<< HEAD
    "cpf": "529.982.247-25",
    "telefone": "(11) 99999-9999",
=======
    "cpf": "111.111.111-11",
    "telefone": "11999999999",
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
    "id_endereco": 1,
    "id_usuario_logado": 1,
    "nome_usuario_logado": "Admin Sistema"
}

# Resposta simulada retornada pelo banco (sem os campos de auditoria)
MOCK_CLIENTE_RESPOSTA = Cliente(
    id=1,
    nome="Carlos Silva",
<<<<<<< HEAD
    cpf="529.982.247-25",
    telefone="(11) 99999-9999",
=======
    cpf="111.111.111-11",
    telefone="11999999999",
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
    id_endereco=1
)

# Caminho do patch ajustado para o novo local do controller
CONTROLLER_PATH = "rotas.clientes_rotas.clientes_controller"

# ==========================================
# TESTES DA ROTA: POST /clientes/
# ==========================================
@patch(f"{CONTROLLER_PATH}.inserir_cliente")
def test_inserir_cliente_sucesso(mock_inserir):
    mock_inserir.return_value = MOCK_CLIENTE_RESPOSTA
    
    response = client.post("/clientes/", json=MOCK_CLIENTE_PAYLOAD)
    
    assert response.status_code == 201
    assert response.json()["nome"] == "Carlos Silva"
    assert "id" in response.json()

@patch(f"{CONTROLLER_PATH}.inserir_cliente")
def test_inserir_cliente_erro_integridade(mock_inserir):
    mock_inserir.side_effect = ValueError("Erro de integridade ao inserir cliente.")
    
    response = client.post("/clientes/", json=MOCK_CLIENTE_PAYLOAD)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Erro de integridade ao inserir cliente."

# ==========================================
# TESTES DA ROTA: GET /clientes/
# ==========================================
@patch(f"{CONTROLLER_PATH}.buscar_clientes")
def test_listar_clientes_sucesso(mock_buscar):
    mock_buscar.return_value = [MOCK_CLIENTE_RESPOSTA]
    
    response = client.get("/clientes/")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

# ==========================================
# TESTES DA ROTA: GET /clientes/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.buscar_cliente_por_id")
def test_buscar_cliente_por_id_sucesso(mock_buscar_id):
    mock_buscar_id.return_value = MOCK_CLIENTE_RESPOSTA
    
    response = client.get("/clientes/1")
    
    assert response.status_code == 200
    assert response.json()["id"] == 1

@patch(f"{CONTROLLER_PATH}.buscar_cliente_por_id")
def test_buscar_cliente_por_id_nao_encontrado(mock_buscar_id):
    mock_buscar_id.side_effect = KeyError("Cliente de ID 999 não encontrado.")
    
    response = client.get("/clientes/999")
    
    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"]

# ==========================================
# TESTES DA ROTA: PUT /clientes/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.atualizar_cliente")
def test_atualizar_cliente_sucesso(mock_atualizar):
    mock_atualizar.return_value = MOCK_CLIENTE_RESPOSTA
    
    response = client.put("/clientes/1", json=MOCK_CLIENTE_PAYLOAD)
    
    assert response.status_code == 200
    assert response.json()["nome"] == "Carlos Silva"

# ==========================================
# TESTES DA ROTA: DELETE /clientes/{id}
# ==========================================
@patch(f"{CONTROLLER_PATH}.deletar_cliente")
def test_deletar_cliente_sucesso(mock_deletar):
    mock_deletar.return_value = None 
    
    # Passando os parâmetros de auditoria exigidos pelo método de deleção
    response = client.delete("/clientes/1?id_usuario_logado=1&nome_usuario_logado=Admin")
    
    assert response.status_code == 204 

@patch(f"{CONTROLLER_PATH}.deletar_cliente")
def test_deletar_cliente_nao_encontrado(mock_deletar):
    mock_deletar.side_effect = KeyError("Cliente de ID 999 não encontrado.")
    
    response = client.delete("/clientes/999?id_usuario_logado=1&nome_usuario_logado=Admin")
    
    assert response.status_code == 404