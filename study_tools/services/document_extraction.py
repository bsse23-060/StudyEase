import io
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader

class ExtractionError(ValueError): pass

@dataclass(frozen=True)
class ExtractedBlock:
    text: str
    page: int | None
    section_title: str
    paragraph_position: int
    source_filename: str

def normalise_text(value: str) -> str:
    value = value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [re.sub(r"[ \t]+", " ", part).strip() for part in re.split(r"\n\s*\n", value)]
    return "\n\n".join(part for part in paragraphs if part)

def _meaningful(blocks):
    if sum(len(block.text) for block in blocks) < 20: raise ExtractionError("No meaningful extractable text was found. Scanned PDFs require a future OCR pipeline.")
    return blocks

def extract_pdf(stream, filename: str) -> list[ExtractedBlock]:
    try: reader = PdfReader(stream)
    except Exception as exc: raise ExtractionError("The PDF is corrupted or cannot be read.") from exc
    page_lines = []
    for page in reader.pages:
        try: page_lines.append([line.strip() for line in (page.extract_text() or "").splitlines() if line.strip()])
        except Exception as exc: raise ExtractionError("PDF text extraction failed.") from exc
    edge_counts = Counter(line for lines in page_lines for line in (lines[:1] + lines[-1:]))
    repeated = {line for line, count in edge_counts.items() if len(page_lines) >= 3 and count > len(page_lines) / 2}
    blocks = []
    for page_number, lines in enumerate(page_lines, 1):
        text = normalise_text("\n".join(line for line in lines if line not in repeated))
        for position, paragraph in enumerate(re.split(r"\n\s*\n", text)):
            if paragraph.strip(): blocks.append(ExtractedBlock(paragraph.strip(), page_number, "", position, filename))
    return _meaningful(blocks)

def extract_docx(stream, filename: str) -> list[ExtractedBlock]:
    try: document = DocxDocument(stream)
    except Exception as exc: raise ExtractionError("The DOCX file is corrupted or cannot be read.") from exc
    blocks = []; heading = ""
    for position, paragraph in enumerate(document.paragraphs):
        text = normalise_text(paragraph.text)
        if not text: continue
        if paragraph.style and paragraph.style.name.lower().startswith("heading"): heading = text; continue
        blocks.append(ExtractedBlock(text, None, heading, position, filename))
    return _meaningful(blocks)

def extract_text(stream, filename: str) -> list[ExtractedBlock]:
    try: wrapper = io.TextIOWrapper(stream, encoding="utf-8-sig"); raw = wrapper.read(); wrapper.detach()
    except (UnicodeDecodeError, ValueError) as exc: raise ExtractionError("Text and Markdown documents must be valid UTF-8.") from exc
    blocks = []; heading = ""
    for position, paragraph in enumerate(re.split(r"\n\s*\n", normalise_text(raw))):
        if re.match(r"^#{1,6}\s+", paragraph): heading = re.sub(r"^#{1,6}\s+", "", paragraph).strip(); continue
        blocks.append(ExtractedBlock(paragraph, None, heading, position, filename))
    return _meaningful(blocks)

def extract_document(document) -> list[ExtractedBlock]:
    if not document.file: raise ExtractionError("Remote URL ingestion is disabled to avoid SSRF; upload a supported file.")
    with document.file.open("rb") as stream:
        if document.mime_type == "application/pdf": return extract_pdf(stream, document.original_filename)
        if document.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document": return extract_docx(stream, document.original_filename)
        if document.mime_type in {"text/plain", "text/markdown"}: return extract_text(stream, document.original_filename)
    raise ExtractionError(f"Unsupported MIME type: {document.mime_type}")
