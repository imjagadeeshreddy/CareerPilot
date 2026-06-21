from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes.analysis import router as analysis_router
from app.api.routes.optimization import router as optimization_router
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title=settings.app_name,
    description="AI Career Intelligence Platform — Resume matching, skill gaps, and optimization.",
    version="0.2.0",
)

app.include_router(analysis_router)
app.include_router(optimization_router)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"app_name": settings.app_name},
        )
