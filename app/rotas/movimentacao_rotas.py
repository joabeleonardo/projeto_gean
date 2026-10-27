from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from modelos.schemas import MovimentacaoEntradaCreate, MovimentacaoSaidaUpdate, MovimentacaoPublico
from entidades.entidades import Movimentacao
from dependencies.database import get_db
from controllers import movimentacao_controller

movimentacao_router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])

@movimentacao_router.post("/entrada", response_model=MovimentacaoPublico, status_code=status.HTTP_201_CREATED)
def entrada(mov: MovimentacaoEntradaCreate, db: Session = Depends(get_db)):
    try:
        return movimentacao_controller.registrar_entrada(mov, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@movimentacao_router.get("/", response_model=List[MovimentacaoPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    try:
        return movimentacao_controller.buscar_movimentacoes(db)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@movimentacao_router.get("/{id_movimentacao}", response_model=MovimentacaoPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_movimentacao: int, db: Session = Depends(get_db)):
    try:
        return movimentacao_controller.buscar_movimentacao_por_id(id_movimentacao, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@movimentacao_router.put("/{id_movimentacao}/saida", response_model=MovimentacaoPublico, status_code=status.HTTP_200_OK)
def saida(id_movimentacao: int, dados_saida: MovimentacaoSaidaUpdate, db: Session = Depends(get_db)):
    try:
        return movimentacao_controller.registrar_saida(id_movimentacao, dados_saida, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))