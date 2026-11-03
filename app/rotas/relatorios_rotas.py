from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from controllers import relatorios_controller
from dependencies.auth import exigir_admin
from dependencies.database import get_db
from modelos.schemas import StatusPagamentoEnum, TipoPagamentoEnum
from rotas._erros import tratar_erros

# Relatórios são restritos a administradores (contêm valores financeiros)
relatorios_router = APIRouter(prefix="/relatorios", tags=["Relatórios"], dependencies=[Depends(exigir_admin)])


@relatorios_router.get("/movimentacoes", status_code=status.HTTP_200_OK)
def movimentacoes(
    inicio: Optional[date] = None, fim: Optional[date] = None, placa: Optional[str] = None,
    id_veiculo: Optional[int] = None, db: Session = Depends(get_db),
):
    """Entradas e saídas no período, com quem registrou cada uma. Filtra por placa ou por um veículo específico."""
    with tratar_erros():
        return relatorios_controller.movimentacoes(db, inicio, fim, placa, id_veiculo)


@relatorios_router.get("/por-veiculo", status_code=status.HTTP_200_OK)
def por_veiculo(inicio: Optional[date] = None, fim: Optional[date] = None, db: Session = Depends(get_db)):
    """Resumo por veículo: visitas, tempo total e valor pago."""
    with tratar_erros():
        return relatorios_controller.por_veiculo(db, inicio, fim)


@relatorios_router.get("/agrupado", status_code=status.HTTP_200_OK)
def agrupado(
    periodo: Literal["dia", "mes"] = "dia",
    inicio: Optional[date] = None, fim: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Entradas, saídas e receita por dia ou por mês."""
    with tratar_erros():
        return relatorios_controller.agrupado(db, periodo, inicio, fim)


@relatorios_router.get("/pagamentos", status_code=status.HTTP_200_OK)
def pagamentos(
    inicio: Optional[date] = None, fim: Optional[date] = None,
    status_pagamento: Optional[StatusPagamentoEnum] = None,
    tipo: Optional[TipoPagamentoEnum] = None,
    cliente: Optional[str] = None, forma: Optional[str] = None, id_usuario: Optional[int] = None,
    db: Session = Depends(get_db),
):
    with tratar_erros():
        return relatorios_controller.pagamentos(
            db, inicio, fim,
            status_pagamento.value if status_pagamento else None,
            tipo.value if tipo else None, cliente, forma, id_usuario,
        )


@relatorios_router.get("/recebimentos-por-cliente", status_code=status.HTTP_200_OK)
def recebimentos_por_cliente(inicio: Optional[date] = None, fim: Optional[date] = None, db: Session = Depends(get_db)):
    """Quanto cada cliente pagou no período."""
    with tratar_erros():
        return relatorios_controller.recebimentos_por_cliente(db, inicio, fim)


@relatorios_router.get("/caixa", status_code=status.HTTP_200_OK)
def caixa(inicio: Optional[date] = None, fim: Optional[date] = None, db: Session = Depends(get_db)):
    """Fechamento de caixa: entradas por usuário e forma de pagamento, com o dinheiro em espécie e o troco."""
    with tratar_erros():
        return relatorios_controller.caixa(db, inicio, fim)


@relatorios_router.get("/clientes", status_code=status.HTTP_200_OK)
def clientes(tipo: str = "", pais: str = "", nome: str = "", documento: str = "", db: Session = Depends(get_db)):
    """Clientes cadastrados (com documento, contatos, plano, veículos e inadimplência)."""
    with tratar_erros():
        return relatorios_controller.clientes_cadastrados(db, tipo, pais, nome, documento)


@relatorios_router.get("/veiculos", status_code=status.HTTP_200_OK)
def veiculos(tipo: str = "", q: str = "", db: Session = Depends(get_db)):
    """Veículos cadastrados, com proprietário."""
    with tratar_erros():
        return relatorios_controller.veiculos_cadastrados(db, tipo, q)


@relatorios_router.get("/inadimplentes", status_code=status.HTTP_200_OK)
def inadimplentes(db: Session = Depends(get_db)):
    """Clientes inadimplentes, com dias de atraso e valor em aberto."""
    with tratar_erros():
        return relatorios_controller.inadimplentes(db)
