import hashlib
import re
from dataclasses import dataclass
from .document_extraction import ExtractedBlock

@dataclass(frozen=True)
class ChunkData:
    text: str
    position: int
    page: int | None
    section_title: str
    start_position: int
    end_position: int
    character_count: int
    token_count: int
    content_checksum: str
    metadata: dict

def _sentences(text: str) -> list[str]: return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]

def chunk_blocks(blocks: list[ExtractedBlock], chunk_size: int, overlap: int, minimum: int) -> list[ChunkData]:
    candidates = []
    for block in blocks:
        units = _sentences(block.text) or [block.text]; current = ""
        for unit in units:
            if current and len(current) + 1 + len(unit) > chunk_size:
                candidates.append((current, block)); current = (current[-overlap:].lstrip() + " " + unit).strip() if overlap else unit
            else: current = f"{current} {unit}".strip()
        if current: candidates.append((current, block))
    result = []; seen = set(); cursor = 0
    for text, block in candidates:
        text = text.strip()
        if len(text) < minimum and result and result[-1].page == block.page:
            previous = result.pop(); text = f"{previous.text}\n\n{text}"; cursor = previous.start_position
        checksum = hashlib.sha256(text.encode()).hexdigest()
        if checksum in seen: continue
        seen.add(checksum); end = cursor + len(text)
        result.append(ChunkData(text, len(result), block.page, block.section_title, cursor, end, len(text), len(text.split()), checksum, {"source_filename": block.source_filename, "paragraph_position": block.paragraph_position}))
        cursor = end
    if not result: raise ValueError("Chunking produced no useful content.")
    return result
