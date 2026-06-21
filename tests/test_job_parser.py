import pytest

from app.services.job_parser import JobParserService


@pytest.fixture
def parser():
    return JobParserService()


SAMPLE_JOB = """
Senior Python Developer

We are looking for a Senior Python Developer to join our team.

Responsibilities:
- Design and build REST APIs using FastAPI
- Work with PostgreSQL and Redis
- Deploy applications on AWS

Required Skills:
- Python
- FastAPI
- PostgreSQL
- AWS
- Docker

Preferred Skills:
- Kubernetes
- React
- Machine Learning
"""


def test_parse_text_extracts_required_skills(parser):
    result = parser.parse_text(SAMPLE_JOB)
    assert "python" in result.required_skills
    assert "fastapi" in result.required_skills
    assert "postgresql" in result.required_skills


def test_parse_text_extracts_preferred_skills(parser):
    result = parser.parse_text(SAMPLE_JOB)
    assert "kubernetes" in result.preferred_skills
    assert "react" in result.preferred_skills


def test_parse_text_extracts_title(parser):
    result = parser.parse_text(SAMPLE_JOB)
    assert "python" in result.title.lower()


def test_parse_text_extracts_responsibilities(parser):
    result = parser.parse_text(SAMPLE_JOB)
    assert len(result.responsibilities) >= 2
