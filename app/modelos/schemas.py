from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime, date


class AuditoriaBase(BaseModel):
    # Todo endpoint de INSERT/UPDATE/DELETE exigirá esses campos no Payload
    id_usuario_logado: int = Field(description="ID do operador logado no sistema")
    nome_usuario_logado: str = Field(description="Nome do operador logado no sistema")

class ClienteBase(BaseModel):
    nome: str = Field(min_length=3, max_length=100)
    cpf: str = Field(min_length=11, max_length=14)
    telefone: Optional[str] = Field(default=None, max_length=20)
    id_endereco: Optional[int] = Field(default=None)

class ClienteCreate(ClienteBase, AuditoriaBase):
    pass

class ClientePublico(ClienteBase):
    id: int


#================================================
#VEÍCULOS
#================================================
# Herança de auditoria que já criamos anteriormente

class VeiculoBase(BaseModel):
    placa: str = Field(min_length=7, max_length=10)
    modelo: str = Field(min_length=2, max_length=50)
    cor: Optional[str] = Field(default=None, max_length=30)
    id_cliente: int = Field(description="ID do cliente proprietário do veículo")

class VeiculoCreate(VeiculoBase, AuditoriaBase):
    pass

class VeiculoPublico(VeiculoBase):
    id: int

#================================================
#VAGAS
#================================================
class TipoVagaEnum(str, Enum):
    Mensalista = 'Mensalista'
    Horista = 'Horista'

class StatusVagaEnum(str, Enum):
    Livre = 'Livre'
    Ocupada = 'Ocupada'

# Auditoria Base já utilizada nos outros módulos

class VagaBase(BaseModel):
    codigo_vaga: str = Field(min_length=1, max_length=10)
    tipo: TipoVagaEnum
    status: StatusVagaEnum = Field(default=StatusVagaEnum.Livre)

class VagaCreate(VagaBase, AuditoriaBase):
    pass

class VagaPublico(VagaBase):
    id: int


#================================================
#PREÇOS
#================================================
class TipoCobrancaEnum(str, Enum):
    Horista = "Horista"
    Mensalista = "Mensalista"

class PrecoBase(BaseModel):
    tipo_cobranca: TipoCobrancaEnum
    valor: float = Field(ge=0.0, description="Valor cobrado (por hora ou mensal)")

class PrecoCreate(PrecoBase, AuditoriaBase):
    pass

class PrecoPublico(PrecoBase):
    id: int

#================================================
#USUÁRIOS
#================================================
class PerfilEnum(str, Enum):
    Administrador = 'Administrador'
    Operador = 'Operador'

class UsuarioBase(BaseModel):
    nome: str = Field(min_length=3, max_length=100)
    login: str = Field(min_length=3, max_length=50)
    perfil: PerfilEnum = Field(default=PerfilEnum.Operador)

class UsuarioCreate(UsuarioBase, AuditoriaBase):
    senha: str = Field(min_length=6, max_length=255)

class UsuarioPublico(UsuarioBase):
    id: int
#================================================
#MOVIMENTAÇÕES
#================================================

class MovimentacaoEntradaCreate(AuditoriaBase):
    id_veiculo: int = Field(description="ID do veículo entrando no estacionamento")
    id_vaga: int = Field(description="ID da vaga sendo ocupada")
    id_usuario_entrada: int = Field(description="ID do operador que registrou a entrada")

class MovimentacaoSaidaUpdate(AuditoriaBase):
    id_usuario_saida: int = Field(description="ID do operador que registrou a saída")

class MovimentacaoPublico(BaseModel):
    id: int
    id_veiculo: int
    id_vaga: int
    data_entrada: datetime
    id_usuario_entrada: int
    data_saida: Optional[datetime] = None
    id_usuario_saida: Optional[int] = None
#================================================
#PAGAMENTOS
#================================================
class TipoPagamentoEnum(str, Enum):
    Mensal = 'Mensal'
    Hora = 'Hora'

class StatusPagamentoEnum(str, Enum):
    Pendente = 'Pendente'
    Pago = 'Pago'

class PagamentoCreate(AuditoriaBase):
    id_movimentacao: Optional[int] = Field(default=None, description="ID da movimentação (se for cobrança por hora)")
    id_cliente: Optional[int] = Field(default=None, description="ID do cliente (se for mensalidade)")
    tipo_cobranca: TipoPagamentoEnum
    valor_total: float = Field(ge=0.0, description="Valor total da cobrança")
    data_vencimento: Optional[date] = Field(default=None, description="Data de vencimento")
    id_usuario_recebimento: int = Field(description="ID do operador que registrou o pagamento")

class PagamentoPublico(BaseModel):
    id: int
    id_movimentacao: Optional[int] = None
    id_cliente: Optional[int] = None
    tipo_cobranca: TipoPagamentoEnum
    valor_total: float
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[datetime] = None
    status: StatusPagamentoEnum
    id_usuario_recebimento: Optional[int] = None
#================================================
#VEÍCULOS
#================================================
