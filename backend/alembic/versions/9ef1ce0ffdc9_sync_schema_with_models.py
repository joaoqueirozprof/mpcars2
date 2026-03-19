"""sync schema indexes and cleanup legacy tables

Revision ID: 9ef1ce0ffdc9
Revises: 4d911c4dc8e1
Create Date: 2026-03-19 11:23:07.610248
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9ef1ce0ffdc9'
down_revision: Union[str, None] = '4d911c4dc8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _safe_create_index(name, table, columns, **kw):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {idx['name'] for idx in insp.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns, **kw)


def _safe_drop_index(name, table):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {idx['name'] for idx in insp.get_indexes(table)}
    if name in existing:
        op.drop_index(name, table_name=table)


def upgrade() -> None:
    # Drop legacy table that is no longer in models
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'contrato_empresa_veiculos' in insp.get_table_names():
        op.drop_table('contrato_empresa_veiculos')

    # Add model-defined indexes (idempotent)
    _safe_create_index('ix_alerta_resolvido', 'alerta_historico', ['resolvido'])
    _safe_create_index('ix_alerta_urgencia', 'alerta_historico', ['urgencia'])
    _safe_create_index('ix_audit_logs_tabela', 'audit_logs', ['tabela'])
    _safe_create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    _safe_create_index('ix_checkin_contrato', 'checkin_checkout', ['contrato_id'])
    _safe_create_index('ix_clientes_ativo', 'clientes', ['ativo'])
    _safe_create_index('ix_clientes_nome', 'clientes', ['nome'])
    _safe_create_index('ix_clientes_validade_cnh', 'clientes', ['validade_cnh'])
    _safe_create_index('ix_contratos_cliente_id', 'contratos', ['cliente_id'])
    _safe_create_index('ix_contratos_data_criacao', 'contratos', ['data_criacao'])
    _safe_create_index('ix_contratos_veiculo_id', 'contratos', ['veiculo_id'])
    _safe_create_index('ix_despesa_contrato_contrato', 'despesa_contrato', ['contrato_id'])
    _safe_create_index('ix_despesa_veiculo_data', 'despesa_veiculo', ['data'])
    _safe_create_index('ix_despesa_veiculo_veiculo', 'despesa_veiculo', ['veiculo_id'])
    _safe_create_index('ix_documentos_entidade', 'documentos', ['tipo_entidade', 'entidade_id'])
    _safe_create_index('ix_empresas_ativo', 'empresas', ['ativo'])
    _safe_create_index('ix_ipva_parcela_ipva', 'ipva_parcela', ['ipva_id'])
    _safe_create_index('ix_ipva_parcela_status', 'ipva_parcela', ['status'])
    _safe_create_index('ix_ipva_registro_status', 'ipva_registro', ['status'])
    _safe_create_index('ix_ipva_registro_veiculo', 'ipva_registro', ['veiculo_id'])
    _safe_create_index('ix_ipva_registro_vencimento', 'ipva_registro', ['data_vencimento'])
    _safe_create_index('ix_multas_data_vencimento', 'multas', ['data_vencimento'])
    _safe_create_index('ix_parcela_seguro_seguro', 'parcela_seguro', ['seguro_id'])
    _safe_create_index('ix_parcela_seguro_status', 'parcela_seguro', ['status'])
    _safe_create_index('ix_prorrogacao_contrato', 'prorrogacao_contrato', ['contrato_id'])
    _safe_create_index('ix_quilometragem_contrato', 'quilometragem', ['contrato_id'])
    _safe_create_index('ix_reservas_cliente', 'reservas', ['cliente_id'])
    _safe_create_index('ix_reservas_veiculo_status', 'reservas', ['veiculo_id', 'status'])
    _safe_create_index('ix_seguros_status', 'seguros', ['status'])
    _safe_create_index('ix_uso_veiculo_empresa', 'uso_veiculo_empresa', ['veiculo_id', 'empresa_id'])
    _safe_create_index('ix_veiculos_ativo', 'veiculos', ['ativo'])
    _safe_create_index('ix_veiculos_status', 'veiculos', ['status'])


def downgrade() -> None:
    pass  # Indexes are additive only; legacy table is gone
