from app.models.schemas import JobDescription, MatchResult, ParsedResume, SkillGap
from app.utils.skills import normalize_skill


class MatchEngine:
    """Compute match score, identify skill gaps, and generate improvement suggestions."""

    REQUIRED_WEIGHT = 0.75
    PREFERRED_WEIGHT = 0.25

    def analyze(self, resume: ParsedResume, job: JobDescription) -> MatchResult:
        resume_skills = {normalize_skill(s) for s in resume.skills}
        required = [normalize_skill(s) for s in job.required_skills]
        preferred = [normalize_skill(s) for s in job.preferred_skills]

        matching_required = [s for s in required if s in resume_skills]
        matching_preferred = [s for s in preferred if s in resume_skills]
        missing_required = [s for s in required if s not in resume_skills]
        missing_preferred = [s for s in preferred if s not in resume_skills]

        score = self._compute_score(
            required_count=len(required),
            preferred_count=len(preferred),
            matching_required=len(matching_required),
            matching_preferred=len(matching_preferred),
            resume_skill_count=len(resume_skills),
        )

        matching_skills = sorted(set(matching_required + matching_preferred))
        skill_gaps = self._build_skill_gaps(missing_required, missing_preferred)
        suggestions = self._build_suggestions(
            resume=resume,
            job=job,
            score=score,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            matching_skills=matching_skills,
        )

        return MatchResult(
            score=score,
            matching_skills=matching_skills,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            skill_gaps=skill_gaps,
            improvement_suggestions=suggestions,
        )

    def _compute_score(
        self,
        required_count: int,
        preferred_count: int,
        matching_required: int,
        matching_preferred: int,
        resume_skill_count: int,
    ) -> float:
        if required_count == 0 and preferred_count == 0:
            base = min(100.0, 40.0 + resume_skill_count * 3)
            return round(base, 1)

        required_score = (matching_required / required_count * 100) if required_count else 100.0
        preferred_score = (matching_preferred / preferred_count * 100) if preferred_count else 100.0

        weighted = (
            required_score * self.REQUIRED_WEIGHT
            + preferred_score * self.PREFERRED_WEIGHT
        )
        return round(min(100.0, max(0.0, weighted)), 1)

    def _build_skill_gaps(
        self,
        missing_required: list[str],
        missing_preferred: list[str],
    ) -> list[SkillGap]:
        gaps: list[SkillGap] = []

        for skill in missing_required:
            gaps.append(
                SkillGap(
                    skill=skill,
                    importance="required",
                    suggestion=self._gap_suggestion(skill, required=True),
                )
            )

        for skill in missing_preferred:
            gaps.append(
                SkillGap(
                    skill=skill,
                    importance="preferred",
                    suggestion=self._gap_suggestion(skill, required=False),
                )
            )

        return gaps

    def _gap_suggestion(self, skill: str, required: bool) -> str:
        urgency = "critical" if required else "beneficial"
        return (
            f"Highlight any {skill} experience in your resume, or add a project/certification "
            f"that demonstrates {skill}. Closing this gap is {urgency} for this role."
        )

    def _build_suggestions(
        self,
        resume: ParsedResume,
        job: JobDescription,
        score: float,
        missing_required: list[str],
        missing_preferred: list[str],
        matching_skills: list[str],
    ) -> list[str]:
        suggestions: list[str] = []

        if score >= 80:
            suggestions.append(
                "Strong match. Tailor your summary to mirror the job title and top responsibilities."
            )
        elif score >= 60:
            suggestions.append(
                "Good foundation. Emphasize matching skills near the top of your resume and in your summary."
            )
        else:
            suggestions.append(
                "Significant gaps detected. Prioritize adding verified experience for required skills before applying."
            )

        if missing_required:
            top_missing = ", ".join(missing_required[:3])
            suggestions.append(
                f"Add specific examples demonstrating: {top_missing}. Use quantified bullet points where possible."
            )

        if matching_skills:
            top_matching = ", ".join(matching_skills[:5])
            suggestions.append(
                f"Lead with your strengths: {top_matching}. Place these in a dedicated Skills section and in relevant job bullets."
            )

        if not resume.summary:
            suggestions.append(
                "Add a professional summary (3-4 lines) aligned with the job description's language."
            )

        if len(resume.experience) == 0:
            suggestions.append(
                "Ensure work experience is clearly structured with role, company, dates, and achievement-focused bullets."
            )

        if job.responsibilities and resume.experience:
            suggestions.append(
                "Rewrite experience bullets to mirror key job responsibilities using similar action verbs and keywords."
            )

        if missing_preferred:
            suggestions.append(
                f"Optional boost: mention {', '.join(missing_preferred[:2])} if you have verified experience."
            )

        return suggestions[:6]
