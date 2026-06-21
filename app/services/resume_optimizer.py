import json
import re

from app.models.schemas import (
    ExperienceEntry,
    JobDescription,
    MatchResult,
    OptimizedResume,
    ParsedResume,
    UserAnswer,
)
from app.prompts.resume_optimization import SYSTEM_PROMPT
from app.services.ai_client import AIClient
from app.services.match_engine import MatchEngine
from app.utils.skills import extract_skills_from_text, normalize_skill


class ResumeOptimizationEngine:
    """Rewrite resume sections using only verified user information."""

    NEGATIVE_PATTERNS = re.compile(
        r"^(no|none|n/a|na|not applicable|don't|dont|never|no experience|nothing)\b",
        re.IGNORECASE,
    )

    def __init__(self, ai_client: AIClient | None = None) -> None:
        self.ai = ai_client or AIClient()
        self.match_engine = MatchEngine()

    def optimize(
        self,
        resume: ParsedResume,
        job: JobDescription,
        match: MatchResult,
        answers: list[UserAnswer],
    ) -> tuple[OptimizedResume, bool]:
        verified = self._filter_verified_answers(answers)
        ai_result = self._optimize_with_ai(resume, job, match, verified)
        if ai_result:
            return ai_result, True

        return self._optimize_fallback(resume, job, verified), False

    def compute_match_after(
        self,
        optimized: OptimizedResume,
        job: JobDescription,
    ) -> float:
        synthetic = ParsedResume(
            raw_text=optimized.full_text,
            skills=optimized.skills,
            experience=optimized.experience,
            summary=optimized.summary,
            education=optimized.education,
        )
        return self.match_engine.analyze(synthetic, job).score

    def _filter_verified_answers(self, answers: list[UserAnswer]) -> list[UserAnswer]:
        verified: list[UserAnswer] = []
        for answer in answers:
            text = answer.answer.strip()
            if len(text) < 10:
                continue
            if self.NEGATIVE_PATTERNS.match(text):
                continue
            verified.append(answer)
        return verified

    def _optimize_with_ai(
        self,
        resume: ParsedResume,
        job: JobDescription,
        match: MatchResult,
        verified_answers: list[UserAnswer],
    ) -> OptimizedResume | None:
        if not self.ai.is_available:
            return None

        user_prompt = json.dumps(
            {
                "original_resume": {
                    "summary": resume.summary,
                    "skills": resume.skills,
                    "experience": [e.model_dump() for e in resume.experience],
                    "education": resume.education,
                },
                "job": {
                    "title": job.title,
                    "required_skills": job.required_skills,
                    "preferred_skills": job.preferred_skills,
                    "responsibilities": job.responsibilities[:6],
                },
                "verified_user_answers": [
                    {"skill": a.skill, "answer": a.answer} for a in verified_answers
                ],
                "missing_skills": match.missing_required + match.missing_preferred,
            },
            indent=2,
        )

        result = self.ai.chat_json(SYSTEM_PROMPT, user_prompt)
        if not result:
            return None

        return self._parse_ai_resume(result, resume)

    def _parse_ai_resume(self, result: dict, original: ParsedResume) -> OptimizedResume | None:
        try:
            experience = [
                ExperienceEntry(
                    title=e.get("title", ""),
                    company=e.get("company", ""),
                    duration=e.get("duration", ""),
                    description=e.get("description", ""),
                )
                for e in result.get("experience", [])
            ]
            if not experience and original.experience:
                experience = original.experience

            optimized = OptimizedResume(
                summary=result.get("summary", original.summary),
                skills=result.get("skills", original.skills),
                experience=experience,
                education=result.get("education", original.education),
            )
            optimized.full_text = self._build_full_text(optimized)
            return optimized
        except (KeyError, TypeError):
            return None

    def _optimize_fallback(
        self,
        resume: ParsedResume,
        job: JobDescription,
        verified_answers: list[UserAnswer],
    ) -> OptimizedResume:
        skills = list(resume.skills)
        experience = [ExperienceEntry(**e.model_dump()) for e in resume.experience]

        for answer in verified_answers:
            skill = normalize_skill(answer.skill) if answer.skill else ""
            if skill and skill not in skills:
                skills.append(skill)

            if experience:
                entry = experience[0]
                bullet = f"• {answer.answer.strip()}"
                entry.description = f"{entry.description}\n{bullet}".strip() if entry.description else bullet
            else:
                experience.append(
                    ExperienceEntry(
                        title="Additional Experience",
                        company="",
                        duration="",
                        description=f"• {answer.answer.strip()}",
                    )
                )

        summary = self._build_summary(resume.summary, job, verified_answers)
        skills = sorted(set(normalize_skill(s) for s in skills))

        optimized = OptimizedResume(
            summary=summary,
            skills=skills,
            experience=experience,
            education=list(resume.education),
        )
        optimized.full_text = self._build_full_text(optimized)
        return optimized

    def _build_summary(
        self,
        original_summary: str,
        job: JobDescription,
        verified_answers: list[UserAnswer],
    ) -> str:
        if original_summary:
            base = original_summary
        else:
            base = f"Professional seeking {job.title or 'a new role'}."

        verified_skills = [normalize_skill(a.skill) for a in verified_answers if a.skill]
        if verified_skills:
            base += f" Verified expertise in {', '.join(verified_skills[:3])}."

        top_required = job.required_skills[:3]
        if top_required:
            base += f" Aligned with role requirements including {', '.join(top_required)}."

        return base.strip()[:600]

    def _build_full_text(self, resume: OptimizedResume) -> str:
        parts = [resume.summary, "SKILLS: " + ", ".join(resume.skills)]
        for exp in resume.experience:
            header = " | ".join(filter(None, [exp.title, exp.company, exp.duration]))
            if header:
                parts.append(header)
            if exp.description:
                parts.append(exp.description)
        if resume.education:
            parts.append("EDUCATION: " + "; ".join(resume.education))
        return "\n\n".join(p for p in parts if p)
