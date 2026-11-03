import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from config.database import engine
from controllers.logs import registrar_hooks
from controllers.mensalidade_controller import gerar_cobrancas_se_necessario
from controllers.usuarios_controller import garantir_admin_inicial
from rotas.auth_rotas import auth_router
from rotas.cadastro_rotas import cadastro_router, enderecos_router
from rotas.clientes_rotas import clientes_router
from rotas.dashboard_rotas import dashboard_router
from rotas.logs_rotas import logs_router
from rotas.sistema_rotas import sistema_router
from rotas.mensalidades_rotas import mensalidades_router
from rotas.movimentacao_rotas import movimentacao_router
from rotas.pagamentos_rotas import pagamentos_router
from rotas.precos_rotas import precos_router
from rotas.relatorios_rotas import relatorios_router
from rotas.usuarios_rotas import usuarios_router
from rotas.vagas_rotas import vagas_router
from rotas.veiculos_rotas import veiculos_router

logger = logging.getLogger("estacionamento")
registrar_hooks()   # logs automáticos do sistema (quem fez o quê)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Na primeira execução (tabela de usuários vazia) cria o administrador inicial
    try:
        with Session(engine) as db:
            if garantir_admin_inicial(db):
                logger.warning("Usuário inicial criado: login 'admin'. Troque a senha no primeiro acesso.")
                print("\n>>> Usuário inicial criado: login 'admin' (senha em ADMIN_SENHA_INICIAL, padrão 'admin123').")
                print(">>> Troque a senha no primeiro acesso.\n")
    except Exception as erro:  # banco fora do ar não deve impedir a API de subir
        logger.error("Não foi possível verificar o usuário inicial: %s", erro)
    # lança as mensalidades vencidas que ainda não existem (idempotente)
    try:
        with Session(engine) as db:
            gerar_cobrancas_se_necessario(db)
    except Exception as erro:
        logger.error("Não foi possível gerar as cobranças mensais: %s", erro)
    yield


app = FastAPI(
    title="Sistema de Estacionamento API",
    description="API para controle de estacionamento modularizada",
    version="2.0.0",
    lifespan=lifespan,
)

# --------------------------------------------------------
# CORS
# A autenticação usa token no cabeçalho (não cookies), então o CORS aberto não
# expõe sessão. Em produção, liste os endereços permitidos em CORS_ORIGINS
# (separados por vírgula), ex.: CORS_ORIGINS=http://127.0.0.1:5500
# --------------------------------------------------------
origens = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(veiculos_router)
app.include_router(cadastro_router)
app.include_router(enderecos_router)
app.include_router(vagas_router)
app.include_router(precos_router)
app.include_router(usuarios_router)
app.include_router(mensalidades_router)
app.include_router(movimentacao_router)
app.include_router(pagamentos_router)
app.include_router(dashboard_router)
app.include_router(logs_router)
app.include_router(sistema_router)
app.include_router(relatorios_router)


@app.get("/")
def read_root():
    return {"status": "API do Sistema de Estacionamento no ar", "docs": "/docs"}


# Opcional: serve o frontend pela própria API (http://127.0.0.1:8000/sistema/html/login.html)
_frontend = Path(__file__).resolve().parent.parent / "frontend"
if _frontend.is_dir():
    app.mount("/sistema", StaticFiles(directory=_frontend), name="sistema")
