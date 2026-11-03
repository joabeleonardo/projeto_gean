from fastapi import FastAPI
from sqlalchemy import text
from db.database import SessionLocal


app = FastAPI(
    title="Sistema de Cadastro de Clientes",
    description="API para gerenciamento de clientes.",
    version="0.1.0"
)


@app.get("/")
def raiz():
    return {
        "mensagem": "API de Cadastro de Clientes funcionando!"
    }


@app.get("/teste-conexao")
def teste_conexao():
    db = SessionLocal()

    try:
        # Executa uma consulta simples para testar a conexão
        db.execute(text("SELECT 1"))

        return {
            "sucesso": True,
            "mensagem": "Conexão com o banco de dados MySQL realizada com sucesso!"
        }

    except Exception as erro:
        return {
            "sucesso": False,
            "mensagem": "Falha ao conectar ao banco de dados MySQL.",
            "erro": str(erro)
        }

    finally:
        # Garante que a sessão seja encerrada
        db.close()