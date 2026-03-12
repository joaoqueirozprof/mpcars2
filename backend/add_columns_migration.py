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
        ("contratos", "taxa_combustivel", "NUMERIC(10,2)"),
        ("contratos", "taxa_limpeza", "NUMERIC(10,2)"),
        ("contratos", "taxa_higienizacao", "NUMERIC(10,2)"),
        ("contratos", "taxa_pneus", "NUMERIC(10,2)"),
        ("contratos", "taxa_acessorios", "NUMERIC(10,2)"),
        ("contratos", "valor_franquia_seguro", "NUMERIC(10,2)"),
        ("contratos", "taxa_administrativa", "NUMERIC(10,2)"),
        ("contratos", "desconto", "NUMERIC(10,2)"),
        ("contratos", "status_pagamento", "VARCHAR DEFAULT 'pendente'"),
        ("contratos", "forma_pagamento", "VARCHAR"),
        ("contratos", "data_vencimento_pagamento", "DATE"),
        ("contratos", "data_pagamento", "DATE"),
        ("contratos", "valor_recebido", "NUMERIC(10,2)"),
        ("contratos", "tipo", "VARCHAR DEFAULT 'cliente'"),
        ("contratos", "cartao_ultimos4", "VARCHAR(4)"),
        ("contratos", "cartao_bandeira", "VARCHAR"),
        ("contratos", "cartao_titular", "VARCHAR"),
        ("contratos", "cartao_numero", "VARCHAR"),
        ("contratos", "cartao_validade", "VARCHAR"),
        ("contratos", "cartao_codigo", "VARCHAR"),
        ("contratos", "cartao_preautorizacao", "VARCHAR"),
        # Veiculo new fields
        ("veiculos", "categoria", "VARCHAR"),
        ("veiculos", "valor_diaria", "NUMERIC(10,2)"),
        ("veiculos", "checklist", "JSONB DEFAULT '{}'::jsonb"),
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
        ("manutencoes", "updated_at", "TIMESTAMP DEFAULT NOW()"),
    ]

    # IMPORTANT: Each ALTER TABLE must be committed individually.
    # In PostgreSQL, if any statement fails inside a transaction,
    # the entire transaction is aborted and subsequent statements are ignored.
    # Using autocommit per-statement prevents one failure from rolling back all changes.
    for table, column, col_type in columns_to_add:
        try:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} {}".format(table, column, col_type)))
                conn.commit()
                print("  OK: {}.{}".format(table, column))
        except Exception as e:
            print("  SKIP: {}.{} - {}".format(table, column, e))
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
