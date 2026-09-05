"""add story research fields

Revision ID: e5f6a7b8c9d0
Revises: d0e1f2a3b4c5
Create Date: 2026-09-05 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 6 research fields to stories."""
    op.add_column(
        "stories",
        sa.Column("researched_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove research fields."""
    op.drop_column("stories", "researched_at")