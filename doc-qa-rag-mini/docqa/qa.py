"""Question answering over the chunk index: cited extractive answer or an explicit 'not found'."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .chunker import Chunk, chunk_documents
from .loader import load_documents
from .retrievers import BM25Retriever, TfidfRetriever, tokenize

NOT_FOUND = "Not found in the provided documents."
DEFAULT_THRESHOLD = {"tfidf": 0.28, "bm25": 0.24}  # values picked by `python -m docqa.evaluate` (calibration set)


@dataclass
class Answer:
    question: str
    found: bool
    answer: str
    score: float
    chunk: Optional[Chunk]  # best chunk even when below threshold (useful for debugging)
    runners_up: List[Chunk]

    @property
    def citation(self) -> str:
        return self.chunk.cite if self.found and self.chunk else "-"


def best_sentence(question: str, passage: str) -> str:
    """Extractive 'answer': the sentence sharing the most query terms with the question."""
    q = set(tokenize(question))
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", passage) if s]
    return max(sentences, key=lambda s: len(q & set(tokenize(s))))


class KnowledgeBase:
    def __init__(self, docs_dir: Path, retriever: str = "tfidf", threshold: Optional[float] = None):
        self.chunks: List[Chunk] = chunk_documents(load_documents(docs_dir))
        texts = [c.text for c in self.chunks]
        self.retriever = {"tfidf": TfidfRetriever, "bm25": BM25Retriever}[retriever](texts)
        self.threshold = DEFAULT_THRESHOLD[retriever] if threshold is None else threshold

    def ask(self, question: str, k: int = 3) -> Answer:
        hits = self.retriever.search(question, k=k)
        top_idx, top_score = hits[0]
        chunk = self.chunks[top_idx]
        found = top_score >= self.threshold
        return Answer(
            question=question,
            found=found,
            answer=best_sentence(question, chunk.text) if found else NOT_FOUND,
            score=top_score,
            chunk=chunk,
            runners_up=[self.chunks[i] for i, _ in hits[1:]],
        )
