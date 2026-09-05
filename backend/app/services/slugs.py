import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def text_to_slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "item"


async def unique_slug(session: AsyncSession, model, title: str) -> str:
    base = text_to_slug(title)
    candidate = base
    counter = 2
    while True:
        existing = await session.execute(
            select(model.slug).where(model.slug == candidate)
        )
        if existing.scalar_one_or_none() is None:
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1