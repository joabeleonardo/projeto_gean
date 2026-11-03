from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
from datetime import date
from sqlalchemy import DateTime, UniqueConstraint

from servicos.datas import agora_local


class PerfilEnum(str, Enum):
    Administrador = 'Administrador'
    Operador = 'Operador'


class TipoDocumentoEnum(str, Enum):
    CPF = 'CPF'
    CNPJ = 'CNPJ'
    Passaporte = 'Passaporte'   # documento de cliente estrangeiro


class PlanoEnum(str, Enum):
    Rotativo = 'Rotativo'
    Premium = 'Premium'


class CategoriaEnum(str, Enum):
    """Tipo de veículo atendido (vaga de carro ou de moto)."""
    Carro = 'Carro'
    Moto = 'Moto'

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
    # coluna "cpf" guarda o documento do cliente: CPF, CNPJ ou passaporte (ver tipo_documento).
    # O nome da coluna foi mantido para não quebrar as triggers de auditoria de tb_clientes.
    cpf: str = Field(max_length=18, unique=True)
    tipo_documento: TipoDocumentoEnum = Field(default=TipoDocumentoEnum.CPF)
    pais: str = Field(default="Brasil", max_length=60)
    telefone: Optional[str] = Field(default=None, max_length=20)
    telefone_whatsapp: bool = Field(default=False)
    telefone2: Optional[str] = Field(default=None, max_length=20)
    telefone2_whatsapp: bool = Field(default=False)
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
    marca: Optional[str] = Field(default=None, max_length=50)
    modelo: str = Field(max_length=50)
    cor: Optional[str] = Field(default=None, max_length=30)
    tipo_veiculo: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    id_cliente: int = Field(foreign_key="tb_clientes.id")

    # Relacionamento reverso com clientes
    cliente: Optional["Cliente"] = Relationship(back_populates="veiculos")

#================================================
#VAGAS
#================================================
class TipoVagaEnum(str, Enum):
    Mensalista = 'Mensalista'   # vaga rotativa de mensalista (qualquer mensalista usa a que estiver livre)
    Horista = 'Horista'
    Premium = 'Premium'         # vaga exclusiva de um cliente mensalista (plano premium)

class StatusVagaEnum(str, Enum):
    Livre = 'Livre'
    Ocupada = 'Ocupada'

class Vaga(SQLModel, table=True):
    __tablename__ = "tb_vagas"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo_vaga: str = Field(max_length=10, unique=True)
    tipo: TipoVagaEnum
    categoria: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    status: StatusVagaEnum = Field(default=StatusVagaEnum.Livre)
    # False = vaga inativa (ex.: em reforma): não aparece como disponível e não recebe entradas
    ativa: bool = Field(default=True)

    # Relacionamento reverso com movimentações (se aplicável)
    movimentacoes: List["Movimentacao"] = Relationship(back_populates="vaga")


#================================================
#PREÇO
#================================================
class TipoCobrancaEnum(str, Enum):
    Horista = "Horista"
    Mensalista = "Mensalista"
    Premium = "Premium"

