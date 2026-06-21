from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import AnalysisResponse
from app.services.job_parser import JobParserService
from app.services.match_engine import MatchEngine
from app.services.resume_parser import ResumeParserService

router = APIRouter(prefix="/api", tags=["analysis"])

resume_parser = ResumeParserService()
job_parser = JobParserService()
match_engine = MatchEngine()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    resume: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    job_description: str = Form(..., min_length=20, description="Job description text"),
) -> AnalysisResponse:
    if not resume.filename:
        raise HTTPException(status_code=400, detail="Resume filename is required.")

    content = await resume.read()
    if not content:
        raise HTTPException(status_code=400, detail="Resume file is empty.")

    try:
        parsed_resume = resume_parser.parse_file(resume.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse resume: {exc}") from exc

    parsed_job = job_parser.parse_text(job_description)
    match_result = match_engine.analyze(parsed_resume, parsed_job)

    return AnalysisResponse(
        resume=parsed_resume,
        job=parsed_job,
        match=match_result,
    )


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "CareerPilot API"}
