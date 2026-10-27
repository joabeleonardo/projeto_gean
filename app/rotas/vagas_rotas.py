from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from modelos.schemas import VagaCreate, VagaPublico
from entidades.entidades import Vaga
from dependencies.database import get_db
from controllers import vagas_controller

vagas_router = APIRouter(prefix="/vagas", tags=["Vagas"])

@vagas_router.post("/", response_model=VagaPublico, status_code=status.HTTP_201_CREATED)
def inserir(vaga: VagaCreate, db: Session = Depends(get_db)):
    try:
        return vagas_controller.inserir_vaga(vaga, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@vagas_router.get("/", response_model=List[VagaPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    try:
        return vagas_controller.buscar_vagas(db)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@vagas_router.get("/{id_vaga}", response_model=VagaPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_vaga: int, db: Session = Depends(get_db)):
    try:
        return vagas_controller.buscar_vaga_por_id(id_vaga, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@vagas_router.put("/{id_vaga}", response_model=VagaPublico, status_code=status.HTTP_200_OK)
def atualizar(id_vaga: int, dados: VagaCreate, db: Session = Depends(get_db)):
    try:
        return vagas_controller.atualizar_vaga(id_vaga, dados, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@vagas_router.delete("/{id_vaga}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_vaga: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session = Depends(get_db)):
    try:
        vagas_controller.deletar_vaga(id_vaga, id_usuario_logado, nome_usuario_logado, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))