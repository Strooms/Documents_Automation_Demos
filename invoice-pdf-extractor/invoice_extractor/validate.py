"""Arithmetic and completeness checks on an extracted invoice."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

TOLERANCE = Decimal("0.01")
REQUIRED = ("vendor", "invoice_number", "invoice_date", "total")


def _d(value) -> Decimal:
    return Decimal(str(value))


def validate_invoice(inv: Dict) -> Dict:
    """Return {'status': 'OK'|'FLAGGED', 'issues': [...]}.

    Checks: required fields, qty*unit == amount per line, sum(lines) vs subtotal,
    and subtotal + tax vs total.
    """
    issues: List[str] = [f"missing_field:{f}" for f in REQUIRED if inv.get(f) in (None, "")]
    items = inv.get("line_items") or []
    if not items:
        issues.append("no_line_items_found")

    for n, it in enumerate(items, start=1):
        expected = _d(it["quantity"]) * _d(it["unit_price"])
        if abs(expected - _d(it["amount"])) > TOLERANCE:
            issues.append(f"line_{n}_amount_mismatch: {it['quantity']} x {it['unit_price']} != {it['amount']}")

    items_sum = sum((_d(it["amount"]) for it in items), Decimal("0"))
    subtotal = inv.get("subtotal")
    if items and subtotal is not None and abs(items_sum - _d(subtotal)) > TOLERANCE:
        issues.append(f"line_items_sum_mismatch: items sum {items_sum} != subtotal {subtotal}")

    base = _d(subtotal) if subtotal is not None else (items_sum if items else None)
    if base is not None and inv.get("total") is not None:
        expected_total = base + (_d(inv["tax"]) if inv.get("tax") is not None else Decimal("0"))
        if abs(expected_total - _d(inv["total"])) > TOLERANCE:
            issues.append(f"total_mismatch: expected {expected_total} but document says {inv['total']}")

    return {"status": "OK" if not issues else "FLAGGED", "issues": issues}
