import re

from app.models.schemas import JobDescription
from app.utils.skills import clean_text, extract_skills_from_text, normalize_skill


class JobParserService:
    """Parse job descriptions and extract required/preferred skills."""

    REQUIRED_MARKERS = (
        "required",
        "must have",
        "must-have",
        "minimum qualifications",
        "basic qualifications",
        "requirements",
        "required skills",
        "required qualifications",
        "what you need",
        "what you'll need",
        "you have",
        "you'll have",
    )

    PREFERRED_MARKERS = (
        "preferred",
        "nice to have",
        "nice-to-have",
        "bonus",
        "plus",
        "desired",
        "preferred skills",
        "preferred qualifications",
        "good to have",
        "would be great",
    )

    def parse_text(self, raw_text: str) -> JobDescription:
        text = clean_text(raw_text)
        title = self._extract_title(text)
        responsibilities = self._extract_responsibilities(text)
        required_skills, preferred_skills = self._extract_skill_groups(text)

        all_skills = extract_skills_from_text(text)
        if not required_skills and not preferred_skills:
            required_skills = all_skills
        else:
            required_set = {normalize_skill(s) for s in required_skills}
            preferred_set = {normalize_skill(s) for s in preferred_skills}
            for skill in all_skills:
                normalized = normalize_skill(skill)
                if normalized not in required_set and normalized not in preferred_set:
                    required_skills.append(skill)

        return JobDescription(
            raw_text=text,
            required_skills=sorted(set(normalize_skill(s) for s in required_skills)),
            preferred_skills=sorted(set(normalize_skill(s) for s in preferred_skills)),
            title=title,
            responsibilities=responsibilities,
        )

    def _extract_title(self, text: str) -> str:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return ""

        first_line = lines[0]
        if len(first_line) <= 80 and not first_line.endswith("."):
            return first_line

        patterns = [
            r"(?i)(?:job title|position|role)[:\s]+(.+)",
            r"(?i)(?:we are looking for|seeking)\s+(?:a\s+)?(.+?)(?:\s+to|\s+who|\.$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()[:100]
        return ""

    def _extract_responsibilities(self, text: str) -> list[str]:
        section = self._extract_section(
            text,
            [
                "responsibilities",
                "what you'll do",
                "what you will do",
                "key responsibilities",
                "your role",
                "the role",
                "duties",
            ],
        )
        if not section:
            return []

        bullets = re.findall(r"(?:^|\n)\s*[-•*]\s*(.+)", section)
        if bullets:
            return [b.strip() for b in bullets[:8]]

        lines = [line.strip() for line in section.split("\n") if len(line.strip()) > 15]
        return lines[:8]

    def _extract_skill_groups(self, text: str) -> tuple[list[str], list[str]]:
        required: list[str] = []
        preferred: list[str] = []

        sections = self._split_into_sections(text)
        for heading, body in sections:
            heading_lower = heading.lower()
            skills = extract_skills_from_text(body)
            if not skills:
                skills = self._extract_bullet_skills(body)

            if any(marker in heading_lower for marker in self.REQUIRED_MARKERS):
                required.extend(skills)
            elif any(marker in heading_lower for marker in self.PREFERRED_MARKERS):
                preferred.extend(skills)

        if not required:
            required = self._extract_bullet_skills(text)

        return required, preferred

    def _extract_bullet_skills(self, text: str) -> list[str]:
        skills: list[str] = []
        for line in text.split("\n"):
            line = line.strip().lstrip("-•* ").strip()
            if not line or len(line) > 120:
                continue
            line_skills = extract_skills_from_text(line)
            if line_skills:
                skills.extend(line_skills)
            elif self._looks_like_skill_phrase(line):
                skills.append(normalize_skill(line.split(",")[0]))
        return skills

    def _looks_like_skill_phrase(self, line: str) -> bool:
        lower = line.lower()
        if any(word in lower for word in ("experience", "years", "degree", "bachelor", "master")):
            return False
        return 2 <= len(line.split()) <= 6

    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        pattern = r"(?i)^([A-Za-z][A-Za-z\s/&'-]{2,50})\s*:?\s*$"
        lines = text.split("\n")
        sections: list[tuple[str, str]] = []
        current_heading = "general"
        current_body: list[str] = []

        for line in lines:
            if re.match(pattern, line.strip()):
                if current_body:
                    sections.append((current_heading, "\n".join(current_body)))
                current_heading = line.strip().rstrip(":")
                current_body = []
            else:
                current_body.append(line)

        if current_body:
            sections.append((current_heading, "\n".join(current_body)))

        return sections

    def _extract_section(self, text: str, headings: list[str]) -> str:
        heading_pattern = "|".join(re.escape(h) for h in headings)
        next_sections = (
            "requirements|qualifications|skills|benefits|about|responsibilities|"
            "what you'll do|what you will do|preferred|required"
        )
        pattern = rf"(?i)(?:{heading_pattern})\s*[:\n](.+?)(?=\n(?:{next_sections})\s*[:\n]|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        return clean_text(match.group(1)) if match else ""
