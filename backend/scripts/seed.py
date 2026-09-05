import asyncio
import hashlib
import secrets

from sqlalchemy import select

from app.core.database import Base, async_session_factory, engine
from app.models.source import Source
from app.models.user import User

SEED_SOURCES = [
    {"name": "The Verge", "url": "https://www.theverge.com", "rss_url": "https://www.theverge.com/rss/index.xml", "source_type": "news", "category": "Technology", "reliability_score": 0.8},
    {"name": "Ars Technica", "url": "https://arstechnica.com", "rss_url": "https://feeds.arstechnica.com/arstechnica/index", "source_type": "news", "category": "Technology", "reliability_score": 0.85},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com", "rss_url": "https://www.technologyreview.com/feed/", "source_type": "news", "category": "AI", "reliability_score": 0.85},
    {"name": "NASA Breaking News", "url": "https://www.nasa.gov", "rss_url": "https://www.nasa.gov/news-release/feed/", "source_type": "official", "category": "Space", "reliability_score": 0.95},
    {"name": "ScienceDaily Top Science", "url": "https://www.sciencedaily.com", "rss_url": "https://feeds.sciencedaily.com/sciencedaily/top_news/top_science", "source_type": "news", "category": "Science", "reliability_score": 0.75},
    {"name": "The Hindu — National", "url": "https://www.thehindu.com", "rss_url": "https://www.thehindu.com/news/national/feeder/default.rss", "source_type": "news", "category": "India", "reliability_score": 0.8},
    {"name": "The Hacker News", "url": "https://thehackernews.com", "rss_url": "https://feeds.feedburner.com/TheHackersNews", "source_type": "news", "category": "Cybersecurity", "reliability_score": 0.7},
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com", "rss_url": "https://www.bleepingcomputer.com/feed/", "source_type": "news", "category": "Cybersecurity", "reliability_score": 0.75},
    {"name": "Reuters World", "url": "https://www.reuters.com", "rss_url": "https://feeds.reuters.com/reuters/worldNews", "source_type": "news", "category": "World", "reliability_score": 0.9},
    {"name": "PIB Press Releases", "url": "https://pib.gov.in", "rss_url": "https://pib.gov.in/allreleasesrss.aspx", "source_type": "government", "category": "India", "reliability_score": 0.9, "license_notes": "Government press releases; check reproduction terms."},
    {"name": "OSINT Framework", "url": "https://osintframework.com", "rss_url": None, "source_type": "research", "category": None, "reliability_score": 0.5, "license_notes": "Manual OSINT tool directory — no RSS feed; human research reference only, never ingested."},
]


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2**14, r=8, p=1).hex()
    return f"scrypt$2^14$8$1${salt}${digest}"


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        existing_user = await session.scalar(select(User).where(User.email == "admin@ainewsroom.local"))
        if existing_user is None:
            session.add(
                User(
                    email="admin@ainewsroom.local",
                    password_hash=hash_password("admin123"),
                    role="admin",
                )
            )
            print("seeded admin user (admin@ainewsroom.local / admin123)")

        existing_count = len((await session.execute(select(Source.id))).all())
        seeded = 0
        for data in SEED_SOURCES:
            dup = await session.scalar(select(Source).where(Source.name == data["name"]))
            if dup is None:
                session.add(Source(**data))
                seeded += 1
        print(f"seeded {seeded} sources ({existing_count} already present)")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())