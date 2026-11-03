"""Datas e horários do sistema — ponto único de verdade.

CONVENÇÃO DO PROJETO
  Todos os horários guardados no banco (colunas DATETIME do MySQL) são o
  "relógio local do estabelecimento", SEM informação de fuso (naive). É assim que
  os registros existentes foram gravados (datetime.now()), então é assim que
  continuam sendo lidos. Nada é convertido para UTC: isso deslocaria em horas os
  registros antigos.

  O fuso do estabelecimento é o do computador onde a API roda. Se o servidor
  rodar em outro fuso (ex.: nuvem em UTC), defina FUSO_HORARIO no .env,
  por exemplo FUSO_HORARIO=America/Sao_Paulo.

Este módulo não depende de banco nem de FastAPI.
"""
import logging
import os
from datetime import date, datetime, tzinfo
from typing import Optional

logger = logging.getLogger("estacionamento.datas")
_avisou_fuso = False


def _fuso() -> Optional[tzinfo]:
    """Fuso do .env (FUSO_HORARIO) ou None = fuso do sistema operacional."""
    global _avisou_fuso
    nome = os.getenv("FUSO_HORARIO")
    if not nome:
        return None
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(nome)
    except Exception:  # nome inválido ou base de fusos ausente (no Windows: pip install tzdata)
        if not _avisou_fuso:
            logger.warning("FUSO_HORARIO=%r inválido ou tzdata ausente; usando o fuso do sistema.", nome)
            _avisou_fuso = True
        return None


def agora_local() -> datetime:
    """Horário atual do estabelecimento, sem fuso — o formato das colunas DATETIME."""
    return datetime.now(_fuso()).replace(tzinfo=None)


def hoje_local() -> date:
    return agora_local().date()


def como_local_naive(valor: datetime) -> datetime:
    """Devolve o horário no padrão do projeto (relógio local, sem fuso).

    * sem fuso (naive): já está no padrão, é devolvido sem alteração;
    * com fuso (aware): é CONVERTIDO para o relógio local (mesmo instante) e só então
      o fuso é removido. Nunca se descarta o fuso sem converter.
    """
    if valor.tzinfo is None or valor.tzinfo.utcoffset(valor) is None:
        return valor
    return valor.astimezone(_fuso()).replace(tzinfo=None)
