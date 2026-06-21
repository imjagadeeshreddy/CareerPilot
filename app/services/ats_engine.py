from app.models.schemas import ATSResult, JobDescription, OptimizedResume
from app.utils.skills import extract_skills_from_text, normalize_skill


class ATSEngine:
    """Score resume against job description for ATS compatibility."""

    SECTION_KEYWORDS = ("experience", "skills", "education", "summary", "work")

    def analyze(self, resume: OptimizedResume, job: JobDescription) -> ATSResult:
        resume_text = resume.full_text.lower()
        resume_skills = {normalize_skill(s) for s in resume.skills}
        resume_skills.update(extract_skills_from_text(resume.full_text))

        all_job_skills = [normalize_skill(s) for s in job.required_skills + job.preferred_skills]
        job_keywords = self._extract_job_keywords(job)

        matched_keywords: list[str] = []
        missing_keywords: list[str] = []

        for skill in all_job_skills:
            if skill in resume_skills or skill in resume_text:
                matched_keywords.append(skill)
            else:
                missing_keywords.append(skill)

        for keyword in job_keywords:
            if keyword in resume_text and keyword not in matched_keywords:
                matched_keywords.append(keyword)
            elif keyword not in resume_text and keyword not in missing_keywords:
                missing_keywords.append(keyword)

        matched_keywords = sorted(set(matched_keywords))
        missing_keywords = sorted(set(missing_keywords))

        score = self._compute_score(
            resume=resume,
            resume_text=resume_text,
            total_job_skills=len(all_job_skills),
            matched_count=len(matched_keywords),
            job_keywords=job_keywords,
        )

        recommendations = self._build_recommendations(
            resume=resume,
            missing_keywords=missing_keywords,
            score=score,
        )

        return ATSResult(
            score=score,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords[:10],
            recommendations=recommendations,
        )

    def _extract_job_keywords(self, job: JobDescription) -> list[str]:
        keywords: set[str] = set()
        for skill in job.required_skills + job.preferred_skills:
            keywords.add(normalize_skill(skill))

        for resp in job.responsibilities:
            for word in resp.lower().split():
                cleaned = word.strip(".,;:-()")
                if len(cleaned) > 4 and cleaned.isalpha():
                    keywords.add(cleaned)

        if job.title:
            for word in job.title.lower().split():
                if len(word) > 3:
                    keywords.add(word)

        return sorted(keywords)

    def _compute_score(
        self,
        resume: OptimizedResume,
        resume_text: str,
        total_job_skills: int,
        matched_count: int,
        job_keywords: list[str],
    ) -> float:
        skill_score = (matched_count / total_job_skills * 100) if total_job_skills else 70.0

        keyword_hits = sum(1 for kw in job_keywords if kw in resume_text)
        keyword_score = (keyword_hits / len(job_keywords) * 100) if job_keywords else 70.0

        structure_score = 0.0
        if resume.summary:
            structure_score += 25
        if resume.skills:
            structure_score += 25
        if resume.experience:
            structure_score += 30
        if resume.education:
            structure_score += 10
        if any(section in resume_text for section in self.SECTION_KEYWORDS):
            structure_score += 10

        weighted = skill_score * 0.5 + keyword_score * 0.3 + structure_score * 0.2
        return round(min(100.0, max(0.0, weighted)), 1)

    def _build_recommendations(
        self,
        resume: OptimizedResume,
        missing_keywords: list[str],
        score: float,
    ) -> list[str]:
        recs: list[str] = []

        if score >= 80:
            recs.append("Strong ATS compatibility. Resume keywords align well with the job description.")
        elif score >= 60:
            recs.append("Moderate ATS score. Add a few more job-specific keywords to key sections.")
        else:
            recs.append("Low ATS score. Incorporate more keywords from the job description naturally.")

        if missing_keywords:
            top = ", ".join(missing_keywords[:5])
            recs.append(f"Consider adding verified experience for: {top}")

        if not resume.summary:
            recs.append("Add a professional summary with role-relevant keywords near the top.")

        if len(resume.skills) < 5:
            recs.append("Expand the skills section with tools and technologies from the job description.")

        if resume.experience:
            recs.append("Use bullet points starting with strong action verbs (Led, Built, Optimized, Delivered).")

        return recs[:5]
