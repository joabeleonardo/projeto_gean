from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from controllers import cadastro_controller
from dependencies.auth import get_usuario_atual
from dependencies.database import get_db
from entidades.entidades import Usuario
from modelos.schemas import (
    CadastroCompletoCreate, CadastroCompletoPublico, ClienteAtualizar, ClienteCompleto, EnderecoEntrada, EnderecoPublico,
)
from rotas._erros import tratar_erros

cadastro_router = APIRouter(prefix="/cadastro", tags=["Cadastro"], dependencies=[Depends(get_usuario_atual)])
enderecos_router = APIRouter(prefix="/enderecos", tags=["Endereços"], dependencies=[Depends(get_usuario_atual)])


@cadastro_router.post("/completo", response_model=CadastroCompletoPublico, status_code=status.HTTP_201_CREATED)
def cadastro_completo(
    dados: CadastroCompletoCreate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Cliente + endereço + primeiro veículo em uma única operação."""
    with tratar_erros():
        return cadastro_controller.cadastrar_completo(dados, usuario, db)


@cadastro_router.get("/cliente/{id_cliente}", response_model=ClienteCompleto, status_code=status.HTTP_200_OK)
def cliente_completo(id_cliente: int, db: Session = Depends(get_db)):
    """Cliente + endereço + veículos + planos, para a tela de edição."""
    with tratar_erros():
        return cadastro_controller.obter_cliente_completo(id_cliente, db)


@cadastro_router.put("/cliente/{id_cliente}", response_model=ClienteCompleto, status_code=status.HTTP_200_OK)
def atualizar_cliente(
    id_cliente: int,
    dados: ClienteAtualizar,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Edita nome, CPF, telefone e endereço do cliente."""
    with tratar_erros():
        return cadastro_controller.atualizar_cliente_completo(id_cliente, dados, usuario, db)


@enderecos_router.get("/{id_endereco}", response_model=EnderecoPublico, status_code=status.HTTP_200_OK)
def buscar_endereco(id_endereco: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return cadastro_controller.buscar_endereco(id_endereco, db)


@enderecos_router.put("/{id_endereco}", response_model=EnderecoPublico, status_code=status.HTTP_200_OK)
def atualizar_endereco(
    id_endereco: int,
    dados: EnderecoEntrada,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    with tratar_erros():
        return cadastro_controller.atualizar_endereco(id_endereco, dados, usuario, db)
