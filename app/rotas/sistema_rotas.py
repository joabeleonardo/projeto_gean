from fastapi import APIRouter

from servicos.datas import agora_local

sistema_router = APIRouter(prefix="/servidor", tags=["Servidor"])


@sistema_router.get("/hora")
def hora_do_servidor():
    """Data e hora do SERVIDOR. As telas usam esta hora (e não o relógio do computador do usuário)
    para datas padrão e para o que depende do dia de hoje."""
    agora = agora_local()
    return {"agora": agora.isoformat(timespec="seconds"), "hoje": agora.date().isoformat()}
