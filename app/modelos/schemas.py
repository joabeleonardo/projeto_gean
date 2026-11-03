from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime, date

from modelos import validadores as val


class CategoriaEnum(str, Enum):
    Carro = 'Carro'
    Moto = 'Moto'


class FormaPagamentoEnum(str, Enum):
    Dinheiro = 'Dinheiro'
    Pix = 'Pix'
    Debito = 'Cartão de débito'
    Credito = 'Cartão de crédito'
    Transferencia = 'Transferência'


class TipoDocumentoEnum(str, Enum):
    CPF = 'CPF'
    CNPJ = 'CNPJ'
    Passaporte = 'Passaporte'


class PlanoEnum(str, Enum):
    Rotativo = 'Rotativo'
    Premium = 'Premium'


class AuditoriaBase(BaseModel):
    # Mantidos por compatibilidade: o backend sempre sobrescreve estes campos
    # com o usuário autenticado (token), então o cliente não precisa enviá-los.
    id_usuario_logado: Optional[int] = Field(default=None, description="Preenchido pelo servidor a partir do login")
    nome_usuario_logado: Optional[str] = Field(default=None, description="Preenchido pelo servidor a partir do login")


# ================================================
# ENDEREÇOS
# ================================================
class EnderecoEntrada(BaseModel):
    logradouro: str = Field(min_length=2, max_length=150)
    numero: str = Field(min_length=1, max_length=10)
    complemento: Optional[str] = Field(default=None, max_length=50)
    bairro: str = Field(min_length=2, max_length=50)
    cidade: str = Field(min_length=2, max_length=50)
    estado: str = Field(min_length=2, max_length=2)
    cep: str = Field(min_length=8, max_length=9)

    @field_validator("cep")
    @classmethod
    def _cep(cls, v: str) -> str:
        return val.formatar_cep(v)

    @field_validator("estado")
    @classmethod
    def _estado(cls, v: str) -> str:
        return val.formatar_estado(v)


class EnderecoCreate(EnderecoEntrada, AuditoriaBase):
    pass


class EnderecoPublico(BaseModel):
    id: int
    logradouro: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str
    cep: str


# ================================================
# CLIENTES
# ================================================
class ClienteBase(BaseModel):
    """Leitura (tolerante com dados antigos): nenhuma validação rígida aqui."""
    nome: str = Field(min_length=3, max_length=100)
    cpf: str = Field(min_length=5, max_length=22, description="Documento: CPF, CNPJ ou passaporte")
    tipo_documento: str = "CPF"
    pais: str = "Brasil"
    telefone: Optional[str] = Field(default=None, max_length=20)
    telefone_whatsapp: bool = False
    telefone2: Optional[str] = Field(default=None, max_length=20)
    telefone2_whatsapp: bool = False
    id_endereco: Optional[int] = Field(default=None)


