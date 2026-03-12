from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, func, Float,
    ForeignKey, Text, JSON, Numeric, Date, UniqueConstraint,
    Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum


# User model is imported from user.py
from app.models.user import User, ActivityLog


# =====================================================================
# ENUMS para validação em Python (Pydantic)
# =====================================================================
class ContratoStatus(str, enum.Enum):
    ativo = "ativo"
    finalizado = "finalizado"
    cancelado = "cancelado"


class VeiculoStatus(str, enum.Enum):
    disponivel = "disponivel"
    alugado = "alugado"
    manutencao = "manutencao"
    inativo = "inativo"


class ReservaStatus(str, enum.Enum):
    pendente = "pendente"
    confirmada = "confirmada"
    convertida = "convertida"
    cancelada = "cancelada"


class ParcelaStatus(str, enum.Enum):
    pendente = "pendente"
    pago = "pago"
    atrasado = "atrasado"


class MultaStatus(str, enum.Enum):
    pendente = "pendente"
    pago = "pago"
    recurso = "recurso"


class ManutencaoStatus(str, enum.Enum):
    pendente = "pendente"
    agendada = "agendada"
    em_andamento = "em_andamento"
    concluida = "concluida"


class IpvaStatus(str, enum.Enum):
    pendente = "pendente"
    pago = "pago"
    atrasado = "atrasado"


class UrgenciaAlerta(str, enum.Enum):
    info = "info"
    atencao = "atencao"
    critico = "critico"


# =====================================================================
# MODELS
# =====================================================================

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    cnpj = Column(String, unique=True, nullable=False)
    razao_social = Column(String, nullable=False)
    endereco = Column(String)
    cidade = Column(String)
    estado = Column(String)
    cep = Column(String)
    telefone = Column(String)
    email = Column(String)
    contato_principal = Column(String)
    data_cadastro = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    ativo = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_empresas_ativo", "ativo"),
    )


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    cpf = Column(String, unique=True, nullable=False)
    rg = Column(String)
    data_nascimento = Column(Date)
    telefone = Column(String)
    email = Column(String, unique=True)
    endereco_residencial = Column(String)
    numero_residencial = Column(String)
    complemento_residencial = Column(String)
    cidade_residencial = Column(String)
    estado_residencial = Column(String)
    cep_residencial = Column(String)
    endereco_comercial = Column(String)
    numero_comercial = Column(String)
    complemento_comercial = Column(String)
    cidade_comercial = Column(String)
    estado_comercial = Column(String)
    cep_comercial = Column(String)
    numero_cnh = Column(String, unique=True)
    validade_cnh = Column(Date)
    categoria_cnh = Column(String)
    hotel_apartamento = Column(String)
    score = Column(Integer, default=100)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"))
    data_cadastro = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    ativo = Column(Boolean, default=True)
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")

    __table_args__ = (
        Index("ix_clientes_ativo", "ativo"),
        Index("ix_clientes_nome", "nome"),
        Index("ix_clientes_validade_cnh", "validade_cnh"),
    )


class Veiculo(Base):
    __tablename__ = "veiculos"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String, unique=True, nullable=False)
    marca = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    ano = Column(Integer)
    cor = Column(String)
    chassis = Column(String, unique=True)
    renavam = Column(String, unique=True)
    combustivel = Column(String)
    capacidade_tanque = Column(Float)
    km_atual = Column(Float, default=0)
    data_aquisicao = Column(Date)
    valor_aquisicao = Column(Numeric(10, 2))
    status = Column(String, default="disponivel")
    # Checklist como JSON flexível
    checklist = Column(JSON, default=dict)
    # Manter colunas antigas para compatibilidade
    checklist_item_1 = Column(Integer, default=0)
    checklist_item_2 = Column(Integer, default=0)
    checklist_item_3 = Column(Integer, default=0)
    checklist_item_4 = Column(Integer, default=0)
    checklist_item_5 = Column(Integer, default=0)
    checklist_item_6 = Column(Integer, default=0)
    checklist_item_7 = Column(Integer, default=0)
    checklist_item_8 = Column(Integer, default=0)
    checklist_item_9 = Column(Integer, default=0)
    checklist_item_10 = Column(Integer, default=0)
    categoria = Column(String)
    valor_diaria = Column(Numeric(10, 2))
    foto_url = Column(String, nullable=True)
    data_cadastro = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    ativo = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_veiculos_status", "status"),
        Index("ix_veiculos_ativo", "ativo"),
        Index("ix_veiculos_status_ativo", "status", "ativo"),
    )


