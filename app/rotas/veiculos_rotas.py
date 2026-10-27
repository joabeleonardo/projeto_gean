from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from modelos.schemas import VeiculoCreate, VeiculoPublico
from dependencies.database import get_db
from controllers import veiculos_controller

veiculos_router = APIRouter(prefix="/veiculos", tags=["Veículos"])

@veiculos_router.post("/", response_model=VeiculoPublico, status_code=status.HTTP_201_CREATED)
def inserir(veiculo: VeiculoCreate, db: Session = Depends(get_db)):
    try:
        return veiculos_controller.inserir_veiculo(veiculo, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@veiculos_router.get("/", response_model=List[VeiculoPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    try:
        return veiculos_controller.buscar_veiculos(db)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@veiculos_router.get("/{id_veiculo}", response_model=VeiculoPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_veiculo: int, db: Session = Depends(get_db)):
    try:
        return veiculos_controller.buscar_veiculo_por_id(id_veiculo, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@veiculos_router.put("/{id_veiculo}", response_model=VeiculoPublico, status_code=status.HTTP_200_OK)
def atualizar(id_veiculo: int, dados: VeiculoCreate, db: Session = Depends(get_db)):
    try:
        return veiculos_controller.atualizar_veiculo(id_veiculo, dados, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@veiculos_router.delete("/{id_veiculo}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_veiculo: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session = Depends(get_db)):
    try:
        veiculos_controller.deletar_veiculo(id_veiculo, id_usuario_logado, nome_usuario_logado, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))