"""Senhas (hash) e tokens de login (JWT).

Este módulo não depende de FastAPI nem do banco, para poder ser testado sozinho.
"""
import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from dotenv import load_dotenv

# O .env fica em app/ (mesmo lugar usado por config/database.py)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger("estacionamento.seguranca")

PREFIXO_HASH = "pbkdf2_sha256"
ITERACOES = 600_000
ALGORITMO_JWT = "HS256"

_chave_temporaria: Optional[str] = None


def _chave_secreta() -> str:
    """Lê SECRET_KEY do .env. Sem ela, gera uma chave temporária (os logins
    deixam de valer quando o servidor reinicia)."""
    global _chave_temporaria
    chave = os.getenv("SECRET_KEY")
    if chave:
        return chave
    if _chave_temporaria is None:
        _chave_temporaria = secrets.token_urlsafe(48)
        logger.warning(
            "SECRET_KEY não definida no .env: usando chave temporária. "
            "Defina SECRET_KEY para manter os logins após reiniciar o servidor."
        )
    return _chave_temporaria


def _minutos_expiracao() -> int:
    try:
        return int(os.getenv("TOKEN_EXPIRA_MINUTOS", "480"))
    except ValueError:
        return 480


# ---------------------------------------------------------------- senhas
def gerar_hash_senha(senha: str) -> str:
    sal = os.urandom(16)
    derivada = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)
    return "$".join([
        PREFIXO_HASH,
        str(ITERACOES),
        base64.b64encode(sal).decode("ascii"),
        base64.b64encode(derivada).decode("ascii"),
    ])


def senha_esta_em_hash(armazenada: str) -> bool:
    return bool(armazenada) and armazenada.startswith(PREFIXO_HASH + "$")


def verificar_senha(senha: str, armazenada: str) -> bool:
    """Confere a senha. Aceita também senhas antigas salvas em texto puro
    (o login regrava essas senhas já com hash)."""
    if not armazenada:
        return False
    if not senha_esta_em_hash(armazenada):
        return hmac.compare_digest(senha.encode("utf-8"), armazenada.encode("utf-8"))
    try:
        _, iteracoes, sal_b64, hash_b64 = armazenada.split("$")
        sal = base64.b64decode(sal_b64)
        esperado = base64.b64decode(hash_b64)
        obtido = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, int(iteracoes))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(obtido, esperado)


# ---------------------------------------------------------------- tokens
def criar_token(id_usuario: int, perfil: str) -> str:
    agora = datetime.now(timezone.utc)
    carga = {
        "sub": str(id_usuario),
        "perfil": perfil,
        "iat": agora,
        "exp": agora + timedelta(minutes=_minutos_expiracao()),
    }
    return jwt.encode(carga, _chave_secreta(), algorithm=ALGORITMO_JWT)


def ler_token(token: str) -> Optional[dict]:
    """Devolve o conteúdo do token ou None se for inválido/expirado."""
    try:
        return jwt.decode(token, _chave_secreta(), algorithms=[ALGORITMO_JWT])
    except jwt.PyJWTError:
        return None