class Contrato(Base):
    __tablename__ = "contratos"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String, unique=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="RESTRICT"), nullable=False)
    data_inicio = Column(DateTime, nullable=False)
    data_fim = Column(DateTime, nullable=False)
    km_inicial = Column(Float)
    km_final = Column(Float)
    valor_diaria = Column(Numeric(10, 2), nullable=False)
    valor_total = Column(Numeric(10, 2))
    status = Column(String, default="ativo")
    # Cartão: apenas últimos 4 dígitos e bandeira (PCI compliance)
    cartao_ultimos4 = Column(String(4))
    cartao_bandeira = Column(String)
    cartao_titular = Column(String)
    cartao_preautorizacao = Column(String)
    # Colunas antigas mantidas para migração gradual
    cartao_numero = Column(String)
    cartao_validade = Column(String)
    cartao_codigo = Column(String)
    observacoes = Column(Text)
    hora_saida = Column(String)
    combustivel_saida = Column(String)
    combustivel_retorno = Column(String)
    km_livres = Column(Float)
    qtd_diarias = Column(Integer)
    valor_hora_extra = Column(Numeric(10, 2))
    valor_km_excedente = Column(Numeric(10, 2))
    valor_avarias = Column(Numeric(10, 2))
    taxa_combustivel = Column(Numeric(10, 2))
    taxa_limpeza = Column(Numeric(10, 2))
    taxa_higienizacao = Column(Numeric(10, 2))
    taxa_pneus = Column(Numeric(10, 2))
    taxa_acessorios = Column(Numeric(10, 2))
    valor_franquia_seguro = Column(Numeric(10, 2))
    taxa_administrativa = Column(Numeric(10, 2))
    desconto = Column(Numeric(10, 2))
    status_pagamento = Column(String, default="pendente")
    forma_pagamento = Column(String)
    data_vencimento_pagamento = Column(Date)
    data_pagamento = Column(Date)
    valor_recebido = Column(Numeric(10, 2))
    tipo = Column(String, default="cliente")
    data_criacao = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    data_finalizacao = Column(DateTime)
    cliente = relationship("Cliente", foreign_keys=[cliente_id], lazy="select")
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")

    __table_args__ = (
        Index("ix_contratos_status", "status"),
        Index("ix_contratos_cliente_id", "cliente_id"),
        Index("ix_contratos_veiculo_id", "veiculo_id"),
        Index("ix_contratos_data_criacao", "data_criacao"),
        Index("ix_contratos_veiculo_status", "veiculo_id", "status"),
    )


class Quilometragem(Base):
    __tablename__ = "quilometragem"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    discriminacao = Column(String)
    quantidade = Column(Float)
    preco_unitario = Column(Numeric(10, 2))
    preco_total = Column(Numeric(10, 2))
    data_registro = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_quilometragem_contrato", "contrato_id"),
    )


class DespesaContrato(Base):
    __tablename__ = "despesa_contrato"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String)
    descricao = Column(String)
    valor = Column(Numeric(10, 2))
    data_registro = Column(DateTime, server_default=func.now())
    responsavel = Column(String)

    __table_args__ = (
        Index("ix_despesa_contrato_contrato", "contrato_id"),
    )


class ProrrogacaoContrato(Base):
    __tablename__ = "prorrogacao_contrato"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    data_anterior = Column(DateTime)
    data_nova = Column(DateTime)
    motivo = Column(String)
    diarias_adicionais = Column(Integer)
    valor_adicional = Column(Numeric(10, 2))
    data_criacao = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_prorrogacao_contrato", "contrato_id"),
    )


class MotoristaEmpresa(Base):
    __tablename__ = "motorista_empresa"
    __table_args__ = (
        UniqueConstraint("empresa_id", "cliente_id", name="uq_motorista_empresa"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    cargo = Column(String)
    ativo = Column(Boolean, default=True)
    data_vinculo = Column(DateTime, server_default=func.now())


class DespesaVeiculo(Base):
    __tablename__ = "despesa_veiculo"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String)
    valor = Column(Numeric(10, 2), nullable=False)
    descricao = Column(String)
    km = Column(Float)
    data = Column(DateTime, server_default=func.now())
    pneu = Column(Boolean, default=False)
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")

    __table_args__ = (
        Index("ix_despesa_veiculo_veiculo", "veiculo_id"),
        Index("ix_despesa_veiculo_data", "data"),
    )


class DespesaLoja(Base):
    __tablename__ = "despesa_loja"

    id = Column(Integer, primary_key=True, index=True)
    mes = Column(Integer)
    ano = Column(Integer)
    categoria = Column(String)
    valor = Column(Numeric(10, 2))
    descricao = Column(String)
    data = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_despesa_loja_mes_ano", "mes", "ano"),
    )


class DespesaOperacional(Base):
    __tablename__ = "despesa_operacional"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)
    origem_tabela = Column(String)
    origem_id = Column(Integer)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="SET NULL"))
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"))
    descricao = Column(String)
    valor = Column(Numeric(10, 2))
    data = Column(DateTime, server_default=func.now())
    categoria = Column(String)
    mes = Column(Integer)
    ano = Column(Integer)