class Preco(SQLModel, table=True):
    __tablename__ = "tb_precos"
    # Um preço para cada combinação (categoria, tipo de cobrança):
    # Carro/Horista, Carro/Mensalista, Moto/Horista, Moto/Mensalista
    __table_args__ = (UniqueConstraint("categoria", "tipo_cobranca", name="uq_preco_categoria_tipo"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    categoria: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    tipo_cobranca: TipoCobrancaEnum
    valor: float = Field(default=0.0)
    # Cobrança por hora: valor mínimo e quantos minutos ele cobre (só usados no tipo Horista)
    valor_minimo: float = Field(default=0.0)
    tempo_minimo_minutos: int = Field(default=0)

#================================================
#USUARIOS
#================================================
class Usuario(SQLModel, table=True):
    __tablename__ = "tb_usuarios"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=100)
    login: str = Field(max_length=50, unique=True)
    senha: str = Field(max_length=255)
    # str (e não Enum) para aceitar qualquer valor já gravado na coluna (ENUM ou VARCHAR)
    perfil: str = Field(default="Operador", max_length=30)
    # PIN do administrador para liberar entrada de cliente inadimplente (guardado com hash)
    codigo_liberacao: Optional[str] = Field(default=None, max_length=255)

#================================================
#USUARIOS
#================================================
class Movimentacao(SQLModel, table=True):
    __tablename__ = "tb_movimentacao"

    id: Optional[int] = Field(default=None, primary_key=True)

    id_veiculo: int = Field(foreign_key="tb_veiculos.id")
    id_vaga: int = Field(foreign_key="tb_vagas.id")

    # DATETIME sem fuso = relógio local do estabelecimento (ver servicos/datas.py).
    # sa_type explícito: sem ele, SQLModel >= 0.0.45 usa um tipo UTC que exige
    # datetimes com fuso na escrita e devolve datetimes com fuso na leitura.
    data_entrada: datetime = Field(default_factory=agora_local, sa_type=DateTime(timezone=False))
    id_usuario_entrada: int = Field(foreign_key="tb_usuarios.id")

    data_saida: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=False))
    id_usuario_saida: Optional[int] = Field(
        default=None,
        foreign_key="tb_usuarios.id"
    )
    # Entrada liberada com o código de um administrador (cliente inadimplente)
    id_usuario_liberacao: Optional[int] = Field(default=None)
    obs_liberacao: Optional[str] = Field(default=None, max_length=255)

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
        foreign_key="tb_movimentacao.id"
    )

    id_cliente: Optional[int] = Field(
        default=None,
        foreign_key="tb_clientes.id"
    )

    tipo_cobranca: TipoPagamentoEnum
    valor_total: float = Field(ge=0.0)
    data_vencimento: Optional[date] = Field(default=None)
    data_pagamento: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=False))

    status: StatusPagamentoEnum = Field(
        default=StatusPagamentoEnum.Pendente
    )

    # Dinheiro, Pix, Cartão de débito, Cartão de crédito, Transferência
    forma_pagamento: Optional[str] = Field(default=None, max_length=20)
    # Pagamento em dinheiro: quanto o cliente entregou e quanto voltou de troco
    valor_recebido: Optional[float] = Field(default=None)
    troco: Optional[float] = Field(default=None)

    id_usuario_recebimento: Optional[int] = Field(
        default=None,
        foreign_key="tb_usuarios.id"
    )



class Mensalidade(SQLModel, table=True):
    """Plano de mensalista de um cliente. Cada cota permite estacionar um veículo ao mesmo tempo
    em vaga de mensalista. O plano vale a partir de data_inicio (data da adesão)."""
    __tablename__ = "tb_mensalidades"

    id: Optional[int] = Field(default=None, primary_key=True)
    id_cliente: int = Field(foreign_key="tb_clientes.id")
    categoria: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    cotas: int = Field(default=1)
    tipo_plano: PlanoEnum = Field(default=PlanoEnum.Rotativo)
    id_vaga: Optional[int] = Field(default=None)   # plano premium: a vaga exclusiva do cliente
    data_inicio: date
    data_fim: Optional[date] = Field(default=None)
    ativa: bool = Field(default=True)



class LogSistema(SQLModel, table=True):
    """Registro legível do que acontece no sistema: quem fez, o quê, quando (relatório de logs)."""
    __tablename__ = "tb_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    data_hora: datetime = Field(default_factory=agora_local, sa_type=DateTime(timezone=False))
    id_usuario: Optional[int] = Field(default=None)
    usuario: str = Field(default="Sistema", max_length=100)
    acao: str = Field(max_length=20)               # CRIAR, ALTERAR, EXCLUIR, ENTRADA, SAIDA, PAGAMENTO, LOGIN...
    entidade: str = Field(max_length=40)
    id_registro: Optional[int] = Field(default=None)
    descricao: str
    campo: Optional[str] = Field(default=None, max_length=60)
    valor_antigo: Optional[str] = Field(default=None)
    valor_novo: Optional[str] = Field(default=None)
