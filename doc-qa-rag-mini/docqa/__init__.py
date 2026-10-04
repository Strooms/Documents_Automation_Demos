"""A tiny local retrieval-QA pipeline: chunk -> TF-IDF/BM25 -> cited extractive answer."""
from .qa import Answer, KnowledgeBase  # noqa: F401
