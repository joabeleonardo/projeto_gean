from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from typing import List

from modelos.schemas import ClienteCreate, ClientePublico, ClienteInadimplente
from entidades.entidades import Usuario
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual, exigir_admin
from controllers import clientes_controller, inadimplencia_controller
from rotas._erros import tratar_erros, preencher_auditoria

clientes_router = APIRouter(prefix="/clientes", tags=["Clientes"], dependencies=[Depends(get_usuario_atual)])

# Rotas fixas (/busca, /inadimplentes) precisam vir antes de /{id_cliente}
@clientes_router.get("/pagina", status_code=status.HTTP_200_OK)
def listar_pagina(
    q: str = "", nome: str = "", documento: str = "", telefone: str = "", placa: str = "", tipo: str = "",
    pais: str = "", ordem: str = "nome", pagina: int = 1, por_pagina: int = 10, db: Session = Depends(get_db),
):
    """Uma página de clientes, com filtros (nome, documento, telefone, placa, tipo, país) e ordenação."""
    with tratar_erros():
        return clientes_controller.listar_pagina(db, q, nome, documento, telefone, placa, tipo, pais, ordem, pagina, por_pagina)


@clientes_router.get("/inadimplentes/pagina", status_code=status.HTTP_200_OK)
def inadimplentes_pagina(nome: str = "", documento: str = "", pagina: int = 1, por_pagina: int = 10, db: Session = Depends(get_db)):
    with tratar_erros():
        return inadimplencia_controller.listar_inadimplentes_pagina(db, nome, documento, pagina, por_pagina)


@clientes_router.get("/{id_cliente}/cobrancas-pendentes", status_code=status.HTTP_200_OK)
def cobrancas_pendentes(id_cliente: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return inadimplencia_controller.cobrancas_pendentes(db, id_cliente)


@clientes_router.get("/inadimplentes", response_model=List[ClienteInadimplente], status_code=status.HTTP_200_OK)
def inadimplentes(db: Session = Depends(get_db)):
    """Clientes com cobrança vencida e não paga, do maior atraso para o menor."""
    with tratar_erros():
        return inadimplencia_controller.listar_inadimplentes(db)



@clientes_router.get("/busca", response_model=List[ClientePublico], status_code=status.HTTP_200_OK)
def pesquisar(q: str = "", db: Session = Depends(get_db)):
    """Busca por nome, CPF, telefone ou placa de veículo."""
    with tratar_erros():
        return clientes_controller.pesquisar_clientes(q, db)


@clientes_router.post("/", response_model=ClientePublico, status_code=status.HTTP_201_CREATED)
def inserir(dados: ClienteCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return clientes_controller.inserir_cliente(dados, db)


@clientes_router.get("/", response_model=List[ClientePublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    with tratar_erros():
        return clientes_controller.buscar_clientes(db)


@clientes_router.get("/{id_cliente}", response_model=ClientePublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_cliente: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return clientes_controller.buscar_cliente_por_id(id_cliente, db)


@clientes_router.put("/{id_cliente}", response_model=ClientePublico, status_code=status.HTTP_200_OK)
def atualizar(id_cliente: int, dados: ClienteCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    preencher_auditoria(dados, usuario)
    with tratar_erros():
        return clientes_controller.atualizar_cliente(id_cliente, dados, db)


@clientes_router.delete("/{id_cliente}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_cliente: int, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    # Excluir registros é permitido apenas a administradores
    with tratar_erros():
        clientes_controller.deletar_cliente(id_cliente, usuario.id, usuario.nome, db)
