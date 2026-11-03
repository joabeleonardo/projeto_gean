from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from controllers import logs
from dependencies.auth import exigir_admin
from dependencies.database import get_db
from rotas._erros import tratar_erros

# Os logs mostram a atividade de todos os usuários: só administradores consultam
logs_router = APIRouter(prefix="/logs", tags=["Logs"], dependencies=[Depends(exigir_admin)])


@logs_router.get("/", status_code=status.HTTP_200_OK)
def listar(
    inicio: Optional[date] = None, fim: Optional[date] = None, id_usuario: Optional[int] = None,
    entidade: Optional[str] = None, acao: Optional[str] = None, q: Optional[str] = None,
    pagina: int = 1, por_pagina: int = 20, db: Session = Depends(get_db),
):
    """Quem fez o quê e quando, com filtros por período, usuário, tipo de registro, ação e texto."""
    with tratar_erros():
        return logs.listar_logs(db, inicio, fim, id_usuario, entidade, acao, q, pagina, por_pagina)
