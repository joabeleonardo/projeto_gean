from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from modelos.schemas import PagamentoCreate, PagamentoPublico
from entidades.entidades import Pagamento
from dependencies.database import get_db
from controllers import pagamentos_controller

pagamentos_router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])

@pagamentos_router.post("/", response_model=PagamentoPublico, status_code=status.HTTP_201_CREATED)
def inserir(pagamento: PagamentoCreate, db: Session = Depends(get_db)):
    try:
        return pagamentos_controller.registrar_pagamento(pagamento, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@pagamentos_router.get("/", response_model=List[PagamentoPublico], status_code=status.HTTP_200_OK)
def listar(db: Session = Depends(get_db)):
    try:
        return pagamentos_controller.buscar_pagamentos(db)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@pagamentos_router.get("/{id_pagamento}", response_model=PagamentoPublico, status_code=status.HTTP_200_OK)
def buscar_por_id(id_pagamento: int, db: Session = Depends(get_db)):
    try:
        return pagamentos_controller.buscar_pagamento_por_id(id_pagamento, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@pagamentos_router.delete("/{id_pagamento}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(id_pagamento: int, id_usuario_logado: int, nome_usuario_logado: str, db: Session = Depends(get_db)):
    try:
        pagamentos_controller.deletar_pagamento(id_pagamento, id_usuario_logado, nome_usuario_logado, db)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))