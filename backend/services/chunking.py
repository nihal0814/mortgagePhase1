import re
from dataclasses import dataclass

from config import POLICY_CHUNK_OVERLAP, POLICY_CHUNK_SIZE


@dataclass
class PolicyChunkData:
    page_number: int | None
    section: str | None
    text: str


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and (stripped.isupper() or re.match(r"^(section|chapter|\d+(\.\d+)*)\b", stripped, re.I))


def chunk_policy_pages(pages: list[tuple[int | None, str]]) -> list[PolicyChunkData]:
    chunks: list[PolicyChunkData] = []
    current_section: str | None = None
    for page_number, page_text in pages:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", page_text) if part.strip()]
        if not paragraphs:
            paragraphs = [line.strip() for line in page_text.splitlines() if line.strip()]
        current = ""
        for paragraph in paragraphs:
            lines = paragraph.splitlines()
            if lines and _is_heading(lines[0]):
                current_section = lines[0][:200]
            if current and len(current) + len(paragraph) + 1 > POLICY_CHUNK_SIZE:
                chunks.append(PolicyChunkData(page_number, current_section, current.strip()))
                overlap = current[-POLICY_CHUNK_OVERLAP:] if POLICY_CHUNK_OVERLAP else ""
                current = f"{overlap}\n{paragraph}"
            else:
                current = f"{current}\n{paragraph}".strip()
        if current:
            chunks.append(PolicyChunkData(page_number, current_section, current.strip()))
    return [chunk for chunk in chunks if chunk.text]
