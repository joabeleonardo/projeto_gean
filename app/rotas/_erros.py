from contextlib import contextmanager

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError

from servicos.excecoes import CotasEsgotadas, EntradaBloqueada


def _mensagem(e: Exception) -> str:
    return str(e.args[0]) if e.args else str(e)


@contextmanager
def tratar_erros():
    """Converte as exceções dos controllers em respostas HTTP.

    KeyError -> 404 | ValueError -> 400 | EntradaBloqueada -> 423 | RuntimeError -> 500
    IntegrityError (vínculos no banco) -> 409
    """
    try:
        yield
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_mensagem(e))
    except EntradaBloqueada as e:  # precisa vir antes de ValueError (é uma subclasse)
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=e.detalhe())
    except CotasEsgotadas as e:  # idem: subclasse de ValueError
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detalhe())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_mensagem(e))
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operação não permitida: o registro possui vínculos (histórico) ou dados duplicados.",
        )
    except (RuntimeError, OperationalError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_mensagem(e) if isinstance(e, RuntimeError) else "Falha de comunicação com o banco de dados.",
        )


def preencher_auditoria(dados, usuario) -> None:
    """Sobrescreve os campos de auditoria com o usuário realmente logado."""
    dados.id_usuario_logado = usuario.id
    dados.nome_usuario_logado = usuario.nome
