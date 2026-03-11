"""Add missing columns for reports specification"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine
from sqlalchemy import text

def run_migration():
    columns_to_add = [
        # Contrato new fields
        ("contratos", "hora_saida", "VARCHAR"),
        ("contratos", "combustivel_saida", "VARCHAR"),
        ("contratos", "combustivel_retorno", "VARCHAR"),
        ("contratos", "km_livres", "FLOAT"),
        ("contratos", "qtd_diarias", "INTEGER"),
        ("contratos", "valor_hora_extra", "NUMERIC(10,2)"),
        ("contratos", "valor_km_excedente", "NUMERIC(10,2)"),
        ("contratos", "valor_avarias", "NUMERIC(10,2)"),
        ("contratos", "desconto", "NUMERIC(10,2)"),
        ("contratos", "tipo", "VARCHAR DEFAULT 'cliente'"),
        ("contratos", "cartao_codigo", "VARCHAR"),
        ("contratos", "cartao_preautorizacao", "VARCHAR"),
        # Veiculo new fields
        ("veiculos", "categoria", "VARCHAR"),
        ("veiculos", "valor_diaria", "NUMERIC(10,2)"),
        # DespesaVeiculo new field
        ("despesa_veiculo", "tipo", "VARCHAR"),
        # DespesaLoja new field
        ("despesa_loja", "categoria", "VARCHAR"),
        # Multa new fields
        ("multas", "descricao", "VARCHAR"),
        ("multas", "data_pagamento", "DATE"),
        # IpvaRegistro new field
        ("ipva_registro", "data_pagamento", "DATE"),
        # UsoVeiculoEmpresa new fields
        ("uso_veiculo_empresa", "km_percorrido", "FLOAT"),
        ("uso_veiculo_empresa", "valor_diaria_empresa", "NUMERIC(10,2)"),
        # DespesaNF fields
        ("despesa_nf", "tipo", "VARCHAR"),
        # updated_at columns for all major tables
        ("empresas", "updated_at", "TIMESTAMP DEFAULT NOW()"),
        ("clientes", "updated_at", "TIMESTAMP DEFAULT NOW()"),
        ("veiculos", "updated_at", "TIMESTAMP DEFAULT NOW()"),
        ("contratos", "updated_at", "TIMESTAMP DEFAULT NOW()"),
        ("seguros", "updated_at", "TIMESTAMP DEFAULT NOW()"),
        ("ipva_registro", "updated_at", "TIMESTAMP DEFAULT NOW()"),
        ("reservas", "updated_at", "TIMESTAMP DEFAULT NOW()"),
        ("multas", "updated_at", "TIMESTAMP DEFAULT NOW()"),
        ("manutencao", "updated_at", "TIMESTAMP DEFAULT NOW()"),
    ]
    
    with engine.connect() as conn:
        for table, column, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"))
                print(f"  OK: {table}.{column}")
            except Exception as e:
                print(f"  SKIP: {table}.{column} - {e}")
        conn.commit()
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
