from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, date


# Validação das regras do banco da dados
class TradeBase(BaseModel):
    ativo: str = Field(..., min_length=2, max_length=10)
    ordem: str = Field(..., description="Deve ser BUY ou SELL")
    setup_id: int
    resultado: float = 0.0
    emocional_id: int
    relatorio: Optional[str] = ""
    quantidade: Optional[int] = None
    preco_entrada: Optional[float] = None
    preco_saida: Optional[float] = None

    # Inteligência de validação: intercepta o erro de ativos futuros antes do banco
    @model_validator(mode="after")
    def verificar_dados_futuros(self) -> "TradeBase":
        ativo_upper = self.ativo.upper()
        # Se for contrato futuro (WIN ou WDO)
        if any(futuro in ativo_upper for futuro in ["WIN", "WDO"]):
            if self.quantidade is None or self.quantidade <= 0:
                self.quantidade = 1  # Força um valor padrão seguro em vez de null
            if self.preco_entrada is None or self.preco_entrada == 0:
                self.preco_entrada = 1.0
            if self.preco_saida is None or self.preco_saida == 0:
                self.preco_saida = 1.0
        return self

class TradeCreate(TradeBase):
    pass

class TradeResponse(TradeBase):
    id: int
    data_trade: str

    @classmethod
    def from_supabase(cls, data: dict):
        # Transforma o retorno bruto do Supabase num objeto validado
        return cls(
            id=data["id"],
            ativo=data["ativo"],
            ordem=data["ordem"],
            setup_id=data["setup_id"],
            resultado=float(data["resultado"]),
            emocional_id=data["emocional_id"],
            relatorio=data.get("relatorio", ""),
            quantidade=data.get("quantidade"),
            preco_entrada=data.get("preco_entrada"),
            preco_saida=data.get("preco_saida"),
            data_trade=data["data_trade"]
        )


class TradeInferenciaSchema(BaseModel):
    # Outros campos do seu trade (ativo, quantidade, etc) permanecem aqui
    setup_nome: str
    emocional_nome: str

class CheckinBase(BaseModel):
    data: date
    checkin: datetime
    checkout: Optional[datetime] = None
    status: str = Field(default="Presente", min_length=1, max_length=32)
    observacao: Optional[str] = ""

class CheckinCreate(CheckinBase):
    pass

class CheckinUpdate(BaseModel):
    checkout: Optional[datetime] = None
    status: Optional[str] = None
    observacao: Optional[str] = None