from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

<<<<<<< HEAD
from modelos.schemas import UsuarioCreate, UsuarioUpdate, UsuarioPublico
from entidades.entidades import Usuario
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual, exigir_admin
from controllers import usuarios_controller
from rotas._erros import tratar_erros, preencher_auditoria

usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuários"], dependencies=[Depends(exigir_admin)])

@usuarios_router.post("/", response_model=UsuarioPublico, status_code=status.HTTP_201_CREATED)
def inserir(dados: UsuarioCreate, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return usuarios_controller.inserir_usuario(dados, db)


@usuarios_router.get("/", response_model=List[UsuarioPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    with tratar_erros():
        return usuarios_controller.buscar_usuarios(db)


@usuarios_router.get("/{id_usuario}", response_model=UsuarioPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_usuario: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return usuarios_controller.buscar_usuario_por_id(id_usuario, db)


@usuarios_router.put("/{id_usuario}", response_model=UsuarioPublico, status_code=status.HTTP_200_OK)
def atualizar(id_usuario: int, dados: UsuarioUpdate, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return usuarios_controller.atualizar_usuario(id_usuario, dados, db)


@usuarios_router.delete("/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_usuario: int, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    if id_usuario == usuario.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Você não pode excluir o próprio usuário.")
    with tratar_erros():
        usuarios_controller.deletar_usuario(id_usuario, usuario.id, usuario.nome, db)
=======
from modelos.schemas import UsuarioCreate, UsuarioPublico
from entidades.entidades import Usuario
from dependencies.database import get_db
from controllers import usuarios_controller

usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuários"])

@usuarios_router.post("/", response_model=UsuarioPublico, status_code=status.HTTP_201_CREATED)
def inserir(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    try:
        return usuarios_controller.inserir_usuario(usuario, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@usuarios_router.get("/", response_model=List[UsuarioPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    try:
        return usuarios_controller.buscar_usuarios(db)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@usuarios_router.get("/{id_usuario}", response_model=UsuarioPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_usuario: int, db: Session = Depends(get_db)):
    try:
        return usuarios_controller.buscar_usuario_por_id(id_usuario, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@usuarios_router.put("/{id_usuario}", response_model=UsuarioPublico, status_code=status.HTTP_200_OK)
def atualizar(id_usuario: int, dados: UsuarioCreate, db: Session = Depends(get_db)):
    try:
        return usuarios_controller.atualizar_usuario(id_usuario, dados, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@usuarios_router.delete("/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_usuario: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session = Depends(get_db)):
    try:
        usuarios_controller.deletar_usuario(id_usuario, id_usuario_logado, nome_usuario_logado, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
>>>>>>> e1168e0b2866878a1368d6f2183807561c179272
