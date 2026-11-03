"""Configuração dos testes: valores de teste para as variáveis do .env,
para que os testes rodem sem MySQL e sem o arquivo .env."""
import os

for chave, valor in {
    "DB_HOST": "localhost",
    "DB_PORT": "3306",
    "DB_USER": "teste",
    "DB_PASSWORD": "teste",
    "DB_NAME": "teste",
    "SECRET_KEY": "chave-somente-para-testes",
}.items():
    os.environ.setdefault(chave, valor)
