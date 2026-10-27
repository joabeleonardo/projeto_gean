
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Carrega as variáveis do arquivo .env
load_dotenv()

# Obtém as configurações do banco através das variáveis de ambiente
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


if not DB_USER:
    raise ValueError("A variável de ambiente DB_USER não foi configurada.")

if not DB_PASSWORD:
    raise ValueError("A variável de ambiente DB_PASSWORD não foi configurada.")

if not DB_HOST:
    raise ValueError("A variável de ambiente DB_HOST não foi configurada.")

if not DB_NAME:
    raise ValueError("A variável de ambiente DB_NAME não foi configurada.")


# URL de conexão utilizando o driver PyMySQL

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# Cria o engine de conexão com o MySQL
engine = create_engine(DATABASE_URL)


# Cria as sessões utilizadas para acessar o banco

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

