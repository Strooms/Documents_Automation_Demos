"""Calibrate the not-found threshold on a SEPARATE question set, then score the 10 test questions.

    python -m docqa.evaluate            # writes output/results.json and output/results.md

A test question passes if
  - answerable:   an answer is returned, the top-1 chunk is from the expected document,
                  and it contains the expected fact string;
  - unanswerable: the system answers 'Not found'.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .qa import KnowledgeBase

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "data" / "docs"


def is_correct(kb: KnowledgeBase, item: Dict) -> Dict:
    ans = kb.ask(item["question"])
    if item["expected_doc"] is None:
        ok = not ans.found
    else:
        ok = bool(ans.found and ans.chunk.doc == item["expected_doc"] and item["expected_fact"] in ans.chunk.text)
    in_top3 = item["expected_fact"] is not None and any(
        item["expected_fact"] in c.text for c in [ans.chunk] + ans.runners_up
    )
    # did retrieval itself find the right chunk, regardless of the not-found threshold?
    retrieved = item["expected_fact"] is not None and item["expected_fact"] in ans.chunk.text
    return {"ans": ans, "ok": ok, "in_top3": in_top3, "retrieved_top1": retrieved}


def calibrate(retriever: str, items: List[Dict]) -> float:
    """Pick the threshold with the best accuracy on the calibration set (median of the best plateau)."""
    kb = KnowledgeBase(DOCS, retriever)
    best, best_acc = [], -1.0
    for t in (x / 100 for x in range(2, 80)):
        kb.threshold = t
        acc = sum(is_correct(kb, it)["ok"] for it in items) / len(items)
        if acc > best_acc + 1e-9:
            best, best_acc = [t], acc
        elif abs(acc - best_acc) < 1e-9:
            best.append(t)
    return round(best[len(best) // 2], 2)


def main() -> int:
    calib = json.loads((ROOT / "data" / "calibration_questions.json").read_text(encoding="utf-8"))
    tests = json.loads((ROOT / "data" / "test_questions.json").read_text(encoding="utf-8"))
    results: Dict[str, Dict] = {}
    for name in ("tfidf", "bm25"):
        threshold = calibrate(name, calib)
        kb = KnowledgeBase(DOCS, name, threshold)
        rows = []
        for item in tests:
            r = is_correct(kb, item)
            a = r["ans"]
            rows.append({
                "id": item["id"], "question": item["question"],
                "expected": item["expected_doc"] or "NOT FOUND",
                "got": a.chunk.doc if a.found else "NOT FOUND",
                "citation": a.citation, "score": round(a.score, 3),
                "answer": a.answer, "pass": r["ok"], "fact_in_top3": r["in_top3"],
                "right_chunk_ranked_first": r["retrieved_top1"],
            })
        results[name] = {"threshold": threshold, "passed": sum(r["pass"] for r in rows), "total": len(rows), "rows": rows}

    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    for name, res in results.items():
        lines += [f"### {name} (not-found threshold {res['threshold']}, chosen on the separate calibration set) "
                  f"- **{res['passed']}/{res['total']} passed**", "",
                  "| # | Question | Expected | Got | Top score | Right chunk ranked #1? | Result |",
                  "|---|---|---|---|---|---|---|"]
        for r in res["rows"]:
            lines.append(f"| {r['id']} | {r['question']} | {r['expected']} | {r['got']} | {r['score']} | "
                         f"{'yes' if r['right_chunk_ranked_first'] else ('no' if r['expected'] != 'NOT FOUND' else 'n/a')} | "
                         f"{'PASS' if r['pass'] else '**FAIL**'} |")
        lines.append("")
    (out / "results.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    for r in results["tfidf"]["rows"]:
        print(f"[{r['id']:>2}] {r['question']}\n     -> {r['answer']}  ({r['citation']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
