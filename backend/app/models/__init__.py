from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Float, ForeignKey, Text, JSON, Numeric, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


# User model is imported from user.py
from app.models.user import User


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
    ativo = Column(Boolean, default=True)


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
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    data_cadastro = Column(DateTime, server_default=func.now())
    ativo = Column(Boolean, default=True)
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")


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
    data_cadastro = Column(DateTime, server_default=func.now())
    ativo = Column(Boolean, default=True)


class Contrato(Base):
    __tablename__ = "contratos"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String, unique=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    data_inicio = Column(DateTime, nullable=False)
    data_fim = Column(DateTime, nullable=False)
    km_inicial = Column(Float)
    km_final = Column(Float)
    valor_diaria = Column(Numeric(10, 2), nullable=False)
    valor_total = Column(Numeric(10, 2))
    status = Column(String, default="ativo")
    cartao_numero = Column(String)
    cartao_bandeira = Column(String)
    cartao_validade = Column(String)
    cartao_titular = Column(String)
    observacoes = Column(Text)
    data_criacao = Column(DateTime, server_default=func.now())
    data_finalizacao = Column(DateTime)
    cliente = relationship("Cliente", foreign_keys=[cliente_id], lazy="select")
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")


class Quilometragem(Base):
    __tablename__ = "quilometragem"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"), nullable=False)
    discriminacao = Column(String)
    quantidade = Column(Float)
    preco_unitario = Column(Numeric(10, 2))
    preco_total = Column(Numeric(10, 2))
    data_registro = Column(DateTime, server_default=func.now())


class DespesaContrato(Base):
    __tablename__ = "despesa_contrato"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"), nullable=False)
    tipo = Column(String)
    descricao = Column(String)
    valor = Column(Numeric(10, 2))
    data_registro = Column(DateTime, server_default=func.now())
    responsavel = Column(String)


class ProrrogacaoContrato(Base):
    __tablename__ = "prorrogacao_contrato"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"), nullable=False)
    data_anterior = Column(DateTime)
    data_nova = Column(DateTime)
    motivo = Column(String)
    diarias_adicionais = Column(Integer)
    valor_adicional = Column(Numeric(10, 2))
    data_criacao = Column(DateTime, server_default=func.now())


class MotoristaEmpresa(Base):
    __tablename__ = "motorista_empresa"
    __table_args__ = (
        UniqueConstraint("empresa_id", "cliente_id", name="uq_motorista_empresa"),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    cargo = Column(String)
    ativo = Column(Boolean, default=True)
    data_vinculo = Column(DateTime, server_default=func.now())


class DespesaVeiculo(Base):
    __tablename__ = "despesa_veiculo"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    descricao = Column(String)
    km = Column(Float)
    data = Column(DateTime, server_default=func.now())
    pneu = Column(Boolean, default=False)


class DespesaLoja(Base):
    __tablename__ = "despesa_loja"

    id = Column(Integer, primary_key=True, index=True)
    mes = Column(Integer)
    ano = Column(Integer)
    valor = Column(Numeric(10, 2))
    descricao = Column(String)
    data = Column(DateTime, server_default=func.now())


class DespesaOperacional(Base):
    __tablename__ = "despesa_operacional"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)
    origem_tabela = Column(String)
    origem_id = Column(Integer)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"))
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    descricao = Column(String)
    valor = Column(Numeric(10, 2))
    data = Column(DateTime, server_default=func.now())
    categoria = Column(String)
    mes = Column(Integer)
    ano = Column(Integer)


class Seguro(Base):
    __tablename__ = "seguros"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
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
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")


class ParcelaSeguro(Base):
    __tablename__ = "parcela_seguro"

    id = Column(Integer, primary_key=True, index=True)
    seguro_id = Column(Integer, ForeignKey("seguros.id"), nullable=False)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    numero_parcela = Column(Integer)
    valor = Column(Numeric(10, 2))
    vencimento = Column(Date)
    data_pagamento = Column(Date)
    status = Column(String, default="pendente")


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
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    ano_referencia = Column(Integer)
    valor_venal = Column(Numeric(10, 2))
    aliquota = Column(Float)
    valor_ipva = Column(Numeric(10, 2))
    valor_pago = Column(Numeric(10, 2))
    data_vencimento = Column(Date)
    status = Column(String, default="pendente")
    data_criacao = Column(DateTime, server_default=func.now())
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime)
    status = Column(String, default="pendente")
    valor_estimado = Column(Numeric(10, 2))
    data_criacao = Column(DateTime, server_default=func.now())
    cliente = relationship("Cliente", foreign_keys=[cliente_id], lazy="select")
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")


class CheckinCheckout(Base):
    __tablename__ = "checkin_checkout"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"), nullable=False)
    tipo = Column(String)
    data_hora = Column(DateTime, server_default=func.now())
    km = Column(Float)
    nivel_combustivel = Column(String)
    itens_checklist = Column(JSON)
    avarias = Column(Text)


class Multa(Base):
    __tablename__ = "multas"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    contrato_id = Column(Integer, ForeignKey("contratos.id"))
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    data_infracao = Column(Date)
    valor = Column(Numeric(10, 2))
    pontos = Column(Integer)
    gravidade = Column(String)
    status = Column(String, default="pendente")
    responsavel = Column(String)
    data_criacao = Column(DateTime, server_default=func.now())
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")
    cliente = relationship("Cliente", foreign_keys=[cliente_id], lazy="select")
    contrato = relationship("Contrato", foreign_keys=[contrato_id], lazy="select")


class Manutencao(Base):
    __tablename__ = "manutencoes"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
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
    veiculo = relationship("Veiculo", foreign_keys=[veiculo_id], lazy="select")


class UsoVeiculoEmpresa(Base):
    __tablename__ = "uso_veiculo_empresa"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    contrato_id = Column(Integer, ForeignKey("contratos.id"))
    km_inicial = Column(Float)
    km_final = Column(Float)
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime)
    km_referencia = Column(Float)
    valor_km_extra = Column(Numeric(10, 2))
    status = Column(String, default="ativo")
    data_criacao = Column(DateTime, server_default=func.now())


class RelatorioNF(Base):
    __tablename__ = "relatorio_nf"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    uso_id = Column(Integer, ForeignKey("uso_veiculo_empresa.id"))
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
    uso_id = Column(Integer, ForeignKey("uso_veiculo_empresa.id"))
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
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
