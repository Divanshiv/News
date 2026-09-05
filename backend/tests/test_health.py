from app.core.config import get_settings


async def test_root_endpoint(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ai-newsroom-backend"
    assert data["health"] == "/api/v1/health"


async def test_health_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ai-newsroom-backend"
    assert data["status"] in {"ok", "degraded"}
    assert data["database"] in {"connected", "unavailable"}
    assert data["version"]
    assert data["timestamp"]


async def test_settings_defaults():
    settings = get_settings()
    assert settings.app_name == "AI Newsroom Backend"
    assert settings.app_version == "0.1.0"
    assert settings.api_v1_prefix == "/api/v1"
    assert "http://localhost:3000" in settings.cors_origins