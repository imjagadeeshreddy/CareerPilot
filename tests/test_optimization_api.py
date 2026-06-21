import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.schemas import (
    ExperienceEntry,
    JobDescription,
    MatchResult,
    ParsedResume,
    UserAnswer,
)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


SAMPLE_RESUME = ParsedResume(
    summary="Python developer.",
    skills=["python", "fastapi"],
    experience=[ExperienceEntry(title="Engineer", company="Corp", duration="2020-Present", description="Built APIs")],
    education=["B.S. CS"],
)

SAMPLE_JOB = JobDescription(
    title="Python Developer",
    required_skills=["python", "fastapi", "kubernetes"],
    preferred_skills=["react"],
)

SAMPLE_MATCH = MatchResult(
    score=55.0,
    matching_skills=["python", "fastapi"],
    missing_required=["kubernetes"],
    missing_preferred=["react"],
)


@pytest.mark.asyncio
async def test_gap_questions_endpoint(client):
    response = await client.post(
        "/api/gap-questions",
        json={
            "resume": SAMPLE_RESUME.model_dump(),
            "job": SAMPLE_JOB.model_dump(),
            "match": SAMPLE_MATCH.model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert len(data["questions"]) >= 1


@pytest.mark.asyncio
async def test_optimize_endpoint(client):
    response = await client.post(
        "/api/optimize",
        json={
            "resume": SAMPLE_RESUME.model_dump(),
            "job": SAMPLE_JOB.model_dump(),
            "match": SAMPLE_MATCH.model_dump(),
            "answers": [
                UserAnswer(
                    question_id="q1",
                    skill="kubernetes",
                    answer="Managed Kubernetes clusters for microservices at Corp.",
                ).model_dump()
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "optimized_resume" in data
    assert "ats" in data
    assert data["ats"]["score"] >= 0


@pytest.mark.asyncio
async def test_download_pdf_endpoint(client):
    optimize_response = await client.post(
        "/api/optimize",
        json={
            "resume": SAMPLE_RESUME.model_dump(),
            "job": SAMPLE_JOB.model_dump(),
            "match": SAMPLE_MATCH.model_dump(),
            "answers": [],
        },
    )
    optimized = optimize_response.json()

    response = await client.post(
        "/api/download",
        json={
            "optimized_resume": optimized["optimized_resume"],
            "format": "pdf",
            "filename": "test_resume",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_download_docx_endpoint(client):
    optimize_response = await client.post(
        "/api/optimize",
        json={
            "resume": SAMPLE_RESUME.model_dump(),
            "job": SAMPLE_JOB.model_dump(),
            "match": SAMPLE_MATCH.model_dump(),
            "answers": [],
        },
    )
    optimized = optimize_response.json()

    response = await client.post(
        "/api/download",
        json={
            "optimized_resume": optimized["optimized_resume"],
            "format": "docx",
            "filename": "test_resume",
        },
    )
    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
