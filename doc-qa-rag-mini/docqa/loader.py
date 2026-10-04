"""Load .txt / .md / .pdf files into (doc_name, page_number, text) records."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator, Tuple

import pdfplumber

PARAGRAPH_GAP = 0.9  # gap between lines, relative to line height, that starts a new PDF paragraph


def _pdf_page_text(page) -> str:
    """Rebuild paragraph breaks (blank lines) from vertical gaps between text lines."""
    out, prev_bottom = [], None
    for line in page.extract_text_lines():
        if prev_bottom is not None and line["top"] - prev_bottom > PARAGRAPH_GAP * (line["bottom"] - line["top"]):
            out.append("")
        out.append(line["text"])
        prev_bottom = line["bottom"]
    return "\n".join(out)


def load_documents(folder: Path) -> Iterator[Tuple[str, int, str]]:
    for path in sorted(Path(folder).iterdir()):
        if path.suffix == ".pdf":
            with pdfplumber.open(path) as pdf:
                for n, page in enumerate(pdf.pages, start=1):
                    yield path.name, n, _pdf_page_text(page)
        elif path.suffix in (".txt", ".md"):
            yield path.name, 1, path.read_text(encoding="utf-8")
