"""Balance reconciliation: per-row running balance and statement-level totals."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from .parser import Statement

ZERO = Decimal("0")
TOL = Decimal("0.005")


def reconcile(stmt: Statement) -> Dict:
    """Return a report dict; also sets `.check` on each transaction's row result.

    Row check:   previous printed balance + credit - debit == printed balance
    Total check: opening + sum(credits) - sum(debits) == closing
    """
    rows: List[Dict] = []
    prev = stmt.opening_balance
    for i, t in enumerate(stmt.transactions):
        if prev is None or t.balance is None:
            status, diff = "UNCHECKED", None
        else:
            expected = prev + (t.credit or ZERO) - (t.debit or ZERO)
            diff = t.balance - expected
            status = "OK" if abs(diff) <= TOL else "MISMATCH"
        rows.append({"index": i, "date": t.date, "description": t.description, "status": status,
                     "difference": str(diff) if diff is not None else None})
        prev = t.balance if t.balance is not None else prev

    debits = sum((t.debit or ZERO for t in stmt.transactions), ZERO)
    credits = sum((t.credit or ZERO for t in stmt.transactions), ZERO)
    total_status, total_diff = "UNCHECKED", None
    if stmt.opening_balance is not None and stmt.closing_balance is not None:
        expected_close = stmt.opening_balance + credits - debits
        total_diff = stmt.closing_balance - expected_close
        total_status = "OK" if abs(total_diff) <= TOL else "MISMATCH"

    bad = [r for r in rows if r["status"] == "MISMATCH"]
    return {
        "source_file": stmt.source_file,
        "layout": stmt.layout,
        "transactions": len(stmt.transactions),
        "opening_balance": str(stmt.opening_balance) if stmt.opening_balance is not None else None,
        "closing_balance": str(stmt.closing_balance) if stmt.closing_balance is not None else None,
        "total_debits": str(debits),
        "total_credits": str(credits),
        "total_check": total_status,
        "total_difference": str(total_diff) if total_diff is not None else None,
        "row_mismatches": bad,
        "row_status": [r["status"] for r in rows],
        "overall": "OK" if total_status == "OK" and not bad else "NEEDS_REVIEW",
    }
