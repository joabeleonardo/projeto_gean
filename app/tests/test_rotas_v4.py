"""Rotas novas da 4ª rodada (com os controllers simulados): relógio do servidor, logs, paginação, troco."""
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient as ClienteHttp

from dependencies.auth import get_usuario_atual
from dependencies.database import get_db
from entidades.entidades import Pagamento, PerfilEnum, Usuario
from rotas.clientes_rotas import clientes_router
from rotas.logs_rotas import logs_router
from rotas.movimentacao_rotas import movimentacao_router
from rotas.pagamentos_rotas import pagamentos_router
from rotas.relatorios_rotas import relatorios_router
from rotas.sistema_rotas import sistema_router

app = FastAPI()
for r in (sistema_router, logs_router, clientes_router, pagamentos_router, movimentacao_router, relatorios_router):
    app.include_router(r)
app.dependency_overrides[get_db] = lambda: MagicMock()
client = ClienteHttp(app)


def logar_como(perfil):
    app.dependency_overrides[get_usuario_atual] = lambda: Usuario(id=2, nome="Fulano", login="fulano", senha="x", perfil=perfil)


# ------------------------------------------------------------ hora do servidor
def test_hora_do_servidor_nao_exige_login_e_vem_sem_fuso():
    app.dependency_overrides.pop(get_usuario_atual, None)
    r = client.get("/servidor/hora")
    assert r.status_code == 200
    agora = datetime.fromisoformat(r.json()["agora"])
    assert agora.tzinfo is None and r.json()["hoje"] == agora.date().isoformat()


# ----------------------------------------------------------------------- logs
def test_logs_so_para_administrador():
    logar_como(PerfilEnum.Operador)
    assert client.get("/logs/").status_code == 403


@patch("rotas.logs_rotas.logs.listar_logs")
def test_administrador_consulta_logs_com_filtros(mock_listar):
    logar_como(PerfilEnum.Administrador)
    mock_listar.return_value = {"itens": [], "total": 0, "pagina": 2, "por_pagina": 20, "paginas": 1}
    r = client.get("/logs/?entidade=Preço&acao=ALTERAR&id_usuario=3&q=valor&pagina=2&por_pagina=20")
    assert r.status_code == 200
    args = mock_listar.call_args[0]
    assert args[2] == 3 and args[3] == "Preço" and args[4] == "ALTERAR" and args[5] == "valor" and args[6:] == (2, 20)


def test_novos_relatorios_so_para_administrador():
    logar_como(PerfilEnum.Operador)
    for rota in ("caixa", "clientes", "veiculos", "inadimplentes", "recebimentos-por-cliente"):
        assert client.get(f"/relatorios/{rota}").status_code == 403, rota


# ------------------------------------------------------------------ paginação
@patch("rotas.clientes_rotas.clientes_controller.listar_pagina")
def test_clientes_paginados_repassam_filtros_e_pagina(mock_listar):
    logar_como(PerfilEnum.Operador)
    mock_listar.return_value = {"itens": [], "total": 0, "pagina": 2, "por_pagina": 20, "paginas": 1}
    r = client.get("/clientes/pagina?nome=Ana&documento=529&tipo=mensalista&pais=estrangeiro&ordem=documento&pagina=2&por_pagina=20")
    assert r.status_code == 200
    db, q, nome, documento, telefone, placa, tipo, pais, ordem, pagina, por_pagina = mock_listar.call_args[0]
    assert (nome, documento, tipo, pais, ordem, pagina, por_pagina) == ("Ana", "529", "mensalista", "estrangeiro", "documento", 2, 20)


@patch("rotas.pagamentos_rotas.pagamentos_controller.listar_pagamentos_pagina")
def test_pagamentos_paginados(mock_listar):
    logar_como(PerfilEnum.Operador)
    mock_listar.return_value = {"itens": [], "total": 0, "pagina": 1, "por_pagina": 10, "paginas": 1}
    assert client.get("/pagamentos/pagina?status_pagamento=Pendente&cliente=Maria").status_code == 200
    assert mock_listar.call_args[0][3] == "Pendente" and mock_listar.call_args[0][5] == "Maria"


# ---------------------------------------------------------------------- troco
@patch("rotas.pagamentos_rotas.pagamentos_controller.baixar_pagamento")
def test_baixa_repassa_o_valor_recebido_em_dinheiro(mock_baixa):
    logar_como(PerfilEnum.Operador)
    mock_baixa.return_value = Pagamento(id=1, tipo_cobranca="Mensal", valor_total=120.0, status="Pago",
                                        forma_pagamento="Dinheiro", valor_recebido=200.0, troco=80.0)
    r = client.put("/pagamentos/1/baixa", json={"forma_pagamento": "Dinheiro", "valor_recebido": 200})
    assert r.status_code == 200 and r.json()["troco"] == 80.0
    assert mock_baixa.call_args[0][4] == 200.0


@patch("rotas.movimentacao_rotas.movimentacao_controller.registrar_saida")
def test_saida_repassa_valor_recebido(mock_saida):
    logar_como(PerfilEnum.Operador)
    mock_saida.return_value = {"id": 1, "id_veiculo": 1, "id_vaga": 1, "data_entrada": "2026-10-22T10:00:00",
                               "id_usuario_entrada": 2, "valor_total": 120.0, "troco": 80.0}
    r = client.put("/movimentacoes/1/saida", json={"forma_pagamento": "Dinheiro", "valor_recebido": 200})
    assert r.status_code == 200 and r.json()["troco"] == 80.0
    assert mock_saida.call_args[0][1].valor_recebido == 200.0


def test_baixa_em_dinheiro_sem_forma_e_rejeitada_pela_validacao():
    logar_como(PerfilEnum.Operador)
    assert client.put("/pagamentos/1/baixa", json={"valor_recebido": 10}).status_code == 422
