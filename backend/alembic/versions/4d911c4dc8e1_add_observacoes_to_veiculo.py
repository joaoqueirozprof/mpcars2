"""add_observacoes_to_veiculo

Revision ID: 4d911c4dc8e1
Revises: 20260311_2300
Create Date: 2026-03-18 12:45:29.031967
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '4d911c4dc8e1'
down_revision: Union[str, None] = '20260311_2300'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("veiculos")}
    if "observacoes" not in columns:
        op.add_column("veiculos", sa.Column("observacoes", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("veiculos")}
    if "observacoes" in columns:
        op.drop_column("veiculos", "observacoes")
