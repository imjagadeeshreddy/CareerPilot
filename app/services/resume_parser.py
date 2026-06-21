import io
import re
from pathlib import Path

import pdfplumber
from docx import Document

from app.models.schemas import ExperienceEntry, ParsedResume
from app.utils.skills import clean_text, extract_skills_from_text


class ResumeParserService:
    """Extract text, skills, and experience from resume files."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}

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
        skills = extract_skills_from_text(text)
        experience = self._extract_experience(text)
        summary = self._extract_summary(text)
        education = self._extract_education(text)

        return ParsedResume(
            raw_text=text,
            skills=skills,
            experience=experience,
            summary=summary,
            education=education,
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

    def _extract_summary(self, text: str) -> str:
        patterns = [
            r"(?i)(?:professional\s+)?summary[:\s]*(.+?)(?=\n(?:experience|work history|employment|skills|education)\b)",
            r"(?i)(?:profile|objective)[:\s]*(.+?)(?=\n(?:experience|work history|employment|skills|education)\b)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return clean_text(match.group(1))[:500]
        return ""

    def _extract_education(self, text: str) -> list[str]:
        section = self._extract_section(text, ["education", "academic background", "qualifications"])
        if not section:
            return []

        entries: list[str] = []
        for line in section.split("\n"):
            line = line.strip()
            if line and len(line) > 5:
                entries.append(line)
        return entries[:5]

    def _extract_experience(self, text: str) -> list[ExperienceEntry]:
        section = self._extract_section(
            text,
            ["experience", "work experience", "professional experience", "employment history", "work history"],
        )
        if not section:
            return self._fallback_experience(text)

        entries: list[ExperienceEntry] = []
        blocks = re.split(r"\n(?=[A-Z][^\n]{0,80}(?:\||–|—|-)\s*(?:\d{4}|present|current))", section)

        for block in blocks:
            block = block.strip()
            if len(block) < 20:
                continue

            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue

            header = lines[0]
            title, company, duration = self._parse_experience_header(header)
            description = " ".join(lines[1:])[:500]

            entries.append(
                ExperienceEntry(
                    title=title,
                    company=company,
                    duration=duration,
                    description=description,
                )
            )

        return entries[:10]

    def _fallback_experience(self, text: str) -> list[ExperienceEntry]:
        pattern = re.compile(
            r"(?i)([\w\s/&]+)\s+(?:at|@)\s+([\w\s.&]+?)(?:\s*[|–—-]\s*(\d{4}.*?))?(?:\n|$)"
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
        return entries[:5]

    def _parse_experience_header(self, header: str) -> tuple[str, str, str]:
        parts = re.split(r"\s*[|–—-]\s*", header)
        if len(parts) >= 3:
            return parts[0].strip(), parts[1].strip(), parts[2].strip()
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip(), ""
        return header.strip(), "", ""

    def _extract_section(self, text: str, headings: list[str]) -> str:
        heading_pattern = "|".join(re.escape(h) for h in headings)
        next_sections = (
            "experience|work experience|professional experience|employment|work history|"
            "skills|technical skills|education|projects|certifications|summary|profile"
        )
        pattern = rf"(?i)(?:{heading_pattern})\s*[:\n](.+?)(?=\n(?:{next_sections})\s*[:\n]|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        return clean_text(match.group(1)) if match else ""
