"""Command line: extract every PDF in a folder, validate, write JSON + CSV."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .extract import extract_invoice
from .validate import validate_invoice

SUMMARY_COLS = [
    "source_file", "extraction_method", "vendor", "invoice_number", "invoice_date", "currency",
    "subtotal", "tax", "total", "line_item_count", "validation_status", "validation_issues",
]
ITEM_COLS = [
    "source_file", "invoice_number", "vendor", "invoice_date", "currency",
    "description", "quantity", "unit_price", "amount",
]


def run(input_dir: Path, output_dir: Path) -> list:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for pdf in sorted(input_dir.glob("*.pdf")):
        inv = extract_invoice(str(pdf))
        inv["validation"] = validate_invoice(inv)
        results.append(inv)

    (output_dir / "invoices.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    with open(output_dir / "invoices_summary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUMMARY_COLS)
        w.writeheader()
        for inv in results:
            w.writerow({
                **{c: inv.get(c) for c in SUMMARY_COLS if c in inv},
                "line_item_count": len(inv["line_items"]),
                "validation_status": inv["validation"]["status"],
                "validation_issues": " | ".join(inv["validation"]["issues"]),
            })

    with open(output_dir / "line_items.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ITEM_COLS)
        w.writeheader()
        for inv in results:
            for it in inv["line_items"]:
                w.writerow({**{c: inv.get(c) for c in ITEM_COLS if c in inv}, **it})
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_dir", type=Path, help="folder containing invoice PDFs")
    ap.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    args = ap.parse_args(argv)
    results = run(args.input_dir, args.output_dir)
    for inv in results:
        v = inv["validation"]
        print(f"{inv['source_file']:<28} {inv['extraction_method']:<5} "
              f"{inv['invoice_number']!s:<16} total={inv['total']!s:<10} {v['status']}")
        for issue in v["issues"]:
            print(f"    ! {issue}")
    return 0
