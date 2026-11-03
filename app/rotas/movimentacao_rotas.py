from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from typing import List

from modelos.schemas import (
    MovimentacaoEntradaCreate, MovimentacaoSaidaUpdate, MovimentacaoPublico, MovimentacaoPatio, PreviaSaida, ModoEntrada,
)
from entidades.entidades import Usuario
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual
from controllers import movimentacao_controller
from rotas._erros import tratar_erros, preencher_auditoria

movimentacao_router = APIRouter(
    prefix="/movimentacoes", tags=["Movimentações"], dependencies=[Depends(get_usuario_atual)]
)


@movimentacao_router.post("/entrada", response_model=MovimentacaoPublico, status_code=status.HTTP_201_CREATED)
def entrada(mov: MovimentacaoEntradaCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    preencher_auditoria(mov, usuario)
    mov.id_usuario_entrada = usuario.id
    with tratar_erros():
        return movimentacao_controller.registrar_entrada(mov, db)


@movimentacao_router.get("/", response_model=List[MovimentacaoPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    with tratar_erros():
        return movimentacao_controller.buscar_movimentacoes(db)


# Rotas fixas (/patio) precisam vir antes de /{id_movimentacao}
@movimentacao_router.get("/patio", response_model=List[MovimentacaoPatio], status_code=status.HTTP_200_OK)
def no_patio(db: Session = Depends(get_db)):
    """Veículos que estão no pátio agora."""
    with tratar_erros():
        return movimentacao_controller.listar_no_patio(db)


@movimentacao_router.get("/modo-entrada/{id_veiculo}", response_model=ModoEntrada, status_code=status.HTTP_200_OK)
def modo_entrada(id_veiculo: int, db: Session = Depends(get_db)):
    """Como o veículo entraria agora: mensalista (usa uma cota) ou horista."""
    with tratar_erros():
        return movimentacao_controller.consultar_modo_entrada(id_veiculo, db)


@movimentacao_router.get("/{id_movimentacao}", response_model=MovimentacaoPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_movimentacao: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return movimentacao_controller.buscar_movimentacao_por_id(id_movimentacao, db)


@movimentacao_router.get("/{id_movimentacao}/previa-saida", response_model=PreviaSaida, status_code=status.HTTP_200_OK)
def previa_saida(id_movimentacao: int, db: Session = Depends(get_db)):
    """Quanto seria cobrado se o veículo saísse agora."""
    with tratar_erros():
        return movimentacao_controller.previa_saida(id_movimentacao, db)


@movimentacao_router.put("/{id_movimentacao}/saida", response_model=MovimentacaoPublico, status_code=status.HTTP_200_OK)
def saida(
    id_movimentacao: int,
    dados_saida: MovimentacaoSaidaUpdate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    preencher_auditoria(dados_saida, usuario)
    dados_saida.id_usuario_saida = usuario.id
    with tratar_erros():
        return movimentacao_controller.registrar_saida(id_movimentacao, dados_saida, db)