class LancamentoFinanceiro(Base):
    __tablename__ = "lancamentos_financeiros"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    tipo = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default="pendente")
    data_criacao = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_lancamentos_financeiros_data", "data"),
        Index("ix_lancamentos_financeiros_tipo", "tipo"),
        Index("ix_lancamentos_financeiros_status", "status"),
    )


class Seguro(Base):
    __tablename__ = "seguros"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    seguradora = Column(String)
    numero_apolice = Column(String, unique=True)
    tipo_seguro = Column(String)
    data_inicio = Column(Date)
    data_fim = Column(Date)
    valor = Column(Numeric(10, 2))
    valor_franquia = Column(Numeric(10, 2))
    status = Column(String, default="ativo")
    qtd_parcelas = Column(Integer)
    data_criacao = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")

    __table_args__ = (
        Index("ix_seguros_veiculo", "veiculo_id"),
        Index("ix_seguros_status", "status"),
        Index("ix_seguros_data_fim", "data_fim"),
    )


class ParcelaSeguro(Base):
    __tablename__ = "parcela_seguro"

    id = Column(Integer, primary_key=True, index=True)
    seguro_id = Column(Integer, ForeignKey("seguros.id", ondelete="CASCADE"), nullable=False)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    numero_parcela = Column(Integer)
    valor = Column(Numeric(10, 2))
    vencimento = Column(Date)
    data_pagamento = Column(Date)
    status = Column(String, default="pendente")
    seguro = relationship("Seguro", foreign_keys=[seguro_id], lazy="select")

    __table_args__ = (
        Index("ix_parcela_seguro_seguro", "seguro_id"),
        Index("ix_parcela_seguro_status", "status"),
    )


class IpvaAliquota(Base):
    __tablename__ = "ipva_aliquota"
    __table_args__ = (
        UniqueConstraint("estado", "tipo_veiculo", name="uq_ipva_aliquota"),
    )

    id = Column(Integer, primary_key=True, index=True)
    estado = Column(String, nullable=False)
    tipo_veiculo = Column(String, nullable=False)
    aliquota = Column(Float)
    descricao = Column(String)


class IpvaRegistro(Base):
    __tablename__ = "ipva_registro"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    ano_referencia = Column(Integer)
    valor_venal = Column(Numeric(10, 2))
    aliquota = Column(Float)
    valor_ipva = Column(Numeric(10, 2))
    valor_pago = Column(Numeric(10, 2))
    data_vencimento = Column(Date)
    data_pagamento = Column(Date)
    status = Column(String, default="pendente")
    data_criacao = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    qtd_parcelas = Column(Integer)
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")

    __table_args__ = (
        Index("ix_ipva_registro_veiculo", "veiculo_id"),
        Index("ix_ipva_registro_status", "status"),
        Index("ix_ipva_registro_vencimento", "data_vencimento"),
    )


class IpvaParcela(Base):
    __tablename__ = "ipva_parcela"

    id = Column(Integer, primary_key=True, index=True)
    ipva_id = Column(Integer, ForeignKey("ipva_registro.id", ondelete="CASCADE"), nullable=False)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    numero_parcela = Column(Integer)
    valor = Column(Numeric(10, 2))
    vencimento = Column(Date)
    data_pagamento = Column(Date)
    status = Column(String, default="pendente")
    ipva = relationship("IpvaRegistro", foreign_keys=[ipva_id], lazy="select")

    __table_args__ = (
        Index("ix_ipva_parcela_ipva", "ipva_id"),
        Index("ix_ipva_parcela_status", "status"),
    )


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="RESTRICT"), nullable=False)
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime)
    status = Column(String, default="pendente")
    valor_estimado = Column(Numeric(10, 2))
    data_criacao = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    cliente = relationship("Cliente", foreign_keys=[cliente_id], lazy="select")
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")

    __table_args__ = (
        Index("ix_reservas_veiculo_status", "veiculo_id", "status"),
        Index("ix_reservas_cliente", "cliente_id"),
    )


class CheckinCheckout(Base):
    __tablename__ = "checkin_checkout"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String)
    data_hora = Column(DateTime, server_default=func.now())
    km = Column(Float)
    nivel_combustivel = Column(String)
    itens_checklist = Column(JSON)
    avarias = Column(Text)

    __table_args__ = (
        Index("ix_checkin_contrato", "contrato_id"),
    )


