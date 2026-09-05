from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.article import Article
from app.models.claim import Claim
from app.models.source import Source
from app.models.story import Story, StorySource
from app.services.llm.base import LLMResponse
from app.workers.article import handle_generate_article

VALID_JSON = (
    '{"headline": "Company X Announces Product Y", "subheadline": "", '
    '"summary": "Company X unveiled product Y today.", '
    '"what_happened": "Company X announced the new product at its event.", '
    '"key_details": ["Launches December 1."], '
    '"why_it_matters": "The launch expands the market.", '
    '"what_happens_next": "", '
    '"how_we_know": "Based on the official announcement.", '
    '"sources": ["https://example.com/press"], '
    '"seo_title": "Company X Announces Product Y", '
    '"seo_description": "Company X unveiled product Y today."}'
)


class FakeProvider:
    def __init__(self, text=None):
        self.text = text or VALID_JSON

    async def generate(self, prompt, **kwargs):
        return LLMResponse(text=self.text, model="m")


_SEED_COUNTER = 0


async def _seed_story(**overrides) -> int:
    global _SEED_COUNTER
    _SEED_COUNTER += 1
    fields = {
        "title": f"Writing story {_SEED_COUNTER}",
        "slug": f"writing-story-{_SEED_COUNTER}",
        "url": f"https://example.com/w/{_SEED_COUNTER}",
        "status": "VERIFICATION",
        "category": "AI",
    }
    fields.update(overrides)
    async with async_session_factory() as session:
        story = Story(**fields)
        session.add(story)
        await session.commit()
        await session.refresh(story)
        return story.id


async def _seed_source() -> int:
    async with async_session_factory() as session:
        source = Source(
            name="ACME Press",
            url="https://acme.com",
            rss_url="https://acme.com/rss",
            source_type="news",
            category="AI",
            reliability_score=0.7,
            active=True,
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)
        return source.id


async def _seed_claims(story_id: int, source_id: int):
    async with async_session_factory() as session:
        claim = Claim(
            story_id=story_id,
            claim_text="Company X announced a new product.",
            status="CONFIRMED",
            confidence_score=0.9,
        )
        session.add(claim)
        await session.flush()
        session.add(
            StorySource(
                story_id=story_id,
                source_id=source_id,
                relationship_note="research (primary)",
                relevance_score=0.9,
            )
        )
        await session.commit()


async def test_article_worker_persists_draft():
    story_id = await _seed_story()
    source_id = await _seed_source()
    await _seed_claims(story_id, source_id)

    report = await handle_generate_article(
        {"story_id": story_id}, provider=FakeProvider()
    )

    entry = report[0]
    assert "error" not in entry
    assert entry["article_id"]
    assert entry["headline"] == "Company X Announces Product Y"

    async with async_session_factory() as session:
        story = await session.get(Story, story_id)
        assert story.status == "DRAFT"

        article = (
            await session.execute(
                select(Article).where(Article.story_id == story_id)
            )
        ).scalar_one()
        assert article.status == "DRAFT"
        assert article.body
        assert "## How We Know" in article.body
        assert "## Sources" in article.body
        assert article.seo_title
        assert article.seo_description
        session.expunge_all()


async def test_article_worker_skips_story_without_claims():
    story_id = await _seed_story()
    report = await handle_generate_article(
        {"story_id": story_id}, provider=FakeProvider()
    )
    assert report[0]["error"] == "no claims to write from"


async def test_article_worker_skips_existing_article():
    story_id = await _seed_story()
    source_id = await _seed_source()
    await _seed_claims(story_id, source_id)

    await handle_generate_article({"story_id": story_id}, provider=FakeProvider())
    report = await handle_generate_article(
        {"story_id": story_id}, provider=FakeProvider()
    )
    assert report[0]["error"] == "article already exists"

    async with async_session_factory() as session:
        articles = (
            await session.execute(
                select(Article).where(Article.story_id == story_id)
            )
        ).scalars().all()
        assert len(articles) == 1


async def test_article_worker_batch_targets_verification_stories():
    good_id = await _seed_story(slug="w-batch-good")
    await _seed_story(slug="w-batch-draft", status="DRAFT")
    source_id = await _seed_source()
    await _seed_claims(good_id, source_id)

    report = await handle_generate_article({}, provider=FakeProvider())
    assert [entry["story_id"] for entry in report] == [good_id]


async def test_article_worker_handles_unknown_and_merged():
    report = await handle_generate_article(
        {"story_id": 99999}, provider=FakeProvider()
    )
    assert report[0]["error"] == "story not found"

    merged_id = await _seed_story(status="MERGED")
    report = await handle_generate_article(
        {"story_id": merged_id}, provider=FakeProvider()
    )
    assert report[0]["error"] == "story is merged"