import pytest

from app.models.schemas import ExperienceEntry, OptimizedResume
from app.services.resume_generator import ResumeGeneratorService


@pytest.fixture
def generator():
    return ResumeGeneratorService()


@pytest.fixture
def sample_resume():
    return OptimizedResume(
        summary="Experienced Python developer.",
        skills=["python", "fastapi", "aws"],
        experience=[
            ExperienceEntry(
                title="Software Engineer",
                company="TechCorp",
                duration="2020 - Present",
                description="• Built REST APIs\n• Deployed on AWS",
            )
        ],
        education=["B.S. Computer Science"],
        full_text="Experienced Python developer.",
    )


def test_generate_pdf(generator, sample_resume):
    content, media_type, ext = generator.generate(sample_resume, "pdf")
    assert ext == "pdf"
    assert media_type == "application/pdf"
    assert content[:4] == b"%PDF"


def test_generate_docx(generator, sample_resume):
    content, media_type, ext = generator.generate(sample_resume, "docx")
    assert ext == "docx"
    assert "wordprocessingml" in media_type
    assert content[:2] == b"PK"