class Multa(Base):
    __tablename__ = "multas"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    contrato_id = Column(Integer, ForeignKey("contratos.id", ondelete="SET NULL"))
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"))
    data_infracao = Column(Date)
    numero_infracao = Column(String)
    data_vencimento = Column(Date)
    valor = Column(Numeric(10, 2))
    pontos = Column(Integer)
    gravidade = Column(String)
    descricao = Column(String)
    status = Column(String, default="pendente")
    responsavel = Column(String)
    data_pagamento = Column(Date)
    data_criacao = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")
    cliente = relationship("Cliente", foreign_keys=[cliente_id], lazy="select")
    contrato = relationship("Contrato", foreign_keys=[contrato_id], lazy="select")

    __table_args__ = (
        Index("ix_multas_veiculo", "veiculo_id"),
        Index("ix_multas_status", "status"),
        Index("ix_multas_data_vencimento", "data_vencimento"),
    )


class Manutencao(Base):
    __tablename__ = "manutencoes"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String)
    descricao = Column(String)
    km_realizada = Column(Float)
    km_proxima = Column(Float)
    data_realizada = Column(Date)
    data_proxima = Column(Date)
    custo = Column(Numeric(10, 2))
    oficina = Column(String)
    status = Column(String, default="pendente")
    data_criacao = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")

    __table_args__ = (
        Index("ix_manutencoes_veiculo", "veiculo_id"),
        Index("ix_manutencoes_status", "status"),
        Index("ix_manutencoes_data_proxima", "data_proxima"),
    )


class UsoVeiculoEmpresa(Base):
    __tablename__ = "uso_veiculo_empresa"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    contrato_id = Column(Integer, ForeignKey("contratos.id", ondelete="SET NULL"))
    km_inicial = Column(Float)
    km_final = Column(Float)
    km_percorrido = Column(Float)
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime)
    km_referencia = Column(Float)
    valor_km_extra = Column(Numeric(10, 2))
    valor_diaria_empresa = Column(Numeric(10, 2))
    status = Column(String, default="ativo")
    data_criacao = Column(DateTime, server_default=func.now())
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")
    contrato = relationship("Contrato", foreign_keys=[contrato_id], lazy="select")
    despesas = relationship("DespesaNF", foreign_keys="DespesaNF.uso_id", lazy="select")

    __table_args__ = (
        Index("ix_uso_veiculo_empresa", "veiculo_id", "empresa_id"),
    )


class RelatorioNF(Base):
    __tablename__ = "relatorio_nf"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    uso_id = Column(Integer, ForeignKey("uso_veiculo_empresa.id", ondelete="SET NULL"))
    periodo_inicio = Column(Date)
    periodo_fim = Column(Date)
    km_percorrida = Column(Float)
    km_excedente = Column(Float)
    valor_total_extra = Column(Numeric(10, 2))
    caminho_pdf = Column(String)
    data_criacao = Column(DateTime, server_default=func.now())


class DespesaNF(Base):
    __tablename__ = "despesa_nf"

    id = Column(Integer, primary_key=True, index=True)
    uso_id = Column(Integer, ForeignKey("uso_veiculo_empresa.id", ondelete="CASCADE"))
    veiculo_id = Column(Integer, ForeignKey("veiculos.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String)
    descricao = Column(String)
    valor = Column(Numeric(10, 2))
    data = Column(DateTime, server_default=func.now())


class Documento(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    tipo_entidade = Column(String)
    entidade_id = Column(Integer)
    nome_arquivo = Column(String, unique=True)
    nome_original = Column(String)
    tipo_documento = Column(String)
    caminho = Column(String)
    tamanho = Column(Float)
    data_upload = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_documentos_entidade", "tipo_entidade", "entidade_id"),
    )


class Configuracao(Base):
    __tablename__ = "configuracoes"

    id = Column(Integer, primary_key=True, index=True)
    chave = Column(String, unique=True, nullable=False)
    valor = Column(Text)
    data_atualizacao = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, server_default=func.now())
    acao = Column(String)
    tabela = Column(String)
    registro_id = Column(Integer)
    dados_anteriores = Column(JSON)
    dados_novos = Column(JSON)
    usuario = Column(String)
    ip_address = Column(String)

    __table_args__ = (
        Index("ix_audit_logs_tabela", "tabela"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )


class AlertaHistorico(Base):
    __tablename__ = "alerta_historico"

    id = Column(Integer, primary_key=True, index=True)
    tipo_alerta = Column(String)
    urgencia = Column(String)
    entidade_tipo = Column(String)
    entidade_id = Column(Integer)
    titulo = Column(String)
    descricao = Column(Text)
    data_criacao = Column(DateTime, server_default=func.now())
    resolvido = Column(Boolean, default=False)
    resolvido_por = Column(String)
    data_resolucao = Column(DateTime)

    __table_args__ = (
        Index("ix_alerta_resolvido", "resolvido"),
        Index("ix_alerta_urgencia", "urgencia"),
    )
