"""add story scout fields

Revision ID: d0e1f2a3b4c5
Revises: c9d8e7f0a1b2
Create Date: 2026-09-05 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 5 scout agent fields to stories."""
    op.add_column("stories", sa.Column("should_research", sa.Boolean(), nullable=True))
    op.add_column("stories", sa.Column("scout_reason", sa.Text(), nullable=True))
    op.add_column(
        "stories",
        sa.Column("scouted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_stories_should_research"), "stories", ["should_research"]
    )


def downgrade() -> None:
    """Remove scout agent fields."""
    op.drop_index(op.f("ix_stories_should_research"), table_name="stories")
    op.drop_column("stories", "scouted_at")
    op.drop_column("stories", "scout_reason")
    op.drop_column("stories", "should_research")