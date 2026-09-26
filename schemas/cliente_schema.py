# schemas/cliente_schema.py

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ClienteCreate(BaseModel):
    nome: str = Field(..., min_length=3)
    email: EmailStr
    telefone: str | None = Field(default=None, max_length=11)
    cidade: str | None = None

    @field_validator("telefone")
    @classmethod
    def validar_telefone(cls, valor: str | None) -> str | None:
        if valor is not None and not valor.isdigit():
            raise ValueError("O telefone deve conter apenas números.")
        return valor


class ClienteResponse(BaseModel):
    id: int
    nome: str
    email: EmailStr
    telefone: str | None = None
    cidade: str | None = None
    data_criacao: datetime

    model_config = ConfigDict(from_attributes=True)