from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from dependencies.database import get_db
from entidades.entidades import Usuario
from servicos.seguranca import ler_token

_bearer = HTTPBearer(auto_error=False)


def eh_admin(usuario) -> bool:
    perfil = getattr(usuario.perfil, "value", usuario.perfil)
    # aceita valores antigos gravados no banco (ex.: "admin", "administrador")
    return str(perfil).strip().lower() in ("administrador", "admin")


def get_usuario_atual(
    credenciais: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Exige login: lê o token do cabeçalho Authorization e devolve o usuário."""
    nao_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciais is None:
        raise nao_autenticado
    dados = ler_token(credenciais.credentials)
    if not dados:
        raise nao_autenticado
    try:
        usuario = db.get(Usuario, int(dados["sub"]))
    except (KeyError, ValueError, TypeError):
        raise nao_autenticado
    if usuario is None:
        raise nao_autenticado
    return usuario


def exigir_admin(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
    """Exige login de um Administrador."""
    if not eh_admin(usuario):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return usuario
