import pytest
from fastapi import FastAPI
<<<<<<< HEAD
from fastapi.testclient import TestClient as ClienteHttp
=======
from fastapi.testclient import TestClient
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
from unittest.mock import patch, MagicMock

from rotas.pagamentos_rotas import pagamentos_router
from entidades.entidades import Pagamento, TipoPagamentoEnum, StatusPagamentoEnum
from dependencies.database import get_db
<<<<<<< HEAD
from dependencies.auth import get_usuario_atual
from entidades.entidades import Usuario as _Usuario, PerfilEnum as _Perfil
=======
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272

app = FastAPI()
app.include_router(pagamentos_router)

def override_get_db():
    yield MagicMock()

app.dependency_overrides[get_db] = override_get_db
<<<<<<< HEAD
app.dependency_overrides[get_usuario_atual] = lambda: _Usuario(
    id=1, nome="Admin Sistema", login="admin", senha="x", perfil=_Perfil.Administrador
)
client = ClienteHttp(app)
=======
client = TestClient(app)
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272

MOCK_PAGAMENTO_PAYLOAD = {
    "id_cliente": 1,
    "tipo_cobranca": "Mensal",
    "valor_total": 250.00,
    "id_usuario_recebimento": 1,
    "id_usuario_logado": 1,
    "nome_usuario_logado": "Admin Sistema"
}

MOCK_PAGAMENTO_RESPOSTA = Pagamento(
    id=1,
    id_cliente=1,
    tipo_cobranca=TipoPagamentoEnum.Mensal,
    valor_total=250.00,
    status=StatusPagamentoEnum.Pago,
    id_usuario_recebimento=1
)

CONTROLLER_PATH = "rotas.pagamentos_rotas.pagamentos_controller"

@patch(f"{CONTROLLER_PATH}.registrar_pagamento")
def test_registrar_pagamento_sucesso(mock_registrar):
    mock_registrar.return_value = MOCK_PAGAMENTO_RESPOSTA
    response = client.post("/pagamentos/", json=MOCK_PAGAMENTO_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["valor_total"] == 250.00

@patch(f"{CONTROLLER_PATH}.buscar_pagamentos")
def test_listar_pagamentos_sucesso(mock_buscar):
    mock_buscar.return_value = [MOCK_PAGAMENTO_RESPOSTA]
    response = client.get("/pagamentos/")
    assert response.status_code == 200
    assert len(response.json()) > 0

@patch(f"{CONTROLLER_PATH}.buscar_pagamento_por_id")
def test_buscar_pagamento_por_id_sucesso(mock_buscar_id):
    mock_buscar_id.return_value = MOCK_PAGAMENTO_RESPOSTA
    response = client.get("/pagamentos/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

@patch(f"{CONTROLLER_PATH}.deletar_pagamento")
def test_deletar_pagamento_sucesso(mock_deletar):
    mock_deletar.return_value = None
    response = client.delete("/pagamentos/1?id_usuario_logado=1&nome_usuario_logado=Admin")
    assert response.status_code == 204