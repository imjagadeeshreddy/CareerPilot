import pytest

from app.models.schemas import ExperienceEntry, JobDescription, OptimizedResume
from app.services.ats_engine import ATSEngine


@pytest.fixture
def engine():
    return ATSEngine()


@pytest.fixture
def optimized_resume():
    return OptimizedResume(
        summary="Senior Python developer with FastAPI and Kubernetes experience.",
        skills=["python", "fastapi", "kubernetes", "postgresql", "aws"],
        experience=[
            ExperienceEntry(
                title="Software Engineer",
                company="TechCorp",
                duration="2020 - Present",
                description="Built REST APIs with FastAPI\nManaged Kubernetes deployments",
            )
        ],
        education=["B.S. Computer Science, State University"],
        full_text=(
            "Senior Python developer with FastAPI and Kubernetes experience.\n"
            "SKILLS: python, fastapi, kubernetes, postgresql, aws\n"
            "Software Engineer | TechCorp | 2020 - Present"
        ),
    )


@pytest.fixture
def job():
    return JobDescription(
        title="Senior Python Developer",
        required_skills=["python", "fastapi", "kubernetes", "postgresql"],
        preferred_skills=["react", "machine learning"],
        responsibilities=["Build REST APIs", "Deploy on AWS"],
    )


def test_ats_score_in_valid_range(engine, optimized_resume, job):
    result = engine.analyze(optimized_resume, job)
    assert 0 <= result.score <= 100


def test_matched_keywords_detected(engine, optimized_resume, job):
    result = engine.analyze(optimized_resume, job)
    assert "python" in result.matched_keywords
    assert "fastapi" in result.matched_keywords


def test_missing_keywords_detected(engine, optimized_resume, job):
    result = engine.analyze(optimized_resume, job)
    assert "react" in result.missing_keywords or "machine learning" in result.missing_keywords


def test_recommendations_generated(engine, optimized_resume, job):
    result = engine.analyze(optimized_resume, job)
    assert len(result.recommendations) >= 1
