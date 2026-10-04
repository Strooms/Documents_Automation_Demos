import csv
from decimal import Decimal
from pathlib import Path

import pytest

from bank_parser import parse_statement, reconcile
from bank_parser.cli import COLUMNS, run

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def load_truth(name):
    with open(SAMPLES / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def d(x):
    return Decimal(x) if x not in ("", None) else None


@pytest.mark.parametrize("pdf,truth,layout", [
    ("statement_bankA_jan2026.pdf", "truth_bankA_jan2026.csv", "signed-amount"),
    ("statement_bankB_feb2026.pdf", "truth_bankB_feb2026.csv", "debit-credit"),
])
def test_transactions_match_ground_truth(pdf, truth, layout):
    stmt = parse_statement(str(SAMPLES / pdf))
    rows = load_truth(truth)
    assert stmt.layout == layout
    assert len(stmt.transactions) == len(rows)
    for t, r in zip(stmt.transactions, rows):
        assert (t.date, t.description) == (r["date"], r["description"])
        assert (t.debit, t.credit, t.balance) == (d(r["debit"]), d(r["credit"]), d(r["balance"]))


def test_multi_page_statement_is_fully_read():
    stmt = parse_statement(str(SAMPLES / "statement_bankA_jan2026.pdf"))
    assert {t.page for t in stmt.transactions} == {1, 2}


def test_clean_statements_reconcile():
    for name in ("statement_bankA_jan2026.pdf", "statement_bankB_feb2026.pdf"):
        report = reconcile(parse_statement(str(SAMPLES / name)))
        assert report["overall"] == "OK" and report["row_mismatches"] == []


def test_tampered_statement_is_flagged():
    report = reconcile(parse_statement(str(SAMPLES / "tampered" / "statement_bankB_feb2026_tampered.pdf")))
    assert report["overall"] == "NEEDS_REVIEW"
    assert report["total_check"] == "MISMATCH"
    assert [r["index"] for r in report["row_mismatches"]] == [1]


def test_csv_is_sheets_ready(tmp_path):
    run(SAMPLES, tmp_path)
    with open(tmp_path / "all_transactions.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0].keys()) == COLUMNS
    for r in rows:
        assert len(r["date"]) == 10 and r["date"][4] == "-"          # ISO date
        for col in ("debit", "credit", "balance"):
            assert "," not in r[col]                                  # no thousands separators
        assert bool(r["debit"]) != bool(r["credit"])                  # exactly one of debit/credit
