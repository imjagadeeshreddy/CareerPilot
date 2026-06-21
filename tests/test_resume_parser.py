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

JAGADEESH_STYLE_RESUME = """
JAGADEESH REDDY PANDHIKUNTA
jagadeeshpandhikunta@gmail.com +1 (816) 768-1635 in/jagadeeshreddyp

SUMMARY
Google Cloud Platform Data Engineer with four years of experience working with GCP stacks.

SKILLS
Programming Languages: Python, Java, Scala, HTML5, CSS3, JavaScript
Big Data Tools & Frameworks: Apache Spark, Hadoop, Hive, Kafka, Git
Cloud Platforms: Google Cloud Platform, Azure, AWS
Database Technologies: MySQL, Oracle Database, Apache Cassandra
DevOps: CI/CD, Jenkins, Docker, Kubernetes

EXPERIENCE
Data Engineer | WALMART
September 2023 – Present | Bentonville, AR
Optimized Apache Spark jobs achieving 30% reduction in data processing time
Implemented data compression in Cassandra and Cosmos DB
Migrated data pipelines to GCP using BigQuery, Dataproc, and Spark
Reduced data streaming latency by 40% using Apache Kafka and Lenses
Optimized Airflow DAGs with Python code
Conducted Hadoop cluster optimizations

Java Developer | COGNIZANT
January 2019 – December 2021 | Bangalore, India
Developed Java-based web applications using Spring Boot and Hibernate
Designed micro-services architecture contributing to 50% enhancement in scalability
Leveraged AWS services including RDS, DynamoDB, SQS, and Kafka
Developed RESTful APIs with 98% test coverage using JUnit and Mockito
Worked in Agile environments and conducted knowledge-sharing sessions

EDUCATION
Master's Degree, Major in Computer Science, University of Missouri - Kansas City, 2023
Bachelor's Degree, Major in Electronics & Communication Engineering, Lovely Professional University, 2019

CERTIFICATIONS
Oracle Certified Professional: Java SE 11 Developer, Oracle, 2023
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


def test_parse_text_extracts_multiple_jobs(parser):
    result = parser.parse_text(SAMPLE_RESUME)
    assert len(result.experience) >= 2
    companies = {entry.company.lower() for entry in result.experience}
    assert "techcorp" in companies
    assert "startupxyz" in companies


def test_parse_text_extracts_education(parser):
    result = parser.parse_text(SAMPLE_RESUME)
    assert len(result.education) >= 1


def test_jagadeesh_resume_extracts_both_jobs(parser):
    result = parser.parse_text(JAGADEESH_STYLE_RESUME)
    assert len(result.experience) == 2
    companies = {entry.company.upper() for entry in result.experience}
    assert "WALMART" in companies
    assert "COGNIZANT" in companies


def test_jagadeesh_resume_preserves_all_bullets(parser):
    result = parser.parse_text(JAGADEESH_STYLE_RESUME)
    walmart = next(e for e in result.experience if e.company.upper() == "WALMART")
    cognizant = next(e for e in result.experience if e.company.upper() == "COGNIZANT")
    assert "Spark" in walmart.description
    assert "Kafka" in walmart.description
    assert "Spring Boot" in cognizant.description
    assert "RESTful" in cognizant.description


def test_jagadeesh_resume_extracts_contact(parser):
    result = parser.parse_text(JAGADEESH_STYLE_RESUME)
    assert "Jagadeesh" in result.name
    assert "jagadeeshpandhikunta@gmail.com" in result.email
    assert result.linkedin


def test_jagadeesh_resume_extracts_certifications(parser):
    result = parser.parse_text(JAGADEESH_STYLE_RESUME)
    assert len(result.certifications) >= 1
    assert any("Oracle" in cert for cert in result.certifications)


def test_jagadeesh_resume_extracts_skills_section(parser):
    result = parser.parse_text(JAGADEESH_STYLE_RESUME)
    assert "Programming Languages" in result.skills_section
    assert "Apache Spark" in result.skills_section


def test_unsupported_file_type(parser):
    with pytest.raises(ValueError, match="Unsupported file type"):
        parser.parse_file("resume.xyz", b"content")
