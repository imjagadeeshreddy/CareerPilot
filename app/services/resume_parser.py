import io
import re
from pathlib import Path

import pdfplumber
from docx import Document

from app.models.schemas import ExperienceEntry, ParsedResume
from app.utils.skills import clean_text, extract_skills_from_text

MONTH_PATTERN = (
    r"january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)


class ResumeParserService:
    """Extract text, skills, and experience from resume files."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
    BULLET_PREFIX = re.compile(r"^[\u2022\-*•]\s*")

    def parse_file(self, filename: str, content: bytes) -> ParsedResume:
        extension = Path(filename).suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {extension}. Use PDF, DOCX, or TXT.")

        if extension == ".pdf":
            raw_text = self._extract_pdf(content)
        elif extension in {".docx", ".doc"}:
            raw_text = self._extract_docx(content)
        else:
            raw_text = content.decode("utf-8", errors="ignore")

        return self.parse_text(raw_text)

    def parse_text(self, raw_text: str) -> ParsedResume:
        text = clean_text(raw_text)
        contact = self._extract_contact(text)
        skills_section = self._extract_skills_section(text)
        skills = extract_skills_from_text(text)
        if skills_section:
            skills = sorted(set(skills + extract_skills_from_text(skills_section)))
        experience = self._extract_experience(text)
        summary = self._extract_summary(text)
        education = self._extract_education(text)
        certifications = self._extract_certifications(text)

        return ParsedResume(
            raw_text=text,
            name=contact["name"],
            email=contact["email"],
            phone=contact["phone"],
            linkedin=contact["linkedin"],
            skills=skills,
            skills_section=skills_section,
            experience=experience,
            summary=summary,
            education=education,
            certifications=certifications,
        )

    def _extract_pdf(self, content: bytes) -> str:
        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
        return "\n".join(pages)

    def _extract_docx(self, content: bytes) -> str:
        document = Document(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())

    def _extract_contact(self, text: str) -> dict[str, str]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        name = ""
        email = ""
        phone = ""
        linkedin = ""

        email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
        if email_match:
            email = email_match.group(0)

        phone_match = re.search(r"\+?\d[\d\s().-]{8,}\d", text)
        if phone_match:
            phone = phone_match.group(0).strip()

        linkedin_match = re.search(r"(?:linkedin\.com/in/|in/)([\w-]+)", text, re.I)
        if linkedin_match:
            linkedin = linkedin_match.group(1)

        for line in lines[:5]:
            if email in line or phone in line or "linkedin" in line.lower():
                continue
            if len(line.split()) >= 2 and len(line) < 60 and line.isupper():
                name = line.title()
                break
            if len(line.split()) >= 2 and len(line) < 60 and not re.search(r"\d", line):
                name = line
                break

        return {"name": name, "email": email, "phone": phone, "linkedin": linkedin}

    def _extract_summary(self, text: str) -> str:
        patterns = [
            r"(?i)(?:professional\s+)?summary[:\s]*(.+?)(?=\n(?:skills|experience|work history|employment|education)\b)",
            r"(?i)(?:profile|objective)[:\s]*(.+?)(?=\n(?:skills|experience|work history|employment|education)\b)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return clean_text(match.group(1))[:800]
        return ""

    def _extract_skills_section(self, text: str) -> str:
        section = self._extract_section(
            text,
            ["skills", "technical skills", "core competencies", "technologies"],
        )
        return section.strip()

    def _extract_education(self, text: str) -> list[str]:
        section = self._extract_section(text, ["education", "academic background", "qualifications"])
        if not section:
            return []

        entries: list[str] = []
        for line in section.split("\n"):
            line = line.strip().lstrip("-•* ")
            if line and len(line) > 5 and not re.match(r"(?i)^certification", line):
                entries.append(line)
        return entries[:6]

    def _extract_certifications(self, text: str) -> list[str]:
        section = self._extract_section(text, ["certifications", "certificates", "licenses"])
        if not section:
            return []

        entries: list[str] = []
        for line in section.split("\n"):
            line = line.strip().lstrip("-•* ")
            if line and len(line) > 5:
                entries.append(line)
        return entries[:6]

    def _extract_experience(self, text: str) -> list[ExperienceEntry]:
        section = self._extract_section(
            text,
            ["experience", "work experience", "professional experience", "employment history", "work history"],
        )
        if not section:
            return self._fallback_experience(text)

        entries = self._parse_experience_blocks(section)
        if entries:
            return entries[:15]

        return self._fallback_experience(text)

    def _parse_experience_blocks(self, section: str) -> list[ExperienceEntry]:
        lines = [line.strip() for line in section.split("\n") if line.strip()]
        entries: list[ExperienceEntry] = []
        i = 0

        while i < len(lines):
            line = lines[i]
            if not self._is_job_header(line):
                i += 1
                continue

            title, company = self._parse_job_header(line)
            duration = ""
            i += 1

            if i < len(lines) and self._is_date_line(lines[i]):
                duration = self._parse_duration_line(lines[i])
                i += 1

            bullets: list[str] = []
            while i < len(lines) and not self._is_job_header(lines[i]):
                bullet = self.BULLET_PREFIX.sub("", lines[i]).strip()
                if bullet:
                    bullets.append(bullet)
                i += 1

            entries.append(
                ExperienceEntry(
                    title=title,
                    company=company,
                    duration=duration,
                    description="\n".join(bullets),
                )
            )

        return entries

    def _is_job_header(self, line: str) -> bool:
        if "|" not in line or self.BULLET_PREFIX.match(line):
            return False
        if self._is_date_line(line):
            return False

        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 2:
            return False

        title, company = parts
        if len(title) < 3 or len(company) < 2:
            return False
        if re.search(r"\d{4}", title) and not re.search(r"(?i)engineer|developer|manager|analyst|architect|lead|consultant", title):
            return False
        return True

    def _is_date_line(self, line: str) -> bool:
        lower = line.lower()
        if re.search(rf"(?i)(?:{MONTH_PATTERN})", lower) and re.search(r"\d{4}|present|current", lower):
            return True
        if re.search(r"\d{4}\s*[-–—]\s*(?:\d{4}|present|current)", lower):
            return True
        return False

    def _parse_job_header(self, line: str) -> tuple[str, str]:
        parts = [part.strip() for part in line.split("|", 1)]
        return parts[0], parts[1]

    def _parse_duration_line(self, line: str) -> str:
        return line.split("|")[0].strip()

    def _fallback_experience(self, text: str) -> list[ExperienceEntry]:
        pattern = re.compile(
            r"(?i)([\w\s/&]+)\s+(?:at|@|\|)\s*([\w\s.&]+?)(?:\s*[|–—-]\s*(\d{4}.*?))?(?:\n|$)"
        )
        entries: list[ExperienceEntry] = []
        for match in pattern.finditer(text):
            entries.append(
                ExperienceEntry(
                    title=match.group(1).strip(),
                    company=match.group(2).strip(),
                    duration=(match.group(3) or "").strip(),
                    description="",
                )
            )
        return entries[:10]

    def _extract_section(self, text: str, headings: list[str]) -> str:
        heading_pattern = "|".join(re.escape(h) for h in headings)
        next_sections = (
            "experience|work experience|professional experience|employment|work history|"
            "skills|technical skills|education|projects|certifications|summary|profile"
        )
        pattern = rf"(?i)(?:{heading_pattern})\s*[:\n](.+?)(?=\n(?:{next_sections})\s*[:\n]|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        return clean_text(match.group(1)) if match else ""
