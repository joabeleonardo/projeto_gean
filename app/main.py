from fastapi import FastAPI
from rotas.clientes_rotas import clientes_router
from rotas.veiculos_rotas import veiculos_router
from rotas.vagas_rotas import vagas_router
from rotas.precos_rotas import precos_router
from rotas.usuarios_rotas import usuarios_router
from rotas.movimentacao_rotas import movimentacao_router
from rotas.pagamentos_rotas import pagamentos_router 

from fastapi.middleware.cors import CORSMiddleware # ⚠️ Importe o CORS


app = FastAPI(
    title="Sistema de Estacionamento API",
    description="API para controle de estacionamento modularizada",
    version="1.0.0"
)

# --------------------------------------------------------
# CONFIGURAÇÃO DE CORS (Libera o acesso para o Frontend)
# --------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Permite qualquer origem (ideal para desenvolvimento local)
    allow_credentials=True,
    allow_methods=["*"],          # Permite todos os métodos (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],          # Permite todos os cabeçalhos
)

# Registro das Rotas[cite: 1]
app.include_router(clientes_router)
app.include_router(veiculos_router)
app.include_router(vagas_router)
app.include_router(precos_router)
app.include_router(usuarios_router)
app.include_router(movimentacao_router)
app.include_router(pagamentos_router)          # ⚠️ Registra o router de pagamentos

@app.get("/")
def read_root():
    return {"status": "API FastAPI operando com todos os módulos, incluindo Pagamentos!"}