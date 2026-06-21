from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models.schemas import (
    DownloadRequest,
    GapQuestionsRequest,
    GapQuestionsResponse,
    OptimizeRequest,
    OptimizeResponse,
)
from app.services.ats_engine import ATSEngine
from app.services.gap_discovery import GapDiscoveryEngine
from app.services.resume_generator import ResumeGeneratorService
from app.services.resume_optimizer import ResumeOptimizationEngine

router = APIRouter(prefix="/api", tags=["optimization"])

gap_engine = GapDiscoveryEngine()
optimizer = ResumeOptimizationEngine()
ats_engine = ATSEngine()
generator = ResumeGeneratorService()


@router.post("/gap-questions", response_model=GapQuestionsResponse)
async def get_gap_questions(payload: GapQuestionsRequest) -> GapQuestionsResponse:
    if not payload.match.missing_required and not payload.match.missing_preferred:
        return GapQuestionsResponse(questions=[], ai_powered=False)

    return gap_engine.generate(payload.resume, payload.job, payload.match)


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(payload: OptimizeRequest) -> OptimizeResponse:
    optimized, ai_powered = optimizer.optimize(
        resume=payload.resume,
        job=payload.job,
        match=payload.match,
        answers=payload.answers,
    )

    ats_result = ats_engine.analyze(optimized, payload.job)
    score_after = optimizer.compute_match_after(optimized, payload.job)

    return OptimizeResponse(
        optimized_resume=optimized,
        ats=ats_result,
        match_score_before=payload.match.score,
        match_score_after=score_after,
        ai_powered=ai_powered,
    )


@router.post("/download")
async def download_resume(payload: DownloadRequest) -> Response:
    fmt = payload.format.lower()
    if fmt not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'docx'.")

    try:
        content, media_type, extension = generator.generate(payload.optimized_resume, fmt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate resume: {exc}") from exc

    filename = f"{payload.filename}.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
