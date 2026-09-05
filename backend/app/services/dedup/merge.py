"""Story merging: consolidate duplicate stories into one canonical story."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.story import Story, StorySource
from app.services.dedup.similarity import is_same_event
from app.services.ingestion import DUPLICATE_WINDOW_DAYS

logger = logging.getLogger(__name__)

NON_MERGABLE_STATUSES = frozenset({"APPROVED", "PUBLISHED", "MERGED"})


class MergeError(Exception):
    pass


async def merge_stories(session: AsyncSession, keep_id: int, absorb_id: int) -> dict:
    if keep_id == absorb_id:
        raise MergeError("cannot merge a story into itself")
    keep = await session.get(Story, keep_id)
    absorb = await session.get(Story, absorb_id)
    if keep is None or absorb is None:
        raise MergeError("story not found")
    if keep.status in NON_MERGABLE_STATUSES or absorb.status in NON_MERGABLE_STATUSES:
        raise MergeError(f"cannot merge story in status '{absorb.status}'")

    keep_links = (
        await session.execute(select(StorySource).where(StorySource.story_id == keep.id))
    ).scalars().all()
    absorb_links = (
        await session.execute(select(StorySource).where(StorySource.story_id == absorb.id))
    ).scalars().all()
    keep_source_ids = {link.source_id for link in keep_links}
    keep_has_primary = any(link.relationship_note == "primary" for link in keep_links)

    moved = 0
    demoted = False
    for link in absorb_links:
        if link.source_id in keep_source_ids:
            await session.delete(link)
            continue
        note = link.relationship_note
        relevance = link.relevance_score
        if note == "primary" and keep_has_primary:
            note = "secondary"
            relevance = min(relevance or 0.9, 0.85)
            demoted = True
        session.add(
            StorySource(
                story_id=keep.id,
                source_id=link.source_id,
                relationship_note=note,
                relevance_score=relevance,
            )
        )
        moved += 1
        await session.delete(link)

    absorbed_url = absorb.url
    absorb.url = None
    absorb.status = "MERGED"
    absorb.merged_into_id = keep.id
    if not keep.image_url and absorb.image_url:
        keep.image_url = absorb.image_url
    if len(absorb.summary or "") > len(keep.summary or ""):
        keep.summary = absorb.summary

    session.add(
        AuditLog(
            action="story_merged",
            entity_type="story",
            entity_id=str(absorb.id),
            previous_value={
                "title": absorb.title,
                "url": absorbed_url,
                "summary": absorb.summary,
                "status": absorb.status,
            },
            new_value={
                "merged_into_id": keep.id,
                "keep_title": keep.title,
                "moved_links": moved,
                "demoted_primary": demoted,
            },
        )
    )
    await session.commit()

    return {
        "keep_id": keep.id,
        "keep_title": keep.title,
        "absorbed_id": absorb.id,
        "absorbed_title": absorb.title,
        "moved_links": moved,
        "demoted_primary": demoted,
    }


async def pick_keep(session: AsyncSession, stories: list[Story]) -> Story:
    best: Story | None = None
    best_links = -1
    best_discovered = None
    for story in stories:
        count = await session.scalar(
            select(func.count()).select_from(StorySource).where(StorySource.story_id == story.id)
        )
        links = count or 0
        discovered = story.discovered_at
        if links > best_links:
            best, best_links, best_discovered = story, links, discovered
        elif links == best_links:
            if best_discovered is None or (discovered is not None and discovered < best_discovered):
                best, best_discovered = story, discovered
    return best or stories[0]


async def merge_cluster(session: AsyncSession, stories: list[Story]) -> dict | None:
    if len(stories) < 2:
        return None
    keep = await pick_keep(session, stories)
    others = [s for s in stories if s.id != keep.id]
    report: dict = {"keep_id": keep.id, "absorbed_ids": [], "moved_links": 0}
    for absorb in others:
        result = await merge_stories(session, keep.id, absorb.id)
        report["absorbed_ids"].append(absorb.id)
        report["moved_links"] += result["moved_links"]
    return report


async def dedupe_all(session: AsyncSession, limit: int = 5000) -> list[dict]:
    stories = (
        await session.execute(
            select(Story).where(Story.status != "MERGED").order_by(Story.discovered_at).limit(limit)
        )
    ).scalars().all()

    parent = {s.id: s.id for s in stories}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    window = timedelta(days=DUPLICATE_WINDOW_DAYS)
    left = 0
    for right, story_b in enumerate(stories):
        discovered_b = story_b.discovered_at
        while (
            left < right
            and stories[left].discovered_at is not None
            and discovered_b - stories[left].discovered_at > window
        ):
            left += 1
        for story_a in stories[left:right]:
            if is_same_event(
                story_a.title, story_a.summary, story_b.title, story_b.summary
            ):
                parent[find(story_b.id)] = find(story_a.id)

    groups: dict[int, list[Story]] = {}
    for story in stories:
        groups.setdefault(find(story.id), []).append(story)

    reports: list[dict] = []
    for members in groups.values():
        report = await merge_cluster(session, members)
        if report is not None:
            reports.append(report)
    return reports