import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_home_page(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "CareerPilot" in response.text


@pytest.mark.asyncio
async def test_analyze_endpoint(client):
    resume_content = b"""
John Doe - Python Developer
Skills: Python, FastAPI, PostgreSQL, AWS, Docker
Experience: Built APIs at TechCorp using FastAPI and PostgreSQL.
"""
    job_description = """
Senior Python Developer
Required: Python, FastAPI, PostgreSQL, AWS, Kubernetes
Preferred: React, Machine Learning
"""

    response = await client.post(
        "/api/analyze",
        files={"resume": ("resume.txt", resume_content, "text/plain")},
        data={"job_description": job_description},
    )

    assert response.status_code == 200
    data = response.json()
    assert "match" in data
    assert "score" in data["match"]
    assert data["match"]["score"] >= 0
