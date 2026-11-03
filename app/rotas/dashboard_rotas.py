from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from controllers import dashboard_controller
from dependencies.auth import get_usuario_atual
from dependencies.database import get_db
from entidades.entidades import Usuario
from rotas._erros import tratar_erros

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@dashboard_router.get("/resumo", status_code=status.HTTP_200_OK)
def resumo(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    """Dados do painel inicial. Valores em dinheiro só vêm para administradores."""
    with tratar_erros():
        return dashboard_controller.resumo(usuario, db)
