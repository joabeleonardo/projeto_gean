<<<<<<< HEAD
from fastapi import APIRouter, Depends, status
=======
from fastapi import APIRouter, Depends, HTTPException, status
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
from sqlmodel import Session
from typing import List

from modelos.schemas import PrecoCreate, PrecoPublico
<<<<<<< HEAD
from entidades.entidades import Usuario
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual, exigir_admin
from controllers import precos_controller
from rotas._erros import tratar_erros, preencher_auditoria

precos_router = APIRouter(prefix="/precos", tags=["Preços"], dependencies=[Depends(get_usuario_atual)])

@precos_router.post("/", response_model=PrecoPublico, status_code=status.HTTP_201_CREATED)
def inserir(dados: PrecoCreate, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return precos_controller.inserir_preco(dados, db)


@precos_router.get("/", response_model=List[PrecoPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    with tratar_erros():
        return precos_controller.buscar_precos(db)


@precos_router.get("/{id_preco}", response_model=PrecoPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_preco: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return precos_controller.buscar_preco_por_id(id_preco, db)


@precos_router.put("/{id_preco}", response_model=PrecoPublico, status_code=status.HTTP_200_OK)
def atualizar(id_preco: int, dados: PrecoCreate, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return precos_controller.atualizar_preco(id_preco, dados, db)


@precos_router.delete("/{id_preco}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_preco: int, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    # Excluir registros é permitido apenas a administradores
    with tratar_erros():
        precos_controller.deletar_preco(id_preco, usuario.id, usuario.nome, db)
=======
from entidades.entidades import Preco
from dependencies.database import get_db
from controllers import precos_controller

precos_router = APIRouter(prefix="/precos", tags=["Preços"])

@precos_router.post("/", response_model=PrecoPublico, status_code=status.HTTP_201_CREATED)
def inserir(preco: PrecoCreate, db: Session = Depends(get_db)):
    try:
        return precos_controller.inserir_preco(preco, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@precos_router.get("/", response_model=List[PrecoPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    try:
        return precos_controller.buscar_precos(db)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@precos_router.get("/{id_preco}", response_model=PrecoPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_preco: int, db: Session = Depends(get_db)):
    try:
        return precos_controller.buscar_preco_por_id(id_preco, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@precos_router.put("/{id_preco}", response_model=PrecoPublico, status_code=status.HTTP_200_OK)
def atualizar(id_preco: int, dados: PrecoCreate, db: Session = Depends(get_db)):
    try:
        return precos_controller.atualizar_preco(id_preco, dados, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@precos_router.delete("/{id_preco}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_preco: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session = Depends(get_db)):
    try:
        precos_controller.deletar_preco(id_preco, id_usuario_logado, nome_usuario_logado, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
