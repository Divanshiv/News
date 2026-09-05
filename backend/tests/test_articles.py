async def _create_story(client, title="Pipeline story"):
    return (await client.post("/api/v1/stories", json={"title": title})).json()


async def test_create_article_for_story(client):
    story = await _create_story(client)
    response = await client.post(
        "/api/v1/articles",
        json={"story_id": story["id"], "headline": "The headline"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["headline"] == "The headline"
    assert data["status"] == "DRAFT"
    assert data["story_id"] == story["id"]
    assert data["published_at"] is None


async def test_create_article_for_missing_story_404(client):
    response = await client.post(
        "/api/v1/articles", json={"story_id": 9999, "headline": "Ghost"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Story not found"


async def test_create_article_as_published_sets_timestamp(client):
    story = await _create_story(client)
    response = await client.post(
        "/api/v1/articles",
        json={"story_id": story["id"], "headline": "Already live", "status": "PUBLISHED"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PUBLISHED"
    assert data["published_at"] is not None


async def test_list_articles_filter_by_story(client):
    story_one = await _create_story(client, "Story one")
    story_two = await _create_story(client, "Story two")
    await client.post("/api/v1/articles", json={"story_id": story_one["id"], "headline": "A1"})
    await client.post("/api/v1/articles", json={"story_id": story_two["id"], "headline": "A2"})
    response = await client.get(f"/api/v1/articles?story_id={story_one['id']}")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["headline"] == "A1"


async def test_update_article_status(client):
    story = await _create_story(client)
    article = (
        await client.post(
            "/api/v1/articles", json={"story_id": story["id"], "headline": "Draft headline"}
        )
    ).json()
    response = await client.patch(
        f"/api/v1/articles/{article['id']}",
        json={"headline": "Final headline", "status": "REVIEW"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["headline"] == "Final headline"
    assert data["status"] == "REVIEW"


async def test_update_article_to_published_sets_timestamp(client):
    story = await _create_story(client)
    article = (
        await client.post(
            "/api/v1/articles", json={"story_id": story["id"], "headline": "About to go live"}
        )
    ).json()
    response = await client.patch(
        f"/api/v1/articles/{article['id']}", json={"status": "PUBLISHED"}
    )
    data = response.json()
    assert data["published_at"] is not None


async def test_delete_article(client):
    story = await _create_story(client)
    article = (
        await client.post(
            "/api/v1/articles", json={"story_id": story["id"], "headline": "Doomed"}
        )
    ).json()
    response = await client.delete(f"/api/v1/articles/{article['id']}")
    assert response.status_code == 204
    assert (await client.get(f"/api/v1/articles/{article['id']}")).status_code == 404