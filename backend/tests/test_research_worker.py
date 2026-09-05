from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.claim import Claim, Evidence
from app.models.research import ResearchRun
from app.models.source import Source
from app.models.story import Story, StorySource
from app.services.llm.base import LLMResponse
from app.tools import SearchResult
from app.workers.research import handle_research_story


class FakeProvider:
    def __init__(self, text=None):
        self.text = text or (
            '{"claims": ["Company X announced product Y.", "Product Y launches '
            'on December 1."], "summary": "Company X unveiled product Y."}'
        )

    async def generate(self, prompt, **kwargs):
        return LLMResponse(text=self.text, model="m")


class FakeSearch:
    def __init__(self):
        self.results = [
            SearchResult(title="ACME press", url="https://acme.com/press", snippet="ACME announced product Y today."),
            SearchResult(title="Gov registry", url="https://registry.gov.in/item/3", snippet="Official registry entry about product Y."),
        ]

    async def search(self, query, limit=10):
        return self.results


class FakeFetch:
    async def extract(self, url):
        return f"Page {url}", ["Announcement paragraph with details.", "Second paragraph mentioning launch month."]


_SEED_COUNTER = 0


async def _seed_story(**overrides) -> int:
    global _SEED_COUNTER
    _SEED_COUNTER += 1
    fields = {
        "title": f"Research story {_SEED_COUNTER}",
        "slug": f"research-story-{_SEED_COUNTER}",
        "url": f"https://example.com/r/{_SEED_COUNTER}",
        "status": "DISCOVERED",
        "should_research": True,
    }
    fields.update(overrides)
    async with async_session_factory() as session:
        story = Story(**fields)
        session.add(story)
        await session.commit()
        await session.refresh(story)
        return story.id


def _tools():
    from app.tools import ResearchTools
    from app.tools.source_lookup import SourceLookupTool

    return ResearchTools(search=FakeSearch(), fetch=FakeFetch(), source_lookup=SourceLookupTool())


async def test_research_worker_persists_package():
    story_id = await _seed_story(title="Company announces product Y", category="AI")
    report = await handle_research_story(
        {"story_id": story_id}, provider=FakeProvider(), tools=_tools()
    )

    entry = report[0]
    assert entry["sources"] == 2
    assert entry["claims"] == 2
    assert "error" not in entry

    async with async_session_factory() as session:
        story = await session.get(Story, story_id)
        assert story.status == "RESEARCHING"
        assert story.researched_at is not None

        runs = (
            await session.execute(
                select(ResearchRun).where(ResearchRun.story_id == story_id)
            )
        ).scalars().all()
        assert len(runs) == 1
        assert runs[0].status == "COMPLETED"
        assert runs[0].output["sources"]

        links = (
            await session.execute(
                select(StorySource).where(StorySource.story_id == story_id)
            )
        ).scalars().all()
        assert len(links) == 2
        assert any(
            link.relationship_note and link.relationship_note.startswith("research")
            for link in links
        )

        claims = (
            await session.execute(select(Claim).where(Claim.story_id == story_id))
        ).scalars().all()
        assert len(claims) == 2

        evidence = (
            await session.execute(
                select(Evidence).where(
                    Evidence.claim_id == claims[0].id
                )
            )
        ).scalars().all()
        assert len(evidence) == 2

        sources = (await session.execute(select(Source))).scalars().all()
        gov = [s for s in sources if "gov.in" in s.url]
        assert gov and gov[0].reliability_score >= 0.8
        session.expunge_all()


async def test_research_worker_skips_already_researched():
    story_id = await _seed_story()
    await handle_research_story(
        {"story_id": story_id}, provider=FakeProvider(), tools=_tools()
    )
    report = await handle_research_story(
        {"story_id": story_id}, provider=FakeProvider(), tools=_tools()
    )
    assert report[0]["error"] == "already researched"

    async with async_session_factory() as session:
        runs = (
            await session.execute(
                select(ResearchRun).where(ResearchRun.story_id == story_id)
            )
        ).scalars().all()
        assert len(runs) == 1


async def test_research_worker_batch_targets_approved_stories():
    good_id = await _seed_story(slug="batch-good", should_research=True)
    await _seed_story(slug="batch-other", should_research=False)
    await _seed_story(slug="batch-researching", status="RESEARCHING", should_research=True)

    report = await handle_research_story({}, provider=FakeProvider(), tools=_tools())
    assert [entry["story_id"] for entry in report] == [good_id]


async def test_research_worker_handles_unknown_and_merged():
    report = await handle_research_story(
        {"story_id": 99999}, provider=FakeProvider(), tools=_tools()
    )
    assert report[0]["error"] == "story not found"

    merged_id = await _seed_story(status="MERGED")
    report = await handle_research_story(
        {"story_id": merged_id}, provider=FakeProvider(), tools=_tools()
    )
    assert report[0]["error"] == "story is merged"


async def test_research_worker_marks_failed_run_on_agent_error():
    story_id = await _seed_story()

    class ExplodingProvider:
        async def generate(self, prompt, **kwargs):
            raise RuntimeError("provider crashed unexpectedly")

    report = await handle_research_story(
        {"story_id": story_id}, provider=ExplodingProvider(), tools=_tools()
    )
    assert report[0]["error"] == "research failure"

    async with async_session_factory() as session:
        runs = (
            await session.execute(
                select(ResearchRun).where(ResearchRun.story_id == story_id)
            )
        ).scalars().all()
        assert len(runs) == 1
        assert runs[0].status == "FAILED"
        assert "provider crashed" in (runs[0].error or "")
        session.expunge_all()


async def test_research_worker_supersedes_stale_running_run():
    story_id = await _seed_story()
    async with async_session_factory() as session:
        stale = ResearchRun(
            story_id=story_id,
            agent_name="research",
            status="RUNNING",
            input={"title": "orphan run from a killed worker"},
            started_at=datetime.now(timezone.utc),
        )
        session.add(stale)
        await session.commit()

    report = await handle_research_story(
        {"story_id": story_id}, provider=FakeProvider(), tools=_tools()
    )
    assert "error" not in report[0]

    async with async_session_factory() as session:
        runs = (
            await session.execute(
                select(ResearchRun)
                .where(ResearchRun.story_id == story_id)
                .order_by(ResearchRun.id)
            )
        ).scalars().all()
        assert len(runs) == 2
        assert runs[0].status == "FAILED"
        assert "superseded" in (runs[0].error or "")
        assert runs[1].status == "COMPLETED"
        session.expunge_all()