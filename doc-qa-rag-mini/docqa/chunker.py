"""Paragraph-based chunking that keeps headings attached to their text."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple

MAX_CHARS = 700


@dataclass(frozen=True)
class Chunk:
    doc: str
    page: int
    index: int  # position within the document
    text: str

    @property
    def cite(self) -> str:
        return f"{self.doc}, page {self.page}, chunk {self.index}"


def _is_heading(block: str) -> bool:
    """Short block with no sentence-ending punctuation (or a markdown '#' line)."""
    return block.startswith("#") or (len(block) < 60 and "\n" not in block and not block.endswith((".", "!", "?")))


def _split_long(block: str) -> List[str]:
    if len(block) <= MAX_CHARS:
        return [block]
    parts, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", block):
        if cur and len(cur) + len(sentence) > MAX_CHARS:
            parts.append(cur.strip())
            cur = ""
        cur += sentence + " "
    return parts + [cur.strip()]


def chunk_documents(records: Iterable[Tuple[str, int, str]]) -> List[Chunk]:
    chunks: List[Chunk] = []
    counters = {}
    for doc, page, text in records:
        pending_heading = ""
        for block in (b.strip() for b in re.split(r"\n\s*\n", text)):
            if not block:
                continue
            block = re.sub(r"[ \t]*\n[ \t]*", "\n", block)
            if _is_heading(block):
                pending_heading += block.lstrip("# ").strip() + ". "
                continue
            body = (pending_heading + re.sub(r"\n", " ", block)).strip()
            pending_heading = ""
            for part in _split_long(body):
                idx = counters.get(doc, 0)
                counters[doc] = idx + 1
                chunks.append(Chunk(doc, page, idx, part))
    return chunks
