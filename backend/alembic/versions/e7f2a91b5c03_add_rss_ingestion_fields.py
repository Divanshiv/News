"""add rss ingestion fields

Revision ID: e7f2a91b5c03
Revises: 1851973ad4c4
Create Date: 2026-09-05 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7f2a91b5c03"
down_revision: Union[str, Sequence[str], None] = "1851973ad4c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add RSS ingestion fields to sources and stories."""
    op.add_column(
        "sources",
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("sources", sa.Column("last_fetch_error", sa.Text(), nullable=True))

    op.add_column("stories", sa.Column("url", sa.String(length=500), nullable=True))
    op.add_column("stories", sa.Column("author", sa.String(length=200), nullable=True))
    op.add_column("stories", sa.Column("image_url", sa.String(length=500), nullable=True))
    op.add_column(
        "stories",
        sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_stories_url"), "stories", ["url"], unique=True)


def downgrade() -> None:
    """Remove RSS ingestion fields."""
    op.drop_index(op.f("ix_stories_url"), table_name="stories")
    op.drop_column("stories", "source_published_at")
    op.drop_column("stories", "image_url")
    op.drop_column("stories", "author")
    op.drop_column("stories", "url")
    op.drop_column("sources", "last_fetch_error")
    op.drop_column("sources", "last_fetched_at")