class _Telefones(BaseModel):
    telefone: Optional[str] = Field(default=None, max_length=20)
    telefone_whatsapp: bool = False
    telefone2: Optional[str] = Field(default=None, max_length=20)
    telefone2_whatsapp: bool = False
    pais: str = Field(default="Brasil", min_length=2, max_length=60)

    @field_validator("telefone", "telefone2")
    @classmethod
    def _telefone(cls, v: Optional[str]) -> Optional[str]:
        return val.formatar_telefone(v)

    @field_validator("pais")
    @classmethod
    def _pais(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _coerencia_telefones(self):
        if self.telefone2 and not self.telefone:
            raise ValueError("Informe o telefone principal antes do segundo telefone.")
        if not self.telefone:
            self.telefone_whatsapp = False
        if not self.telefone2:
            self.telefone2_whatsapp = False
        return self


class ClienteEntrada(_Telefones):
    """Cadastro: valida e padroniza o documento (CPF, CNPJ ou passaporte), telefones e país."""
    nome: str = Field(min_length=3, max_length=100)
    tipo_documento: TipoDocumentoEnum = Field(default=TipoDocumentoEnum.CPF)
    cpf: str = Field(min_length=5, max_length=22, description="Documento: CPF, CNPJ ou passaporte")

    @model_validator(mode="after")
    def _documento(self):
        self.cpf = val.formatar_documento(self.tipo_documento.value, self.cpf)
        return self


class ClienteEdicao(_Telefones):
    """Edição: o documento (CPF/CNPJ/passaporte) NÃO entra aqui — só pode ser alterado direto no banco."""
    nome: str = Field(min_length=3, max_length=100)


class ClienteCreate(ClienteEntrada, AuditoriaBase):
    id_endereco: Optional[int] = Field(default=None)


class ClientePublico(ClienteBase):
    id: int


# ================================================
# VEÍCULOS
# ================================================
class VeiculoBase(BaseModel):
    placa: str = Field(min_length=7, max_length=10)
    marca: Optional[str] = Field(default=None, max_length=50)
    modelo: str = Field(min_length=2, max_length=50)
    cor: Optional[str] = Field(default=None, max_length=30)
    tipo_veiculo: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    id_cliente: int = Field(description="ID do cliente proprietário do veículo")


class VeiculoEntrada(BaseModel):
    """Veículo sem o dono (usado no cadastro completo)."""
    placa: str = Field(min_length=7, max_length=10)
    marca: str = Field(min_length=2, max_length=50)
    modelo: str = Field(min_length=2, max_length=50)
    cor: Optional[str] = Field(default=None, max_length=30)
    tipo_veiculo: CategoriaEnum = Field(default=CategoriaEnum.Carro)

    @field_validator("placa")
    @classmethod
    def _placa(cls, v: str) -> str:
        return val.formatar_placa(v)


class VeiculoCreate(VeiculoEntrada, AuditoriaBase):
    id_cliente: int = Field(description="ID do cliente proprietário do veículo")


class VeiculoPublico(VeiculoBase):
    id: int


class VeiculoDetalhe(VeiculoPublico):
    cliente_nome: Optional[str] = None
    cliente_cpf: Optional[str] = None




# ================================================
# VAGAS
# ================================================
class TipoVagaEnum(str, Enum):
    Mensalista = 'Mensalista'
    Horista = 'Horista'
    Premium = 'Premium'


class StatusVagaEnum(str, Enum):
    Livre = 'Livre'
    Ocupada = 'Ocupada'


class VagaBase(BaseModel):
    codigo_vaga: str = Field(min_length=1, max_length=10)
    tipo: TipoVagaEnum
    categoria: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    status: StatusVagaEnum = Field(default=StatusVagaEnum.Livre)


class VagaCreate(VagaBase, AuditoriaBase):
    pass


class VagaPublico(VagaBase):
    id: int
    ativa: bool = True


class SituacaoVaga(BaseModel):
    ativa: bool


# ================================================
# PREÇOS
# ================================================
class TipoCobrancaEnum(str, Enum):
    Horista = "Horista"
    Mensalista = "Mensalista"
    Premium = "Premium"


class PrecoBase(BaseModel):
    categoria: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    tipo_cobranca: TipoCobrancaEnum
    valor: float = Field(ge=0.0, description="Valor cobrado (por hora ou mensal)")
    valor_minimo: float = Field(default=0.0, ge=0.0, description="Cobrança mínima por hora (0 = sem mínimo)")
    tempo_minimo_minutos: int = Field(default=0, ge=0, le=1440, description="Até quantos minutos vale o valor mínimo")


class PrecoCreate(PrecoBase, AuditoriaBase):
    pass


class PrecoPublico(PrecoBase):
    id: int


# ================================================
# USUÁRIOS
# ================================================
class PerfilEnum(str, Enum):
    Administrador = 'Administrador'
    Operador = 'Operador'


class UsuarioBase(BaseModel):
    nome: str = Field(min_length=3, max_length=100)
    login: str = Field(min_length=3, max_length=50)
    perfil: PerfilEnum = Field(default=PerfilEnum.Operador)


class UsuarioCreate(UsuarioBase, AuditoriaBase):
    senha: str = Field(min_length=6, max_length=100)
    codigo_liberacao: Optional[str] = Field(default=None, min_length=4, max_length=20, description="PIN para liberar clientes inadimplentes (só administradores)")


class UsuarioUpdate(UsuarioBase, AuditoriaBase):
    # Na edição a senha é opcional: em branco = mantém a atual
    senha: Optional[str] = Field(default=None, min_length=6, max_length=100)
    codigo_liberacao: Optional[str] = Field(default=None, min_length=4, max_length=20)


class UsuarioPublico(BaseModel):
    id: int
    nome: str
    login: str
    perfil: str  # texto livre: aceita qualquer valor já gravado no banco


# ================================================
# LOGIN
# ================================================
class LoginEntrada(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=1, max_length=100)


class LoginResposta(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioPublico


class AlterarSenha(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=100)
    nova_senha: str = Field(min_length=6, max_length=100)


# ================================================
# MOVIMENTAÇÕES
# ================================================
class MovimentacaoEntradaCreate(AuditoriaBase):
    id_veiculo: int = Field(description="ID do veículo entrando no estacionamento")
    id_vaga: int = Field(description="ID da vaga sendo ocupada")
    id_usuario_entrada: Optional[int] = Field(default=None, description="Preenchido pelo servidor")
    como_horista: bool = Field(default=False, description="Mensalista sem cota livre que aceitou entrar como horista")
    codigo_liberacao: Optional[str] = Field(default=None, max_length=20, description="Código do administrador para liberar cliente inadimplente")


class MovimentacaoSaidaUpdate(AuditoriaBase):
    id_usuario_saida: Optional[int] = Field(default=None, description="Preenchido pelo servidor")
    forma_pagamento: Optional[FormaPagamentoEnum] = Field(default=None, description="Obrigatória quando há valor a receber")
    valor_recebido: Optional[float] = Field(default=None, ge=0.0, description="Pagamento em dinheiro: quanto o cliente entregou")


class MovimentacaoPublico(BaseModel):
    id: int
    id_veiculo: int
    id_vaga: int
    data_entrada: datetime
    id_usuario_entrada: int
    data_saida: Optional[datetime] = None
    id_usuario_saida: Optional[int] = None
    # Preenchidos apenas na resposta de saída
    permanencia_minutos: Optional[int] = None
    valor_total: Optional[float] = None
    troco: Optional[float] = None


class PreviaSaida(BaseModel):
    id: int
    placa: str
    codigo_vaga: str
    tipo_vaga: str
    categoria: str = "Carro"
    data_entrada: datetime
    permanencia_minutos: int
    valor_total: Optional[float] = None
    valor_hora: Optional[float] = None
    valor_minimo: float = 0.0
    tempo_minimo_minutos: int = 0


class MovimentacaoPatio(BaseModel):
    id: int
    placa: str
    marca: Optional[str] = None
    modelo: str
    cliente_nome: Optional[str] = None
    codigo_vaga: str
    tipo_vaga: str
    categoria: str = "Carro"
    data_entrada: datetime
    permanencia_minutos: int


# ================================================
# PAGAMENTOS
# ================================================
class TipoPagamentoEnum(str, Enum):
    Mensal = 'Mensal'
    Hora = 'Hora'


class StatusPagamentoEnum(str, Enum):
    Pendente = 'Pendente'
    Pago = 'Pago'


class PagamentoCreate(AuditoriaBase):
    id_movimentacao: Optional[int] = Field(default=None, description="ID da movimentação (cobrança por hora)")
    id_cliente: Optional[int] = Field(default=None, description="ID do cliente (mensalidade)")
    tipo_cobranca: TipoPagamentoEnum
    # Só para mensalidade: qual preço mensal usar (carro ou moto)
    categoria: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    forma_pagamento: Optional[FormaPagamentoEnum] = Field(default=None, description="Obrigatória quando o status é Pago")
    valor_recebido: Optional[float] = Field(default=None, ge=0.0, description="Pagamento em dinheiro: quanto o cliente entregou")
    # O valor é sempre calculado pelo servidor; o campo é aceito mas ignorado.
    valor_total: Optional[float] = Field(default=None, ge=0.0)
    data_vencimento: Optional[date] = Field(default=None, description="Data de vencimento")
    status: Optional[StatusPagamentoEnum] = Field(default=StatusPagamentoEnum.Pago)
    id_usuario_recebimento: Optional[int] = Field(default=None, description="Preenchido pelo servidor")


class PagamentoPublico(BaseModel):
    id: int
    id_movimentacao: Optional[int] = None
    id_cliente: Optional[int] = None
    tipo_cobranca: TipoPagamentoEnum
    valor_total: float
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[datetime] = None
    status: StatusPagamentoEnum
    forma_pagamento: Optional[str] = None
    valor_recebido: Optional[float] = None
    troco: Optional[float] = None
    id_usuario_recebimento: Optional[int] = None


class BaixaPagamento(BaseModel):
    forma_pagamento: FormaPagamentoEnum
    valor_recebido: Optional[float] = Field(default=None, ge=0.0, description="Pagamento em dinheiro: quanto o cliente entregou")


class PagamentoDetalhe(PagamentoPublico):
    cliente_nome: Optional[str] = None
    placa: Optional[str] = None
    recebido_por: Optional[str] = None


# ================================================
# INADIMPLÊNCIA
# ================================================
class ClienteInadimplente(BaseModel):
    id: int
    nome: str
    cpf: str
    telefone: Optional[str] = None
    dias_atraso: int
    valor_em_aberto: float
    cobrancas_vencidas: int


# ================================================
# MENSALIDADES (plano de mensalista com cotas)
# ================================================
class MensalidadeEntrada(BaseModel):
    """Adesão ao plano. A mensalidade vale a partir de data_inicio (padrão: hoje)."""
    categoria: CategoriaEnum = Field(default=CategoriaEnum.Carro)
    cotas: int = Field(default=1, ge=1, le=20, description="Quantos veículos podem estar no pátio ao mesmo tempo")
    data_inicio: Optional[date] = Field(default=None, description="Data da adesão; vazio = hoje")
    status_primeira_cobranca: StatusPagamentoEnum = Field(default=StatusPagamentoEnum.Pendente)
    forma_pagamento: Optional[FormaPagamentoEnum] = Field(default=None, description="Obrigatória se a primeira cobrança já for paga")
    valor_recebido: Optional[float] = Field(default=None, ge=0.0, description="Se pagou em dinheiro: quanto o cliente entregou")
    tipo_plano: PlanoEnum = Field(default=PlanoEnum.Rotativo, description="Rotativo (cotas) ou Premium (vaga exclusiva)")
    id_vaga: Optional[int] = Field(default=None, description="Plano premium: a vaga exclusiva escolhida")

    @model_validator(mode="after")
    def _premium(self):
        if self.tipo_plano == PlanoEnum.Premium:
            if not self.id_vaga:
                raise ValueError("Plano premium: escolha a vaga exclusiva do cliente.")
            self.cotas = 1   # um plano premium = uma vaga exclusiva
        return self


class MensalidadeCreate(MensalidadeEntrada, AuditoriaBase):
    id_cliente: int


class MensalidadeCotas(AuditoriaBase):
    cotas: int = Field(ge=1, le=20)


class MensalidadePublico(BaseModel):
    id: int
    id_cliente: int
    categoria: str
    cotas: int
    tipo_plano: str = "Rotativo"
    id_vaga: Optional[int] = None
    data_inicio: date
    data_fim: Optional[date] = None
    ativa: bool


class MensalidadeDetalhe(MensalidadePublico):
    cliente_nome: Optional[str] = None
    codigo_vaga: Optional[str] = None       # plano premium: código da vaga exclusiva
    valor_mensal: Optional[float] = None   # preço mensal da categoria x cotas
    em_uso: int = 0                         # cotas com veículo no pátio agora
    vigente: bool = False                   # já começou e não foi cancelada


class CapacidadeMensalistas(BaseModel):
    categoria: str
    vagas_mensalista: int
    cotas_contratadas: int
    cotas_livres: int
    vagas_premium: int = 0
    premium_atribuidas: int = 0
    premium_livres: int = 0


# ================================================
# CADASTRO COMPLETO (cliente + endereço + veículo + plano)
# ================================================
class CadastroCompletoCreate(BaseModel):
    cliente: ClienteEntrada
    endereco: Optional[EnderecoEntrada] = None
    veiculo: Optional[VeiculoEntrada] = None
    mensalidade: Optional[MensalidadeEntrada] = None


class CadastroCompletoPublico(BaseModel):
    cliente: ClientePublico
    endereco: Optional[EnderecoPublico] = None
    veiculo: Optional[VeiculoPublico] = None
    mensalidade: Optional[MensalidadePublico] = None


class ClienteAtualizar(BaseModel):
    """Edição do cadastro: dados do cliente (sem o documento) e (opcionalmente) endereço."""
    cliente: ClienteEdicao
    endereco: Optional[EnderecoEntrada] = None


class ClienteCompleto(BaseModel):
    cliente: ClientePublico
    endereco: Optional[EnderecoPublico] = None
    veiculos: List[VeiculoPublico] = []
    mensalidades: List[MensalidadeDetalhe] = []


class ModoEntrada(BaseModel):
    """Como o veículo vai entrar: mensalista (usa uma cota) ou horista."""
    modo: str                        # "Mensalista" | "Horista"
    tem_plano: bool
    cotas: int = 0
    em_uso: int = 0
    esgotado: bool = False           # plano sem cota livre (precisa confirmar entrada como horista)
    placas_em_uso: List[str] = []
    vaga_premium: Optional[dict] = None   # modo Premium: a vaga exclusiva livre do cliente
    inicio_futuro: Optional[date] = None
    cliente_nome: Optional[str] = None
    categoria: str = "Carro"
    mensagem: str = ""
