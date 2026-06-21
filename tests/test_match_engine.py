import pytest

from app.models.schemas import JobDescription, ParsedResume
from app.services.match_engine import MatchEngine


@pytest.fixture
def engine():
    return MatchEngine()


@pytest.fixture
def sample_resume():
    return ParsedResume(
        skills=["python", "fastapi", "postgresql", "aws", "docker", "react"],
        summary="Experienced backend developer",
        experience=[],
    )


@pytest.fixture
def sample_job():
    return JobDescription(
        required_skills=["python", "fastapi", "postgresql", "aws", "kubernetes"],
        preferred_skills=["react", "machine learning"],
        title="Senior Python Developer",
    )


def test_high_match_score(engine, sample_resume, sample_job):
    result = engine.analyze(sample_resume, sample_job)
    assert result.score >= 60
    assert "python" in result.matching_skills
    assert "kubernetes" in result.missing_required


def test_missing_skills_identified(engine, sample_resume, sample_job):
    result = engine.analyze(sample_resume, sample_job)
    assert "kubernetes" in result.missing_required
    assert "machine learning" in result.missing_preferred


def test_improvement_suggestions_generated(engine, sample_resume, sample_job):
    result = engine.analyze(sample_resume, sample_job)
    assert len(result.improvement_suggestions) >= 2


def test_skill_gaps_have_suggestions(engine, sample_resume, sample_job):
    result = engine.analyze(sample_resume, sample_job)
    assert len(result.skill_gaps) >= 1
    assert all(gap.suggestion for gap in result.skill_gaps)


def test_empty_job_skills(engine, sample_resume):
    job = JobDescription(required_skills=[], preferred_skills=[])
    result = engine.analyze(sample_resume, job)
    assert 0 <= result.score <= 100
