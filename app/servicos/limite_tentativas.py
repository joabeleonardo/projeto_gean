"""Limite simples de tentativas erradas (em memória), para o código de liberação.

Protege o PIN do administrador contra tentativa e erro: depois de N erros seguidos
o operador fica bloqueado por alguns minutos.
"""
import time
from typing import Callable, Dict, List


class LimiteTentativas:
    def __init__(self, maximo: int = 5, janela_segundos: int = 300, relogio: Callable[[], float] = time.monotonic):
        self.maximo = maximo
        self.janela = janela_segundos
        self._relogio = relogio
        self._falhas: Dict[object, List[float]] = {}

    def _recentes(self, chave) -> List[float]:
        agora = self._relogio()
        recentes = [t for t in self._falhas.get(chave, []) if agora - t < self.janela]
        self._falhas[chave] = recentes
        return recentes

    def segundos_bloqueado(self, chave) -> int:
        """0 se liberado; senão, quantos segundos faltam."""
        recentes = self._recentes(chave)
        if len(recentes) < self.maximo:
            return 0
        return max(1, int(self.janela - (self._relogio() - recentes[0])))

    def registrar_falha(self, chave) -> None:
        self._recentes(chave).append(self._relogio())

    def limpar(self, chave) -> None:
        self._falhas.pop(chave, None)


# instância usada pela API
limite_liberacao = LimiteTentativas(maximo=5, janela_segundos=300)
