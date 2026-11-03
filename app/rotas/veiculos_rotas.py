from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from typing import List

from modelos.schemas import VeiculoCreate, VeiculoPublico, VeiculoDetalhe
from entidades.entidades import Usuario
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual, exigir_admin
from controllers import veiculos_controller
from rotas._erros import tratar_erros, preencher_auditoria

veiculos_router = APIRouter(prefix="/veiculos", tags=["Veículos"], dependencies=[Depends(get_usuario_atual)])

# A rota fixa /busca precisa vir antes de /{id_veiculo}
@veiculos_router.get("/pagina", status_code=status.HTTP_200_OK)
def listar_pagina(
    q: str = "", placa: str = "", veiculo: str = "", proprietario: str = "", documento: str = "", tipo: str = "",
    ordem: str = "placa", pagina: int = 1, por_pagina: int = 10, db: Session = Depends(get_db),
):
    """Uma página de veículos, com filtros (placa, marca/modelo, dono, documento, tipo) e ordenação."""
    with tratar_erros():
        return veiculos_controller.listar_pagina(db, q, placa, veiculo, proprietario, documento, tipo, ordem, pagina, por_pagina)


@veiculos_router.get("/busca", response_model=List[VeiculoDetalhe], status_code=status.HTTP_200_OK)
def pesquisar(q: str = "", db: Session = Depends(get_db)):
    """Busca por placa, modelo, cor, nome ou CPF do dono."""
    with tratar_erros():
        return veiculos_controller.pesquisar_veiculos(q, db)


@veiculos_router.post("/", response_model=VeiculoPublico, status_code=status.HTTP_201_CREATED)
def inserir(dados: VeiculoCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return veiculos_controller.inserir_veiculo(dados, db)


@veiculos_router.get("/", response_model=List[VeiculoPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    with tratar_erros():
        return veiculos_controller.buscar_veiculos(db)


@veiculos_router.get("/{id_veiculo}", response_model=VeiculoPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_veiculo: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return veiculos_controller.buscar_veiculo_por_id(id_veiculo, db)


@veiculos_router.put("/{id_veiculo}", response_model=VeiculoPublico, status_code=status.HTTP_200_OK)
def atualizar(id_veiculo: int, dados: VeiculoCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return veiculos_controller.atualizar_veiculo(id_veiculo, dados, db)


@veiculos_router.delete("/{id_veiculo}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_veiculo: int, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    # Excluir registros é permitido apenas a administradores
    with tratar_erros():
        veiculos_controller.deletar_veiculo(id_veiculo, usuario.id, usuario.nome, db)
