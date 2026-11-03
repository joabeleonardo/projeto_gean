from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from typing import List

from modelos.schemas import SituacaoVaga, VagaCreate, VagaPublico
from entidades.entidades import Usuario
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual, exigir_admin
from controllers import vagas_controller
from rotas._erros import tratar_erros, preencher_auditoria

vagas_router = APIRouter(prefix="/vagas", tags=["Vagas"], dependencies=[Depends(get_usuario_atual)])

@vagas_router.post("/", response_model=VagaPublico, status_code=status.HTTP_201_CREATED)
def inserir(dados: VagaCreate, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return vagas_controller.inserir_vaga(dados, db)


@vagas_router.get("/", response_model=List[VagaPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    with tratar_erros():
        return vagas_controller.buscar_vagas(db)


@vagas_router.get("/{id_vaga}", response_model=VagaPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_vaga: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return vagas_controller.buscar_vaga_por_id(id_vaga, db)


@vagas_router.put("/{id_vaga}", response_model=VagaPublico, status_code=status.HTTP_200_OK)
def atualizar(id_vaga: int, dados: VagaCreate, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return vagas_controller.atualizar_vaga(id_vaga, dados, db)


@vagas_router.delete("/{id_vaga}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_vaga: int, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    # Excluir registros é permitido apenas a administradores
    with tratar_erros():
        vagas_controller.deletar_vaga(id_vaga, usuario.id, usuario.nome, db)


@vagas_router.put("/{id_vaga}/situacao", response_model=VagaPublico, status_code=status.HTTP_200_OK)
def definir_situacao(
    id_vaga: int, dados: SituacaoVaga, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)
):
    """Ativa ou inativa a vaga (ex.: reforma). Vaga inativa não recebe entradas."""
    with tratar_erros():
        return vagas_controller.definir_situacao(id_vaga, dados.ativa, usuario, db)
