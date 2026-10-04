"""Command line: parse every PDF in a folder -> one Sheets-ready CSV + reconciliation report."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import List

from .parser import parse_statement
from .reconcile import reconcile

COLUMNS = ["date", "description", "debit", "credit", "balance", "source_file", "balance_check"]


def _num(x) -> str:
    return "" if x is None else f"{x:.2f}"


def write_csv(path: Path, rows: List[dict]) -> None:
    """Plain UTF-8 CSV: ISO dates, '.' decimals, no thousands separators, blank = empty cell.

    That is what Google Sheets (File > Import) parses without locale surprises.
    """
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def run(input_dir: Path, output_dir: Path) -> List[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports, all_rows = [], []
    for pdf in sorted(input_dir.glob("*.pdf")):
        stmt = parse_statement(str(pdf))
        report = reconcile(stmt)
        reports.append(report)
        rows = [{
            "date": t.date, "description": t.description, "debit": _num(t.debit), "credit": _num(t.credit),
            "balance": _num(t.balance), "source_file": t.source_file, "balance_check": status,
        } for t, status in zip(stmt.transactions, report["row_status"])]
        write_csv(output_dir / f"{pdf.stem}.csv", rows)
        all_rows += rows
    write_csv(output_dir / "all_transactions.csv", all_rows)
    (output_dir / "reconciliation.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    return reports


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    args = ap.parse_args(argv)
    for r in run(args.input_dir, args.output_dir):
        print(f"{r['source_file']:<40} {r['layout']:<14} txns={r['transactions']:<3} "
              f"opening={r['opening_balance']} closing={r['closing_balance']} "
              f"total_check={r['total_check']} row_mismatches={len(r['row_mismatches'])} -> {r['overall']}")
        for bad in r["row_mismatches"]:
            print(f"    ! row {bad['index']} {bad['date']} {bad['description'][:40]!r}: off by {bad['difference']}")
    return 0
