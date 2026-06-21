import pytest

from app.models.schemas import JobDescription, MatchResult, ParsedResume
from app.services.gap_discovery import GapDiscoveryEngine


@pytest.fixture
def engine():
    return GapDiscoveryEngine()


@pytest.fixture
def match_with_gaps():
    return MatchResult(
        score=55.0,
        matching_skills=["python", "fastapi"],
        missing_required=["kubernetes", "redis"],
        missing_preferred=["react"],
        skill_gaps=[],
    )


def test_fallback_generates_questions_for_missing_skills(engine, match_with_gaps):
    resume = ParsedResume(skills=["python"])
    job = JobDescription(required_skills=["python", "kubernetes"], preferred_skills=["react"])

    result = engine.generate(resume, job, match_with_gaps)

    assert result.ai_powered is False
    assert len(result.questions) >= 2
    skills = {q.skill for q in result.questions}
    assert "kubernetes" in skills


def test_questions_reference_skills(engine, match_with_gaps):
    resume = ParsedResume()
    job = JobDescription()

    result = engine.generate(resume, job, match_with_gaps)

    for question in result.questions:
        assert question.id
        assert question.question
        assert question.skill


def test_no_gaps_returns_empty(engine):
    match = MatchResult(
        score=95.0,
        matching_skills=["python"],
        missing_required=[],
        missing_preferred=[],
    )
    result = engine.generate(ParsedResume(), JobDescription(), match)
    assert result.questions == []
