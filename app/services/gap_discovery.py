import json

from app.models.schemas import GapQuestion, GapQuestionsResponse, JobDescription, MatchResult, ParsedResume
from app.prompts.gap_questions import SYSTEM_PROMPT
from app.services.ai_client import AIClient


class GapDiscoveryEngine:
    """Generate targeted follow-up questions to fill skill gaps."""

    MAX_QUESTIONS = 6

    def __init__(self, ai_client: AIClient | None = None) -> None:
        self.ai = ai_client or AIClient()

    def generate(
        self,
        resume: ParsedResume,
        job: JobDescription,
        match: MatchResult,
    ) -> GapQuestionsResponse:
        ai_result = self._generate_with_ai(resume, job, match)
        if ai_result:
            return ai_result

        return GapQuestionsResponse(
            questions=self._generate_fallback(match),
            ai_powered=False,
        )

    def _generate_with_ai(
        self,
        resume: ParsedResume,
        job: JobDescription,
        match: MatchResult,
    ) -> GapQuestionsResponse | None:
        if not self.ai.is_available:
            return None

        user_prompt = json.dumps(
            {
                "resume_summary": resume.summary,
                "resume_skills": resume.skills,
                "resume_experience": [e.model_dump() for e in resume.experience],
                "job_title": job.title,
                "job_required_skills": job.required_skills,
                "job_preferred_skills": job.preferred_skills,
                "missing_required": match.missing_required,
                "missing_preferred": match.missing_preferred,
                "job_responsibilities": job.responsibilities[:5],
            },
            indent=2,
        )

        result = self.ai.chat_json(SYSTEM_PROMPT, user_prompt)
        if not result or "questions" not in result:
            return None

        questions: list[GapQuestion] = []
        for idx, item in enumerate(result["questions"][: self.MAX_QUESTIONS]):
            questions.append(
                GapQuestion(
                    id=item.get("id", f"q{idx + 1}"),
                    skill=item.get("skill", ""),
                    question=item.get("question", ""),
                    importance=item.get("importance", "required"),
                )
            )

        if not questions:
            return None

        return GapQuestionsResponse(questions=questions, ai_powered=True)

    def _generate_fallback(self, match: MatchResult) -> list[GapQuestion]:
        questions: list[GapQuestion] = []
        idx = 1

        for skill in match.missing_required[:4]:
            questions.append(
                GapQuestion(
                    id=f"q{idx}",
                    skill=skill,
                    importance="required",
                    question=(
                        f"Do you have experience with {skill}? "
                        f"If yes, describe a specific project, your role, and a measurable outcome. "
                        f"Leave blank if you don't have this experience."
                    ),
                )
            )
            idx += 1

        for skill in match.missing_preferred[:2]:
            if len(questions) >= self.MAX_QUESTIONS:
                break
            questions.append(
                GapQuestion(
                    id=f"q{idx}",
                    skill=skill,
                    importance="preferred",
                    question=(
                        f"Have you used {skill} in any professional or personal project? "
                        f"If yes, briefly describe the context and results."
                    ),
                )
            )
            idx += 1

        if not questions and match.skill_gaps:
            for gap in match.skill_gaps[: self.MAX_QUESTIONS]:
                questions.append(
                    GapQuestion(
                        id=f"q{idx}",
                        skill=gap.skill,
                        importance=gap.importance,
                        question=(
                            f"Can you provide verified examples of your work with {gap.skill}? "
                            f"Include metrics if possible."
                        ),
                    )
                )
                idx += 1

        return questions
