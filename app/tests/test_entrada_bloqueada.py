from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient as ClienteHttp

from dependencies.auth import get_usuario_atual
from dependencies.database import get_db
from entidades.entidades import Usuario
from rotas.movimentacao_rotas import movimentacao_router
from servicos.excecoes import CotasEsgotadas, EntradaBloqueada

app = FastAPI()
app.include_router(movimentacao_router)
app.dependency_overrides[get_db] = lambda: MagicMock()
app.dependency_overrides[get_usuario_atual] = lambda: Usuario(
    id=2, nome="Operador", login="op", senha="x", perfil="Operador"
)
client = ClienteHttp(app)


@patch("rotas.movimentacao_rotas.movimentacao_controller.registrar_entrada")
def test_cliente_inadimplente_recebe_423_com_detalhes(mock_entrada):
    mock_entrada.side_effect = EntradaBloqueada("Maria Souza", 12, 300.0, 2)
    r = client.post("/movimentacoes/entrada", json={"id_veiculo": 1, "id_vaga": 1})
    assert r.status_code == 423
    detalhe = r.json()["detail"]
    assert detalhe["codigo"] == "CLIENTE_INADIMPLENTE"
    assert detalhe["dias_atraso"] == 12
    assert "inadimplente há 12 dias" in detalhe["mensagem"]


@patch("rotas.movimentacao_rotas.movimentacao_controller.registrar_entrada")
def test_codigo_de_liberacao_e_repassado_ao_controller(mock_entrada):
    mock_entrada.return_value = {
        "id": 1, "id_veiculo": 1, "id_vaga": 1, "data_entrada": "2026-10-22T10:00:00", "id_usuario_entrada": 2,
    }
    r = client.post("/movimentacoes/entrada", json={"id_veiculo": 1, "id_vaga": 1, "codigo_liberacao": "1234"})
    assert r.status_code == 201
    enviado = mock_entrada.call_args[0][0]
    assert enviado.codigo_liberacao == "1234"
    assert enviado.id_usuario_entrada == 2


@patch("rotas.movimentacao_rotas.movimentacao_controller.registrar_entrada")
def test_codigo_incorreto_volta_como_erro_400(mock_entrada):
    mock_entrada.side_effect = ValueError("Código do administrador incorreto.")
    r = client.post("/movimentacoes/entrada", json={"id_veiculo": 1, "id_vaga": 1, "codigo_liberacao": "0000"})
    assert r.status_code == 400
    assert "incorreto" in r.json()["detail"]


@patch("rotas.movimentacao_rotas.movimentacao_controller.registrar_entrada")
def test_mensalista_sem_cota_livre_recebe_409_com_a_pergunta(mock_entrada):
    mock_entrada.side_effect = CotasEsgotadas("Maria Souza", 1, ["ABC-1234"])
    r = client.post("/movimentacoes/entrada", json={"id_veiculo": 2, "id_vaga": 3})
    assert r.status_code == 409
    d = r.json()["detail"]
    assert d["codigo"] == "COTAS_ESGOTADAS" and d["cotas"] == 1 and d["placas_em_uso"] == ["ABC-1234"]


@patch("rotas.movimentacao_rotas.movimentacao_controller.registrar_entrada")
def test_confirmacao_como_horista_e_repassada_ao_controller(mock_entrada):
    mock_entrada.return_value = {
        "id": 5, "id_veiculo": 2, "id_vaga": 3, "data_entrada": "2026-10-22T10:00:00", "id_usuario_entrada": 2,
    }
    r = client.post("/movimentacoes/entrada", json={"id_veiculo": 2, "id_vaga": 3, "como_horista": True})
    assert r.status_code == 201
    assert mock_entrada.call_args[0][0].como_horista is True


@patch("rotas.movimentacao_rotas.movimentacao_controller.consultar_modo_entrada")
def test_modo_de_entrada_e_consultavel(mock_modo):
    mock_modo.return_value = {
        "modo": "Mensalista", "tem_plano": True, "cotas": 2, "em_uso": 1, "esgotado": False,
        "placas_em_uso": ["ABC-1234"], "cliente_nome": "Maria Souza", "categoria": "Carro", "mensagem": "Mensalista: cota 2 de 2.",
    }
    r = client.get("/movimentacoes/modo-entrada/2")
    assert r.status_code == 200 and r.json()["modo"] == "Mensalista" and r.json()["em_uso"] == 1
