import argparse
from pathlib import Path

from .qa import KnowledgeBase

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="docqa")
    ap.add_argument("question")
    ap.add_argument("--docs", type=Path, default=ROOT / "data" / "docs")
    ap.add_argument("--retriever", choices=["tfidf", "bm25"], default="tfidf")
    ap.add_argument("--threshold", type=float, default=None)
    args = ap.parse_args(argv)
    ans = KnowledgeBase(args.docs, args.retriever, args.threshold).ask(args.question)
    print(f"Q: {ans.question}\nA: {ans.answer}\nscore={ans.score:.3f}  source: {ans.citation}")
    if ans.found:
        print(f"passage: {ans.chunk.text}")
    return 0
