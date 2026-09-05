"""Tests for the jobs-history and service-config endpoints."""

from app.workers.jobs import job_runner


async def test_jobs_endpoint_empty(client):
    response = await client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert response.json() == []


async def test_jobs_endpoint_reflects_submitted_jobs(client):
    job_runner.submit("run_scout")
    response = await client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["job_name"] == "run_scout"
    assert data[0]["status"] in {"QUEUED", "RUNNING", "COMPLETED", "FAILED"}
    assert data[0]["job_id"]


async def test_jobs_endpoint_limit(client):
    job_runner.submit("run_scout")
    job_runner.submit("dedupe_all")
    response = await client.get("/api/v1/jobs?limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_meta_config_endpoint(client):
    response = await client.get("/api/v1/meta/config")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "AI Newsroom Backend"
    assert data["app_version"]
    assert data["environment"]
    assert data["llm_provider"]
