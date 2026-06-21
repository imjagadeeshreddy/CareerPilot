from pydantic import BaseModel, Field


class ExperienceEntry(BaseModel):
    title: str = ""
    company: str = ""
    duration: str = ""
    description: str = ""


class ParsedResume(BaseModel):
    raw_text: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    summary: str = ""
    education: list[str] = Field(default_factory=list)


class JobDescription(BaseModel):
    raw_text: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    title: str = ""
    responsibilities: list[str] = Field(default_factory=list)


class SkillGap(BaseModel):
    skill: str
    importance: str = "required"
    suggestion: str = ""


class MatchResult(BaseModel):
    score: float = Field(ge=0, le=100)
    matching_skills: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    job_description: str


class AnalysisResponse(BaseModel):
    resume: ParsedResume
    job: JobDescription
    match: MatchResult


# --- V2 Models ---


class GapQuestion(BaseModel):
    id: str
    skill: str
    question: str
    importance: str = "required"


class GapQuestionsRequest(BaseModel):
    resume: ParsedResume
    job: JobDescription
    match: MatchResult


class GapQuestionsResponse(BaseModel):
    questions: list[GapQuestion] = Field(default_factory=list)
    ai_powered: bool = False


class UserAnswer(BaseModel):
    question_id: str
    skill: str = ""
    answer: str = ""


class OptimizeRequest(BaseModel):
    resume: ParsedResume
    job: JobDescription
    match: MatchResult
    answers: list[UserAnswer] = Field(default_factory=list)


class OptimizedResume(BaseModel):
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    full_text: str = ""


class ATSResult(BaseModel):
    score: float = Field(ge=0, le=100)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class OptimizeResponse(BaseModel):
    optimized_resume: OptimizedResume
    ats: ATSResult
    match_score_before: float
    match_score_after: float
    ai_powered: bool = False


class DownloadRequest(BaseModel):
    optimized_resume: OptimizedResume
    format: str = Field(default="pdf", pattern="^(pdf|docx)$")
    filename: str = "optimized_resume"
