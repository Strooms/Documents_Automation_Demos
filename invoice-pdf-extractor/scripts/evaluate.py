"""Compare extraction output with the generator's ground truth (synthetic files only)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from invoice_extractor import extract_invoice, validate_invoice  # noqa: E402

FIELDS = ["vendor", "invoice_number", "invoice_date", "currency", "subtotal", "tax", "total"]


def main() -> int:
    truth = json.loads((ROOT / "samples" / "expected.json").read_text(encoding="utf-8"))
    hit = tot = 0
    print(f"{'file':<36}" + "".join(f"{f[:9]:>11}" for f in FIELDS) + "   items  validation")
    for name, exp in truth.items():
        inv = extract_invoice(str(ROOT / "samples" / name))
        status = validate_invoice(inv)["status"]
        marks = []
        for f in FIELDS:
            ok = inv[f] == exp[f]
            hit, tot = hit + ok, tot + 1
            marks.append("ok" if ok else "WRONG")
        n_ok = len(inv["line_items"]) == exp["line_item_count"]
        hit, tot = hit + n_ok, tot + 1
        v_ok = status == exp["expected_validation"]
        hit, tot = hit + v_ok, tot + 1
        print(f"{name:<36}" + "".join(f"{m:>11}" for m in marks)
              + f"   {'ok' if n_ok else 'WRONG':<6} {status} ({'ok' if v_ok else 'WRONG'})")
    print(f"\n{hit}/{tot} checks matched ground truth on {len(truth)} synthetic files")
    return 0 if hit == tot else 1


if __name__ == "__main__":
    raise SystemExit(main())
