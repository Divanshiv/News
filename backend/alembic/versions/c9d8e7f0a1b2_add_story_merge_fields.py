"""add story merge fields

Revision ID: c9d8e7f0a1b2
Revises: e7f2a91b5c03
Create Date: 2026-09-05 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f0a1b2"
down_revision: Union[str, Sequence[str], None] = "e7f2a91b5c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 4 dedup merge fields to stories."""
    op.add_column("stories", sa.Column("merged_into_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_stories_merged_into_id",
        "stories",
        "stories",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_stories_merged_into_id"), "stories", ["merged_into_id"]
    )


def downgrade() -> None:
    """Remove story merge fields."""
    op.drop_index(op.f("ix_stories_merged_into_id"), table_name="stories")
    op.drop_constraint("fk_stories_merged_into_id", "stories", type_="foreignkey")
    op.drop_column("stories", "merged_into_id")