from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from modelos.schemas import (
    PagamentoCreate, PagamentoPublico, PagamentoDetalhe, StatusPagamentoEnum, TipoPagamentoEnum, BaixaPagamento,
)
from entidades.entidades import Usuario
from dependencies.database import get_db
from dependencies.auth import get_usuario_atual, exigir_admin
from controllers import pagamentos_controller
from rotas._erros import tratar_erros, preencher_auditoria

pagamentos_router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"], dependencies=[Depends(get_usuario_atual)])


@pagamentos_router.post("/", response_model=PagamentoPublico, status_code=status.HTTP_201_CREATED)
def inserir(pagamento: PagamentoCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    """O valor é calculado pelo servidor com o preço vigente; o valor enviado é ignorado."""
    preencher_auditoria(pagamento, usuario)
    pagamento.id_usuario_recebimento = usuario.id
    with tratar_erros():
        return pagamentos_controller.registrar_pagamento(pagamento, db)


@pagamentos_router.get("/", response_model=List[PagamentoPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    with tratar_erros():
        return pagamentos_controller.buscar_pagamentos(db)


# Rotas fixas (/detalhado) precisam vir antes de /{id_pagamento}
@pagamentos_router.get("/detalhado", response_model=List[PagamentoDetalhe], status_code=status.HTTP_200_OK)
def listar_detalhado(
    status_pagamento: Optional[StatusPagamentoEnum] = None,
    tipo: Optional[TipoPagamentoEnum] = None,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    db: Session = Depends(get_db),
):
    with tratar_erros():
        return pagamentos_controller.listar_pagamentos_detalhados(
            db, inicio, fim,
            status_pagamento.value if status_pagamento else None,
            tipo.value if tipo else None,
        )


@pagamentos_router.get("/pagina", status_code=status.HTTP_200_OK)
def listar_pagina(
    status_pagamento: Optional[StatusPagamentoEnum] = None, tipo: Optional[TipoPagamentoEnum] = None,
    cliente: Optional[str] = None, forma: Optional[str] = None, inicio: Optional[date] = None, fim: Optional[date] = None,
    pagina: int = 1, por_pagina: int = 10, db: Session = Depends(get_db),
):
    """Uma página de pagamentos (com cliente, placa e quem recebeu)."""
    with tratar_erros():
        return pagamentos_controller.listar_pagamentos_pagina(
            db, inicio, fim, status_pagamento.value if status_pagamento else None, tipo.value if tipo else None,
            cliente, forma, pagina, por_pagina)


@pagamentos_router.get("/{id_pagamento}", response_model=PagamentoPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_pagamento: int, db: Session = Depends(get_db)):
    with tratar_erros():
        return pagamentos_controller.buscar_pagamento_por_id(id_pagamento, db)


@pagamentos_router.put("/{id_pagamento}/baixa", response_model=PagamentoPublico, status_code=status.HTTP_200_OK)
def baixar(
    id_pagamento: int,
    dados: BaixaPagamento,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """Marca uma cobrança pendente como paga, informando a forma de pagamento."""
    with tratar_erros():
        return pagamentos_controller.baixar_pagamento(id_pagamento, dados.forma_pagamento, usuario, db, dados.valor_recebido)


@pagamentos_router.delete("/{id_pagamento}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_pagamento: int, usuario: Usuario = Depends(exigir_admin), db: Session = Depends(get_db)):
    with tratar_erros():
        pagamentos_controller.deletar_pagamento(id_pagamento, usuario.id, usuario.nome, db)
