from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class PerfilEnum(str, Enum):
    Administrador = 'Administrador'
    Operador = 'Operador'

class Endereco(SQLModel, table=True):
    __tablename__ = "tb_enderecos"
    id: Optional[int] = Field(default=None, primary_key=True)
    logradouro: str = Field(max_length=150)
    numero: str = Field(max_length=10)
    complemento: Optional[str] = Field(default=None, max_length=50)
    bairro: str = Field(max_length=50)
    cidade: str = Field(max_length=50)
    estado: str = Field(max_length=2)
    cep: str = Field(max_length=9)
    clientes: List["Cliente"] = Relationship(back_populates="endereco")

class Cliente(SQLModel, table=True):
    __tablename__ = "tb_clientes"
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=100)
    cpf: str = Field(max_length=14, unique=True)
    telefone: Optional[str] = Field(default=None, max_length=20)
    id_endereco: Optional[int] = Field(default=None, foreign_key="tb_enderecos.id")
   
    # Relacionamentos
    endereco: Optional["Endereco"] = Relationship(back_populates="clientes")
    
    # ⚠️ ADICIONADO AQUI: Resolve o erro de propriedade ausente no Mapper do Cliente
    veiculos: List["Veiculo"] = Relationship(back_populates="cliente")


#================================================
#VEÍCULOS
#================================================
class Veiculo(SQLModel, table=True):
    __tablename__ = "tb_veiculos"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    placa: str = Field(max_length=10, unique=True)
    modelo: str = Field(max_length=50)
    cor: Optional[str] = Field(default=None, max_length=30)
    id_cliente: int = Field(foreign_key="tb_clientes.id")

    # Relacionamento reverso com clientes
    cliente: Optional["Cliente"] = Relationship(back_populates="veiculos")

#================================================
#VAGAS
#================================================
class TipoVagaEnum(str, Enum):
    Mensalista = 'Mensalista'
    Horista = 'Horista'

class StatusVagaEnum(str, Enum):
    Livre = 'Livre'
    Ocupada = 'Ocupada'

class Vaga(SQLModel, table=True):
    __tablename__ = "tb_vagas"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo_vaga: str = Field(max_length=10, unique=True)
    tipo: TipoVagaEnum
    status: StatusVagaEnum = Field(default=StatusVagaEnum.Livre)

    # Relacionamento reverso com movimentações (se aplicável)
    movimentacoes: List["Movimentacao"] = Relationship(back_populates="vaga")


#================================================
#PREÇO
#================================================
class TipoCobrancaEnum(str, Enum):
    Horista = "Horista"
    Mensalista = "Mensalista"

class Preco(SQLModel, table=True):
    __tablename__ = "tb_precos"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo_cobranca: TipoCobrancaEnum = Field(unique=True)
    valor: float = Field(default=0.0)

#================================================
#USUARIOS
#================================================
class Usuario(SQLModel, table=True):
    __tablename__ = "tb_usuarios"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=100)
    login: str = Field(max_length=50, unique=True)
    senha: str = Field(max_length=255)
    perfil: PerfilEnum = Field(default=PerfilEnum.Operador)

#================================================
#USUARIOS
#================================================
class Movimentacao(SQLModel, table=True):
    __tablename__ = "tb_movimentacoes"

    id: Optional[int] = Field(default=None, primary_key=True)

    id_veiculo: int = Field(foreign_key="tb_veiculos.id")
    id_vaga: int = Field(foreign_key="tb_vagas.id")

    data_entrada: datetime = Field(default_factory=datetime.now)
    id_usuario_entrada: int = Field(foreign_key="tb_usuarios.id")

    data_saida: Optional[datetime] = Field(default=None)
    id_usuario_saida: Optional[int] = Field(
        default=None,
        foreign_key="tb_usuarios.id"
    )

    vaga: Optional["Vaga"] = Relationship(back_populates="movimentacoes")    

#================================================
#PAGAMENTOS
#================================================
class TipoPagamentoEnum(str, Enum):
    Mensal = "Mensal"
    Hora = "Hora"


class StatusPagamentoEnum(str, Enum):
    Pendente = "Pendente"
    Pago = "Pago"


class Pagamento(SQLModel, table=True):
    __tablename__ = "tb_pagamentos"

    id: Optional[int] = Field(default=None, primary_key=True)

    id_movimentacao: Optional[int] = Field(
        default=None,
        foreign_key="tb_movimentacoes.id"
    )

    id_cliente: Optional[int] = Field(
        default=None,
        foreign_key="tb_clientes.id"
    )

    tipo_cobranca: TipoPagamentoEnum
    valor_total: float = Field(ge=0.0)
    data_vencimento: Optional[date] = Field(default=None)
    data_pagamento: Optional[datetime] = Field(default=None)

    status: StatusPagamentoEnum = Field(
        default=StatusPagamentoEnum.Pendente
    )

    id_usuario_recebimento: Optional[int] = Field(
        default=None,
        foreign_key="tb_usuarios.id"
    )
