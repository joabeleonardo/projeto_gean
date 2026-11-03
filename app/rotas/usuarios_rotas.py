from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

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
