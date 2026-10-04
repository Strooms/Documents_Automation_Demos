from pathlib import Path

import pytest

from docqa.chunker import chunk_documents
from docqa.loader import load_documents
from docqa.qa import NOT_FOUND, KnowledgeBase
from docqa.retrievers import stem, tokenize

DOCS = Path(__file__).resolve().parent.parent / "data" / "docs"


@pytest.fixture(scope="module")
def chunks():
    return chunk_documents(load_documents(DOCS))


def test_all_ten_documents_are_loaded(chunks):
    assert len({c.doc for c in chunks}) == 10
    assert {c.doc.rsplit(".", 1)[1] for c in chunks} == {"md", "txt", "pdf"}


def test_headings_stay_attached_to_their_paragraph(chunks):
    leave = [c for c in chunks if c.doc == "leave_policy.md" and "18 days" in c.text]
    assert leave and "Annual leave" in leave[0].text


def test_tokenizer_keeps_codes_and_normalises_plurals():
    assert "tn-12" in tokenize("Error TN-12 means ...")
    assert stem("days") == stem("day")


@pytest.mark.parametrize("retriever", ["tfidf", "bm25"])
def test_cited_answer(retriever):
    kb = KnowledgeBase(DOCS, retriever, threshold=0.2)
    ans = kb.ask("What does error TN-12 mean in the VPN client?")
    assert ans.found and "certificate" in ans.answer
    assert ans.citation.startswith("vpn_setup.txt, page 1, chunk")


@pytest.mark.parametrize("retriever", ["tfidf", "bm25"])
def test_nonsense_question_is_not_found(retriever):
    ans = KnowledgeBase(DOCS, retriever, threshold=0.2).ask("zzqx blorft wibble")
    assert not ans.found and ans.answer == NOT_FOUND and ans.citation == "-"
