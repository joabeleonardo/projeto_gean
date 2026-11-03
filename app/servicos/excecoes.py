class EntradaBloqueada(ValueError):
    """Entrada barrada porque o cliente está inadimplente.

    Carrega os dados que a tela precisa para avisar o operador e pedir o código
    do administrador.
    """

    def __init__(self, nome_cliente: str, dias_atraso: int, valor_em_aberto: float, cobrancas: int):
        self.nome_cliente = nome_cliente
        self.dias_atraso = dias_atraso
        self.valor_em_aberto = valor_em_aberto
        self.cobrancas = cobrancas
        dias = "1 dia" if dias_atraso == 1 else f"{dias_atraso} dias"
        super().__init__(f"Entrada bloqueada. Cliente inadimplente há {dias}.")

    def detalhe(self) -> dict:
        return {
            "codigo": "CLIENTE_INADIMPLENTE",
            "mensagem": str(self),
            "cliente": self.nome_cliente,
            "dias_atraso": self.dias_atraso,
            "valor_em_aberto": self.valor_em_aberto,
            "cobrancas_vencidas": self.cobrancas,
        }


class CotasEsgotadas(ValueError):
    """Cliente mensalista sem cota livre: todas as cotas já têm veículo no pátio.

    A tela avisa o operador e pergunta se quer dar entrada como horista.
    """

    def __init__(self, nome_cliente: str, cotas: int, placas_em_uso: list):
        self.nome_cliente = nome_cliente
        self.cotas = cotas
        self.placas_em_uso = placas_em_uso
        placas = ", ".join(placas_em_uso) if placas_em_uso else "outro veículo"
        super().__init__(
            f"Todas as cotas de mensalista deste cliente estão em uso ({len(placas_em_uso)} de {cotas}): {placas} já está no pátio."
        )

    def detalhe(self) -> dict:
        return {
            "codigo": "COTAS_ESGOTADAS",
            "mensagem": str(self),
            "cliente": self.nome_cliente,
            "cotas": self.cotas,
            "placas_em_uso": self.placas_em_uso,
        }
