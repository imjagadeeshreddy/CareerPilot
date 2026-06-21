import pytest

from app.models.schemas import ExperienceEntry, JobDescription, MatchResult, OptimizedResume, ParsedResume, UserAnswer
from app.services.resume_optimizer import ResumeOptimizationEngine


@pytest.fixture
def engine():
    return ResumeOptimizationEngine()


@pytest.fixture
def sample_resume():
    return ParsedResume(
        summary="Backend developer with Python experience.",
        skills=["python", "fastapi"],
        experience=[
            ExperienceEntry(
                title="Software Engineer",
                company="TechCorp",
                duration="2020 - Present",
                description="Built REST APIs",
            ),
            ExperienceEntry(
                title="Junior Developer",
                company="OldCorp",
                duration="2018 - 2020",
                description="Maintained legacy systems",
            ),
        ],
        education=["B.S. Computer Science"],
        certifications=["AWS Certified Developer"],
        name="John Doe",
        email="john@example.com",
    )


@pytest.fixture
def sample_job():
    return JobDescription(
        title="Senior Python Developer",
        required_skills=["python", "fastapi", "kubernetes"],
        preferred_skills=["react"],
    )


@pytest.fixture
def sample_match():
    return MatchResult(
        score=60.0,
        missing_required=["kubernetes"],
        missing_preferred=["react"],
    )


def test_verified_answers_add_skills(engine, sample_resume, sample_job, sample_match):
    answers = [
        UserAnswer(
            question_id="q1",
            skill="kubernetes",
            answer="Managed K8s clusters for 3 microservices at TechCorp, reducing deploy time by 40%.",
        )
    ]

    optimized, _ = engine.optimize(sample_resume, sample_job, sample_match, answers)

    assert "kubernetes" in optimized.skills
    assert optimized.full_text
    assert "kubernetes" in optimized.full_text.lower()


def test_negative_answers_not_included(engine, sample_resume, sample_job, sample_match):
    answers = [
        UserAnswer(question_id="q1", skill="kubernetes", answer="No experience with kubernetes"),
    ]

    optimized, _ = engine.optimize(sample_resume, sample_job, sample_match, answers)

    assert "kubernetes" not in optimized.skills


def test_match_score_improves_with_verified_skills(engine, sample_resume, sample_job, sample_match):
    answers = [
        UserAnswer(
            question_id="q1",
            skill="kubernetes",
            answer="Deployed and managed Kubernetes clusters for production workloads at TechCorp.",
        )
    ]

    optimized, _ = engine.optimize(sample_resume, sample_job, sample_match, answers)
    score_after = engine.compute_match_after(optimized, sample_job)

    assert score_after >= sample_match.score


def test_preserves_all_original_experience(engine, sample_resume, sample_job, sample_match):
    optimized, _ = engine.optimize(sample_resume, sample_job, sample_match, [])
    assert len(optimized.experience) == 2
    companies = {entry.company for entry in optimized.experience}
    assert "TechCorp" in companies
    assert "OldCorp" in companies


def test_preserves_contact_and_certifications(engine, sample_resume, sample_job, sample_match):
    optimized, _ = engine.optimize(sample_resume, sample_job, sample_match, [])
    assert optimized.name == "John Doe"
    assert optimized.email == "john@example.com"
    assert len(optimized.certifications) == 1


def test_merge_restores_missing_ai_jobs(engine, sample_resume, sample_job, sample_match):
    partial = OptimizedResume(
        summary="Updated summary",
        skills=["python"],
        experience=[
            ExperienceEntry(
                title="Software Engineer",
                company="TechCorp",
                duration="2020 - Present",
                description="Rewritten bullet",
            )
        ],
        education=["B.S. Computer Science"],
    )
    merged = engine._merge_with_original(partial, sample_resume, [])
    assert len(merged.experience) == 2
    assert any(entry.company == "OldCorp" for entry in merged.experience)
