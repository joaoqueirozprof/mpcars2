"""baseline schema

Revision ID: 20260311_2300
Revises:
Create Date: 2026-03-11 23:00:00
"""

from typing import Sequence, Union

from alembic import op

from app.core.database import Base
import app.models  # noqa: F401
import app.models.user  # noqa: F401
from add_columns_migration import run_migration


# revision identifiers, used by Alembic.
revision: str = "20260311_2300"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    run_migration()


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
