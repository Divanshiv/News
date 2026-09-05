async def test_create_source(client):
    payload = {
        "name": "Test Wire",
        "url": "https://example.com",
        "rss_url": "https://example.com/rss",
        "source_type": "news",
        "category": "Technology",
        "reliability_score": 0.7,
    }
    response = await client.post("/api/v1/sources", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Wire"
    assert data["category"] == "Technology"
    assert data["reliability_score"] == 0.7
    assert data["active"] is True
    assert data["id"] > 0


async def test_create_source_defaults(client):
    response = await client.post(
        "/api/v1/sources", json={"name": "Minimal Source", "url": "https://example.org"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_type"] == "news"
    assert data["reliability_score"] == 0.0


async def test_list_sources_paginated(client):
    for index in range(3):
        await client.post(
            "/api/v1/sources",
            json={"name": f"Source {index}", "url": f"https://example.com/{index}"},
        )
    response = await client.get("/api/v1/sources?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    filtered = await client.get("/api/v1/sources?category=Technology")
    assert filtered.json()["total"] == 0


async def test_list_sources_filtered_by_category(client):
    await client.post(
        "/api/v1/sources",
        json={"name": "AI Wire", "url": "https://example.com", "category": "AI"},
    )
    await client.post(
        "/api/v1/sources",
        json={"name": "Space Wire", "url": "https://example.org", "category": "Space"},
    )
    response = await client.get("/api/v1/sources?category=AI")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "AI Wire"


async def test_get_source(client):
    created = (
        await client.post(
            "/api/v1/sources", json={"name": "Getter", "url": "https://example.com"}
        )
    ).json()
    response = await client.get(f"/api/v1/sources/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Getter"


async def test_get_source_missing(client):
    response = await client.get("/api/v1/sources/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found"


async def test_update_source(client):
    created = (
        await client.post(
            "/api/v1/sources", json={"name": "Old Name", "url": "https://example.com"}
        )
    ).json()
    response = await client.patch(
        f"/api/v1/sources/{created['id']}",
        json={"name": "New Name", "active": False, "reliability_score": 0.9},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["active"] is False
    assert data["reliability_score"] == 0.9


async def test_delete_source(client):
    created = (
        await client.post(
            "/api/v1/sources", json={"name": "Doomed", "url": "https://example.com"}
        )
    ).json()
    response = await client.delete(f"/api/v1/sources/{created['id']}")
    assert response.status_code == 204
    assert (await client.get(f"/api/v1/sources/{created['id']}")).status_code == 404