from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ContratoBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numero: Optional[str] = None
    cliente_id: int
    veiculo_id: int
    data_inicio: datetime | date
    data_fim: Optional[datetime | date] = None
    km_inicial: Optional[float] = None
    quilometragem_inicial: Optional[float] = None
    km_atual_veiculo: Optional[float] = None
    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    valor_diaria: float
    valor_total: Optional[float] = None
    status: str = "ativo"
    observacoes: Optional[str] = None
    hora_saida: Optional[str] = None
    combustivel_saida: Optional[str] = None
    combustivel_retorno: Optional[str] = None
    km_livres: Optional[float] = None
    qtd_diarias: Optional[int] = None
    valor_hora_extra: Optional[float] = None
    valor_km_excedente: Optional[float] = None
    valor_avarias: Optional[float] = None
    taxa_combustivel: Optional[float] = None
    taxa_limpeza: Optional[float] = None
    taxa_higienizacao: Optional[float] = None
    taxa_pneus: Optional[float] = None
    taxa_acessorios: Optional[float] = None
    valor_franquia_seguro: Optional[float] = None
    taxa_administrativa: Optional[float] = None
    desconto: Optional[float] = None
    status_pagamento: Optional[str] = "pendente"
    forma_pagamento: Optional[str] = None
    data_vencimento_pagamento: Optional[date] = None
    data_pagamento: Optional[date] = None
    valor_recebido: Optional[float] = None
    tipo: Optional[str] = "cliente"
    vigencia_indeterminada: Optional[bool] = False
    empresa_uso_id: Optional[int] = None
    empresa_id: Optional[int] = None


class ContratoCreate(ContratoBase):
    pass


class ContratoUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    numero: Optional[str] = None
    cliente_id: Optional[int] = None
    veiculo_id: Optional[int] = None
    data_inicio: Optional[datetime | date] = None
    data_fim: Optional[datetime | date] = None
    km_inicial: Optional[float] = None
    quilometragem_inicial: Optional[float] = None
    km_atual_veiculo: Optional[float] = None
    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    valor_diaria: Optional[float] = None
    valor_total: Optional[float] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None
    hora_saida: Optional[str] = None
    combustivel_saida: Optional[str] = None
    combustivel_retorno: Optional[str] = None
    km_livres: Optional[float] = None
    qtd_diarias: Optional[int] = None
    valor_hora_extra: Optional[float] = None
    valor_km_excedente: Optional[float] = None
    valor_avarias: Optional[float] = None
    taxa_combustivel: Optional[float] = None
    taxa_limpeza: Optional[float] = None
    taxa_higienizacao: Optional[float] = None
    taxa_pneus: Optional[float] = None
    taxa_acessorios: Optional[float] = None
    valor_franquia_seguro: Optional[float] = None
    taxa_administrativa: Optional[float] = None
    desconto: Optional[float] = None
    status_pagamento: Optional[str] = None
    forma_pagamento: Optional[str] = None
    data_vencimento_pagamento: Optional[date] = None
    data_pagamento: Optional[date] = None
    valor_recebido: Optional[float] = None
    tipo: Optional[str] = None
    vigencia_indeterminada: Optional[bool] = None
    empresa_uso_id: Optional[int] = None
    empresa_id: Optional[int] = None


class ContratoFinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    km_final: Optional[float] = None
    quilometragem_final: Optional[float] = None
    km_atual_veiculo: Optional[float] = None
    combustivel_retorno: Optional[str] = None
    itens_checklist: Optional[dict] = None
    valor_avarias: Optional[float] = None
    taxa_combustivel: Optional[float] = None
    taxa_limpeza: Optional[float] = None
    taxa_higienizacao: Optional[float] = None
    taxa_pneus: Optional[float] = None
    taxa_acessorios: Optional[float] = None
    valor_franquia_seguro: Optional[float] = None
    taxa_administrativa: Optional[float] = None
    desconto: Optional[float] = None
    status_pagamento: Optional[str] = None
    forma_pagamento: Optional[str] = None
    data_vencimento_pagamento: Optional[date] = None
    data_pagamento: Optional[date] = None
    valor_recebido: Optional[float] = None
    observacoes: Optional[str] = None
    data_finalizacao: Optional[datetime | date] = None


class ContratoPaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status_pagamento: Optional[str] = None
    forma_pagamento: Optional[str] = None
    data_vencimento_pagamento: Optional[date] = None
    data_pagamento: Optional[date] = None
    valor_recebido: Optional[float] = None


class ContratoResponse(ContratoBase):
    id: int
    data_criacao: datetime
    data_finalizacao: Optional[datetime] = None
    frota_count: Optional[int] = None

    class Config:
        from_attributes = True


class DespesaContratoResponse(BaseModel):
    id: int
    tipo: str
    descricao: str
    valor: float
    data_registro: datetime

    class Config:
        from_attributes = True
