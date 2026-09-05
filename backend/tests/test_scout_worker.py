from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.story import Story
from app.services.llm.base import LLMResponse
from app.workers.scout import handle_run_scout

VALID_JSON = (
    '{"should_research": true, "importance": 7, '
    '"category": "AI", "reason": "Significant model release."}'
)


class FakeProvider:
    def __init__(self, text=VALID_JSON):
        self.text = text

    async def generate(self, prompt, **kwargs):
        return LLMResponse(text=self.text, model="m")


_SEED_COUNTER = 0


async def _seed_story(**overrides) -> int:
    global _SEED_COUNTER
    _SEED_COUNTER += 1
    fields = {
        "title": f"Test story {_SEED_COUNTER}",
        "slug": f"test-story-{_SEED_COUNTER}",
        "url": f"https://example.com/story/{_SEED_COUNTER}",
        "status": "DISCOVERED",
    }
    fields.update(overrides)
    async with async_session_factory() as session:
        story = Story(**fields)
        session.add(story)
        await session.commit()
        await session.refresh(story)
        return story.id


async def test_run_scout_scores_only_unscouted_discovered_stories():
    scouted_id = await _seed_story(slug="already-scouted", should_research=True)
    other_id = await _seed_story(slug="other-status", status="RESEARCHING")
    target_id = await _seed_story(
        slug="target", title="OpenAI launches frontier model", category="AI"
    )

    report = await handle_run_scout({}, provider=FakeProvider())

    assert len(report) == 1
    entry = report[0]
    assert entry["story_id"] == target_id
    assert entry["should_research"] is True
    assert entry["importance"] == 7
    assert entry["category"] == "AI"

    async with async_session_factory() as session:
        target = await session.get(Story, target_id)
        assert target.should_research is True
        assert target.importance_score == 7.0
        assert target.scout_reason == "Significant model release."
        assert target.scouted_at is not None
        assert target.scouted_at.tzinfo == timezone.utc

        untouched = await session.get(Story, scouted_id)
        assert untouched.scout_reason is None

        other = await session.get(Story, other_id)
        assert other.should_research is None


async def test_run_scout_single_story_payload():
    skipped_id = await _seed_story(slug="skip-me")
    target_id = await _seed_story(slug="scout-me")

    report = await handle_run_scout({"story_id": target_id}, provider=FakeProvider())

    assert [entry["story_id"] for entry in report] == [target_id]

    async with async_session_factory() as session:
        skipped = await session.get(Story, skipped_id)
        assert skipped.should_research is None


async def test_run_scout_skips_merged_and_unknown():
    merged_id = await _seed_story(slug="merged", status="MERGED")
    report = await handle_run_scout({"story_id": merged_id}, provider=FakeProvider())
    assert report[0]["error"] == "story is merged"

    report = await handle_run_scout({"story_id": 99999}, provider=FakeProvider())
    assert report == []


async def test_run_scout_writes_category_from_verdict():
    story_id = await _seed_story(slug="cat-change", category="Technology")
    await handle_run_scout({"story_id": story_id}, provider=FakeProvider())
    async with async_session_factory() as session:
        story = await session.get(Story, story_id)
        assert story.category == "AI"


async def test_run_scout_double_run_is_idempotent():
    story_id = await _seed_story(slug="idempotent")
    await handle_run_scout({"story_id": story_id}, provider=FakeProvider())
    first_report = await handle_run_scout({}, provider=FakeProvider())
    assert [entry["story_id"] for entry in first_report] == []


async def test_run_scout_isolates_per_story_failure():
    async with async_session_factory() as session:
        story = Story(
            title="Failing story",
            slug="failing-story",
            url="https://example.com/fail",
            status="DISCOVERED",
        )
        session.add(story)
        story2 = Story(
            title="Second story",
            slug="second-story",
            url="https://example.com/second",
            status="DISCOVERED",
        )
        session.add(story2)
        await session.commit()
        failing_id = story.id
        ok_id = story2.id

    class FlakyProvider:
        calls = 0

        async def generate(self, prompt, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("boom")
            return LLMResponse(
                text='{"should_research": false, "importance": 3, "category": null, "reason": "Quiet day."}',
                model="m",
            )

    provider = FlakyProvider()
    report = await handle_run_scout({}, provider=provider)

    by_id = {entry["story_id"]: entry for entry in report}
    assert by_id[failing_id]["error"] == "scout failure"
    assert by_id[ok_id]["should_research"] is False

    async with async_session_factory() as session:
        failing = await session.get(Story, failing_id)
        assert failing.should_research is None
        ok = await session.get(Story, ok_id)
        assert ok.should_research is False


async def test_scouted_at_filter_drives_batch_queries():
    async with async_session_factory() as session:
        result = await session.execute(
            select(Story).where(Story.should_research.is_(None))
        )
        assert result.scalars().all() == []