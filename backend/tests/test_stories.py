from app.core.database import async_session_factory
from app.models.story import StorySource


async def test_create_story_generates_slug(client):
    response = await client.post(
        "/api/v1/stories",
        json={"title": "OpenAI announces new reasoning model", "category": "AI"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "openai-announces-new-reasoning-model"
    assert data["status"] == "DISCOVERED"
    assert data["importance_score"] is None


async def test_create_story_duplicate_title_gets_unique_slug(client):
    first = (await client.post("/api/v1/stories", json={"title": "Chip shortage worsens"})).json()
    second = (await client.post("/api/v1/stories", json={"title": "Chip shortage worsens"})).json()
    assert first["slug"] == "chip-shortage-worsens"
    assert second["slug"] == "chip-shortage-worsens-2"


async def test_create_story_links_source(client):
    source = (
        await client.post(
            "/api/v1/sources", json={"name": "Wired", "url": "https://example.com"}
        )
    ).json()
    response = await client.post(
        "/api/v1/stories",
        json={"title": "Story from wire", "source_id": source["id"]},
    )
    assert response.status_code == 201
    async with async_session_factory() as session:
        links = (await session.execute(StorySource.__table__.select())).all()
    assert len(links) == 1
    assert links[0].source_id == source["id"]


async def test_create_story_with_unknown_source_404(client):
    response = await client.post(
        "/api/v1/stories", json={"title": "Ghost link", "source_id": 9999}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found"


async def test_list_stories_filter_by_status(client):
    await client.post("/api/v1/stories", json={"title": "One", "status": "DISCOVERED"})
    await client.post("/api/v1/stories", json={"title": "Two", "status": "RESEARCHING"})
    response = await client.get("/api/v1/stories?status=RESEARCHING")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Two"


async def test_get_story_missing(client):
    response = await client.get("/api/v1/stories/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Story not found"


async def test_update_story_regenerates_slug_on_title_change(client):
    created = (
        await client.post("/api/v1/stories", json={"title": "Original headline"})
    ).json()
    response = await client.patch(
        f"/api/v1/stories/{created['id']}",
        json={"title": "Rewritten headline", "status": "RESEARCHING"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Rewritten headline"
    assert data["slug"] == "rewritten-headline"
    assert data["status"] == "RESEARCHING"


async def test_delete_story(client):
    created = (await client.post("/api/v1/stories", json={"title": "Doomed story"})).json()
    response = await client.delete(f"/api/v1/stories/{created['id']}")
    assert response.status_code == 204
    assert (await client.get(f"/api/v1/stories/{created['id']}")).status_code == 404