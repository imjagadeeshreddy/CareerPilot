# CareerPilot

AI-powered Career Intelligence Platform — evaluate resumes against job descriptions, identify skill gaps, and optimize for success.

## MVP V2 (Current)

- Interactive gap questions (AI-powered when OpenAI key is set)
- Resume rewriting using **verified user answers only**
- ATS score and keyword analysis
- Download optimized resume (PDF / DOCX)

### V2 Flow

1. **Analyze** — Upload resume + job description (V1)
2. **Gap Questions** — Answer questions about missing skills
3. **Optimize & Download** — Get ATS score + download tailored resume

> Rule: We never invent experience. Only verified user responses are included.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Pydantic, Uvicorn |
| Frontend | HTML, CSS, Jinja2 |
| Resume parsing | pdfplumber, python-docx |
| Database | SQLite (Phase 2) |
| AI (V2+) | OpenAI API |

## Quick Start

### 1. Clone & install

```bash
cd CareerPilot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Add OPENAI_API_KEY when V2 AI features are enabled
```

### 3. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

### 4. Run tests

```bash
pytest -v
```

## API

### `POST /api/analyze`

Upload a resume and job description for analysis.

**Form fields:**
- `resume` — PDF, DOCX, or TXT file
- `job_description` — plain text (min 20 chars)

**Response:** JSON with parsed resume, parsed job, and match result.

### `GET /api/health`

Health check endpoint.

### `POST /api/gap-questions`

Generate targeted follow-up questions for skill gaps.

**Body:** `{ resume, job, match }` from analyze response.

### `POST /api/optimize`

Rewrite resume using verified user answers. Returns optimized resume + ATS score.

**Body:** `{ resume, job, match, answers[] }`

### `POST /api/download`

Download optimized resume as PDF or DOCX.

**Body:** `{ optimized_resume, format: "pdf"|"docx", filename }`

## Project Structure

```
app/
  api/routes/       # FastAPI route handlers
  services/         # Resume parser, job parser, match engine
  models/           # Pydantic schemas
  prompts/          # AI prompt templates (V2+)
  utils/            # Skill extraction utilities
frontend/
  templates/        # Jinja2 HTML templates
  static/           # CSS & JS
tests/
```

## Roadmap

| Version | Features |
|---------|----------|
| V1 ✅ | Upload, parse, match score, skill gaps, suggestions |
| V2 ✅ | Gap questions, resume rewriting, ATS score, PDF/DOCX download |
| V3 | Multi-job tailoring, interview prep, cover letters, version management |

## Docker

```bash
docker build -t careerpilot .
docker run -p 8000:8000 --env-file .env careerpilot
```

## Deploy to Render

CareerPilot ships with a [Render Blueprint](https://render.com/docs/blueprint-spec) (`render.yaml`).

### Prerequisites

1. Push this repo to GitHub (`.env` is gitignored — never commit secrets).
2. Create a [Render](https://render.com) account.

### Option A — Blueprint (recommended)

1. In Render Dashboard → **New** → **Blueprint**
2. Connect `imjagadeeshreddy/CareerPilot`
3. Render reads `render.yaml` and creates the `careerpilot` web service
4. When prompted, set **`OPENAI_API_KEY`** (mark as secret / sync: false)
5. Click **Apply** — first deploy takes ~5–10 minutes on the free tier

### Option B — Manual web service

1. **New** → **Web Service** → connect GitHub repo
2. **Runtime:** Docker
3. **Health check path:** `/api/health`
4. **Environment variables:**

| Key | Value |
|-----|-------|
| `OPENAI_API_KEY` | Your secret key (set in Render dashboard only) |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `APP_ENV` | `production` |

5. Deploy

### After deploy

- Open your Render URL (e.g. `https://careerpilot.onrender.com`)
- Hit `/api/health` — should return `{"status":"ok"}`
- Run through the 3-step flow: Analyze → Gap Questions → Optimize & Download

### Local secrets

```bash
cp .env.example .env
# Edit .env — never commit this file
```

Render uses dashboard env vars in production; `.env` is for local development only.

## License

Private — Jagadeesh Reddy
