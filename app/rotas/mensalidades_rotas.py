from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from controllers import mensalidade_controller
from dependencies.auth import exigir_admin, get_usuario_atual
from dependencies.database import get_db
from entidades.entidades import Usuario
from modelos.schemas import (
    CapacidadeMensalistas, MensalidadeCotas, MensalidadeCreate, MensalidadeDetalhe, MensalidadePublico,
)
from rotas._erros import tratar_erros

mensalidades_router = APIRouter(
    prefix="/mensalidades", tags=["Mensalidades"], dependencies=[Depends(get_usuario_atual)]
)


@mensalidades_router.get("/", response_model=List[MensalidadeDetalhe], status_code=status.HTTP_200_OK)
def listar_ativas(db: Session = Depends(get_db)):
    """Planos de mensalista ativos (quem é mensalista, categoria, cotas e cotas em uso)."""
    with tratar_erros():
        return mensalidade_controller.listar_ativas(db)


# Rotas fixas precisam vir antes de /{id_mensalidade}
@mensalidades_router.get("/capacidade", response_model=List[CapacidadeMensalistas], status_code=status.HTTP_200_OK)
def capacidade(db: Session = Depends(get_db)):
    """Vagas de mensalista x cotas contratadas, por categoria."""
    with tratar_erros():
        return mensalidade_controller.capacidade(db)


@mensalidades_router.get("/vagas-premium", status_code=status.HTTP_200_OK)
def vagas_premium(db: Session = Depends(get_db)):
    """Vagas premium (exclusivas), com o cliente que reservou cada uma."""
    with tratar_erros():
        return mensalidade_controller.listar_vagas_premium(db)


@mensalidades_router.post("/gerar-cobrancas", status_code=status.HTTP_200_OK)
def gerar_cobrancas(usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    """Cria as mensalidades vencidas que ainda não foram lançadas (não duplica)."""
    with tratar_erros():
        return mensalidade_controller.gerar_cobrancas(db)


@mensalidades_router.post("/", response_model=MensalidadePublico, status_code=status.HTTP_201_CREATED)
def aderir(dados: MensalidadeCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    """Adesão ao plano de mensalista (vale a partir da data de adesão; cria a 1ª cobrança)."""
    with tratar_erros():
        plano = mensalidade_controller.aderir(dados, usuario, db)
        return plano.model_dump(mode="json")


@mensalidades_router.put("/{id_mensalidade}/cotas", response_model=MensalidadePublico, status_code=status.HTTP_200_OK)
def alterar_cotas(
    id_mensalidade: int, dados: MensalidadeCotas,
    usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db),
):
    with tratar_erros():
        plano = mensalidade_controller.alterar_cotas(id_mensalidade, dados.cotas, usuario, db)
        return plano.model_dump(mode="json")


@mensalidades_router.put("/{id_mensalidade}/cancelar", response_model=MensalidadePublico, status_code=status.HTTP_200_OK)
def cancelar(id_mensalidade: int, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    with tratar_erros():
        plano = mensalidade_controller.cancelar(id_mensalidade, usuario, db)
        return plano.model_dump(mode="json")
