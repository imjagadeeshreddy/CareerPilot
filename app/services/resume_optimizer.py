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
from app.utils.skills import normalize_skill


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
            merged = self._merge_with_original(ai_result, resume, verified)
            return merged, True

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
                    "name": resume.name,
                    "summary": resume.summary,
                    "skills": resume.skills,
                    "skills_section": resume.skills_section,
                    "experience": [e.model_dump() for e in resume.experience],
                    "education": resume.education,
                    "certifications": resume.certifications,
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

            optimized = OptimizedResume(
                name=original.name,
                email=original.email,
                phone=original.phone,
                linkedin=original.linkedin,
                summary=result.get("summary") or original.summary,
                skills=result.get("skills") or list(original.skills),
                skills_section=original.skills_section,
                experience=experience if experience else list(original.experience),
                education=result.get("education") or list(original.education),
                certifications=list(original.certifications),
            )
            return optimized
        except (KeyError, TypeError):
            return None

    def _merge_with_original(
        self,
        optimized: OptimizedResume,
        original: ParsedResume,
        verified_answers: list[UserAnswer],
    ) -> OptimizedResume:
        optimized.name = original.name or optimized.name
        optimized.email = original.email or optimized.email
        optimized.phone = original.phone or optimized.phone
        optimized.linkedin = original.linkedin or optimized.linkedin
        optimized.skills_section = original.skills_section or optimized.skills_section
        optimized.certifications = original.certifications or optimized.certifications

        optimized.experience = self._merge_experience(original.experience, optimized.experience)
        optimized.skills = self._merge_skills(original.skills, optimized.skills, verified_answers)

        if len(original.education) > len(optimized.education):
            optimized.education = list(original.education)
        elif not optimized.education:
            optimized.education = list(original.education)

        if not optimized.summary and original.summary:
            optimized.summary = original.summary

        optimized = self._append_verified_answers(optimized, verified_answers)
        optimized.full_text = self._build_full_text(optimized)
        return optimized

    def _merge_experience(
        self,
        original: list[ExperienceEntry],
        updated: list[ExperienceEntry],
    ) -> list[ExperienceEntry]:
        if not original:
            return updated

        updated_by_key = {self._exp_key(e): e for e in updated if self._exp_key(e)}
        merged: list[ExperienceEntry] = []
        used_keys: set[str] = set()

        for orig in original:
            key = self._exp_key(orig)
            if key in updated_by_key:
                ai_entry = updated_by_key[key]
                merged.append(
                    ExperienceEntry(
                        title=ai_entry.title or orig.title,
                        company=orig.company or ai_entry.company,
                        duration=ai_entry.duration or orig.duration,
                        description=self._merge_descriptions(orig.description, ai_entry.description),
                    )
                )
                used_keys.add(key)
            else:
                merged.append(ExperienceEntry(**orig.model_dump()))

        for upd in updated:
            key = self._exp_key(upd)
            if key and key not in used_keys:
                merged.append(upd)

        return merged

    def _merge_descriptions(self, original: str, updated: str) -> str:
        if not updated:
            return original
        if not original:
            return updated

        orig_bullets = self._split_bullets(original)
        upd_bullets = self._split_bullets(updated)
        combined: list[str] = []
        seen: set[str] = set()

        for bullet in upd_bullets + orig_bullets:
            key = bullet.lower().strip()
            if key and key not in seen:
                seen.add(key)
                combined.append(bullet)

        return "\n".join(combined)

    def _split_bullets(self, text: str) -> list[str]:
        lines = [self._clean_bullet(line) for line in text.split("\n")]
        return [line for line in lines if line]

    def _clean_bullet(self, line: str) -> str:
        return re.sub(r"^[\u2022\-*•]\s*", "", line.strip())

    def _exp_key(self, entry: ExperienceEntry) -> str:
        company = normalize_skill(entry.company.replace(".", ""))
        title = normalize_skill(entry.title)
        return f"{company}|{title}" if company else title

    def _merge_skills(
        self,
        original: list[str],
        updated: list[str],
        verified_answers: list[UserAnswer],
    ) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()

        for skill in original + updated:
            key = normalize_skill(skill)
            if key and key not in seen:
                seen.add(key)
                merged.append(skill)

        for answer in verified_answers:
            if answer.skill:
                key = normalize_skill(answer.skill)
                if key not in seen:
                    seen.add(key)
                    merged.append(answer.skill)

        return merged

    def _append_verified_answers(
        self,
        optimized: OptimizedResume,
        verified_answers: list[UserAnswer],
    ) -> OptimizedResume:
        if not verified_answers or not optimized.experience:
            return optimized

        target = optimized.experience[0]
        for answer in verified_answers:
            bullet = answer.answer.strip()
            if bullet and bullet not in target.description:
                prefix = "" if not target.description else "\n"
                target.description = f"{target.description}{prefix}{bullet}".strip()

        return optimized

    def _optimize_fallback(
        self,
        resume: ParsedResume,
        job: JobDescription,
        verified_answers: list[UserAnswer],
    ) -> OptimizedResume:
        experience = [ExperienceEntry(**e.model_dump()) for e in resume.experience]
        skills = list(resume.skills)

        for answer in verified_answers:
            skill = normalize_skill(answer.skill) if answer.skill else ""
            if skill and skill not in {normalize_skill(s) for s in skills}:
                skills.append(answer.skill)

        summary = self._build_summary(resume.summary, job, verified_answers)

        optimized = OptimizedResume(
            name=resume.name,
            email=resume.email,
            phone=resume.phone,
            linkedin=resume.linkedin,
            summary=summary,
            skills=skills,
            skills_section=resume.skills_section,
            experience=experience,
            education=list(resume.education),
            certifications=list(resume.certifications),
        )
        optimized = self._append_verified_answers(optimized, verified_answers)
        optimized.full_text = self._build_full_text(optimized)
        return optimized

    def _build_summary(
        self,
        original_summary: str,
        job: JobDescription,
        verified_answers: list[UserAnswer],
    ) -> str:
        base = original_summary or f"Professional seeking {job.title or 'a new role'}."

        verified_skills = [a.skill for a in verified_answers if a.skill]
        if verified_skills:
            base += f" Verified expertise in {', '.join(verified_skills[:3])}."

        top_required = job.required_skills[:3]
        if top_required and original_summary:
            return base.strip()[:800]

        if top_required:
            base += f" Aligned with role requirements including {', '.join(top_required)}."

        return base.strip()[:800]

    def _build_full_text(self, resume: OptimizedResume) -> str:
        parts: list[str] = []
        if resume.name:
            parts.append(resume.name)
        contact = " | ".join(filter(None, [resume.email, resume.phone, resume.linkedin]))
        if contact:
            parts.append(contact)
        if resume.summary:
            parts.append(resume.summary)
        if resume.skills_section:
            parts.append("SKILLS:\n" + resume.skills_section)
        elif resume.skills:
            parts.append("SKILLS: " + ", ".join(resume.skills))
        for exp in resume.experience:
            header = " | ".join(filter(None, [exp.title, exp.company, exp.duration]))
            if header:
                parts.append(header)
            if exp.description:
                parts.append(exp.description)
        if resume.education:
            parts.append("EDUCATION:\n" + "\n".join(resume.education))
        if resume.certifications:
            parts.append("CERTIFICATIONS:\n" + "\n".join(resume.certifications))
        return "\n\n".join(p for p in parts if p)
