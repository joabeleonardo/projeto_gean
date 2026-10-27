from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from modelos.schemas import ClienteCreate, ClientePublico
from entidades.entidades import Cliente
from dependencies.database import get_db
from controllers import clientes_controller

clientes_router = APIRouter(prefix="/clientes", tags=["Clientes"])

@clientes_router.post("/", response_model=ClientePublico, status_code=status.HTTP_201_CREATED)
def inserir(cliente: ClienteCreate, db: Session = Depends(get_db)):
    try:
        return clientes_controller.inserir_cliente(cliente, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@clientes_router.get("/", response_model=List[ClientePublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    try:
        return clientes_controller.buscar_clientes(db)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@clientes_router.get("/{id_cliente}", response_model=Cliente, status_code=status.HTTP_200_OK)
def buscar_por_id(id_cliente: int, db: Session = Depends(get_db)):
    try:
        return clientes_controller.buscar_cliente_por_id(id_cliente, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@clientes_router.put("/{id_cliente}", response_model=Cliente, status_code=status.HTTP_200_OK)
def atualizar(id_cliente: int, dados: ClienteCreate, db: Session = Depends(get_db)):
    try:
        return clientes_controller.atualizar_cliente(id_cliente, dados, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@clientes_router.delete("/{id_cliente}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_cliente: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session = Depends(get_db)):
    try:
        clientes_controller.deletar_cliente(id_cliente, id_usuario_logado, nome_usuario_logado, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))