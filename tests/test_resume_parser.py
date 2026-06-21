import pytest

from app.services.resume_parser import ResumeParserService


@pytest.fixture
def parser():
    return ResumeParserService()


SAMPLE_RESUME = """
John Doe
Software Engineer

SUMMARY
Experienced Python developer with 5 years building web applications using FastAPI, Django, and React.

EXPERIENCE
Senior Software Engineer | TechCorp | 2020 - Present
- Built REST APIs with FastAPI and PostgreSQL
- Deployed services on AWS using Docker and Kubernetes

Software Engineer | StartupXYZ | 2018 - 2020
- Developed React frontend applications
- Implemented CI/CD pipelines with Jenkins

SKILLS
Python, FastAPI, Django, React, PostgreSQL, AWS, Docker, Kubernetes, Git

EDUCATION
B.S. Computer Science, State University, 2018
"""


def test_parse_text_extracts_skills(parser):
    result = parser.parse_text(SAMPLE_RESUME)
    assert "python" in result.skills
    assert "fastapi" in result.skills
    assert "react" in result.skills
    assert "aws" in result.skills


def test_parse_text_extracts_summary(parser):
    result = parser.parse_text(SAMPLE_RESUME)
    assert "python" in result.summary.lower()


def test_parse_text_extracts_experience(parser):
    result = parser.parse_text(SAMPLE_RESUME)
    assert len(result.experience) >= 1


def test_parse_text_extracts_education(parser):
    result = parser.parse_text(SAMPLE_RESUME)
    assert len(result.education) >= 1


def test_unsupported_file_type(parser):
    with pytest.raises(ValueError, match="Unsupported file type"):
        parser.parse_file("resume.xyz", b"content")
