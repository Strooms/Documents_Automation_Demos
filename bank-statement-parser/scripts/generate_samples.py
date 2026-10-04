"""Generate synthetic bank statements (2 layouts, 3 PDFs) + ground-truth CSVs.

  statement_bankA_jan2026.pdf        single signed "Amount" column, 'DD Mon YYYY' dates, 2 pages
  statement_bankB_feb2026.pdf        separate Debit / Credit columns, 'DD/MM/YYYY' dates, wrapped descriptions
  tampered/statement_bankB_feb2026_tampered.pdf   same as B but ONE debit printed with swapped digits
                                         (to show that reconciliation catches it)

Everything is invented; the random seed is fixed so runs are reproducible.
Usage: python scripts/generate_samples.py
"""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent.parent / "samples"
W, H = 595, 842

MERCHANTS = [
    ("GROCERY MART #102", 20, 95), ("CAFE LUNA POS 4417", 4, 15), ("UTILITY CO ELECTRIC BILL", 60, 140),
    ("STREAMING SERVICE MONTHLY", 8, 16), ("FUEL STOP 22 CARD PURCHASE", 25, 70),
    ("ONLINE BOOKSTORE ORDER 88213 (SYNTHETIC)", 12, 60), ("PHARMACY EXAMPLE", 5, 40),
    ("TRANSFER TO SAVINGS 0000-2222", 100, 400), ("GYM MEMBERSHIP FEE", 30, 30),
]
CREDITS = [("SALARY ACME DEMO CORP", 2200, 2600), ("REFUND ONLINE BOOKSTORE", 10, 60),
           ("TRANSFER FROM SAVINGS 0000-2222", 50, 300), ("INTEREST PAID", 1, 4)]


@dataclass
class Txn:
    day: date
    description: str
    debit: Optional[Decimal]
    credit: Optional[Decimal]
    balance: Decimal


def make_transactions(seed: int, start: date, n: int, opening: Decimal) -> List[Txn]:
    rng = random.Random(seed)
    txns, bal, day = [], opening, start
    for _ in range(n):
        day += timedelta(days=rng.choice([0, 1, 1, 2]))
        if rng.random() < 0.22:
            desc, lo, hi = rng.choice(CREDITS)
            amt = Decimal(rng.randint(lo * 100, hi * 100)) / 100
            bal += amt
            txns.append(Txn(day, desc, None, amt, bal))
        else:
            desc, lo, hi = rng.choice(MERCHANTS)
            amt = Decimal(rng.randint(lo * 100, hi * 100)) / 100
            bal -= amt
            txns.append(Txn(day, desc, amt, None, bal))
    return txns


def m(x: Decimal) -> str:
    return f"{x:,.2f}"


def swap_digits(x: Decimal) -> str:
    """'45.60' -> '54.60' style transposition for the tampered sample."""
    s = f"{x:,.2f}"
    digits = [i for i, ch in enumerate(s) if ch.isdigit()]
    i, j = digits[0], digits[1]
    chars = list(s)
    chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def _footer(c, page, pages, label):
    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, 30, f"{label} - Page {page} of {pages}")


def draw_bank_a(path: Path, txns: List[Txn], opening: Decimal) -> None:
    per_page, pages = 22, 2
    c = canvas.Canvas(str(path), pagesize=(W, H))
    for p in range(pages):
        y = H - 60
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, "SAMPLE BANK A - Statement of Account")
        c.setFont("Helvetica", 9)
        if p == 0:
            c.drawString(40, y - 16, "Account: 0000-1111 (synthetic)   Period: 01 Jan 2026 - 31 Jan 2026")
            c.drawString(40, y - 30, "Account holder: Demo Customer")
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y - 56, "Opening Balance")
            c.drawRightString(545, y - 56, m(opening))
            c.drawString(40, y - 70, "Closing Balance")
            c.drawRightString(545, y - 70, m(txns[-1].balance))
            y -= 100
        else:
            y -= 40
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, "Date"); c.drawString(120, y, "Description")
        c.drawRightString(430, y, "Amount"); c.drawRightString(545, y, "Balance")
        c.line(40, y - 4, 545, y - 4)
        c.setFont("Helvetica", 9)
        for t in txns[p * per_page:(p + 1) * per_page]:
            y -= 18
            amount = -t.debit if t.debit else t.credit
            c.drawString(40, y, t.day.strftime("%d %b %Y")); c.drawString(120, y, t.description)
            c.drawRightString(430, y, f"{amount:,.2f}"); c.drawRightString(545, y, m(t.balance))
        _footer(c, p + 1, pages, "Sample Bank A (synthetic)")
        c.showPage()
    c.save()


def draw_bank_b(path: Path, txns: List[Txn], opening: Decimal, tamper_index: Optional[int] = None) -> None:
    c = canvas.Canvas(str(path), pagesize=(W, H))
    y = H - 60
    c.setFont("Helvetica-Bold", 15)
    c.drawString(40, y, "EXAMPLE CREDIT UNION - Account Statement")
    c.setFont("Helvetica", 9)
    c.drawString(40, y - 16, "Member: Demo Customer   Account 0000-3333 (synthetic)   Statement date 28/02/2026")
    y -= 50
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Date"); c.drawString(105, y, "Details")
    c.drawRightString(400, y, "Debit"); c.drawRightString(470, y, "Credit"); c.drawRightString(550, y, "Balance")
    c.line(40, y - 4, 555, y - 4)
    c.setFont("Helvetica", 9)
    y -= 18
    c.drawString(105, y, "Opening Balance"); c.drawRightString(550, y, m(opening))
    for i, t in enumerate(txns):
        y -= 18
        words = t.description.split()
        first, second = t.description, None
        if len(t.description) > 26:  # wrap long descriptions onto a second line
            cut = len(words) // 2
            first, second = " ".join(words[:cut]), " ".join(words[cut:])
        c.drawString(40, y, t.day.strftime("%d/%m/%Y")); c.drawString(105, y, first)
        if t.debit:
            c.drawRightString(400, y, swap_digits(t.debit) if i == tamper_index else m(t.debit))
        if t.credit:
            c.drawRightString(470, y, m(t.credit))
        c.drawRightString(550, y, m(t.balance))
        if second:
            y -= 12
            c.drawString(105, y, second)
    y -= 26
    c.setFont("Helvetica-Bold", 9)
    c.drawString(105, y, "Closing Balance"); c.drawRightString(550, y, m(txns[-1].balance))
    _footer(c, 1, 1, "Example Credit Union (synthetic)")
    c.save()


def write_truth(path: Path, txns: List[Txn]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "description", "debit", "credit", "balance"])
        for t in txns:
            w.writerow([t.day.isoformat(), t.description,
                        f"{t.debit:.2f}" if t.debit else "", f"{t.credit:.2f}" if t.credit else "", f"{t.balance:.2f}"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    a_open, b_open = Decimal("5000.00"), Decimal("1840.35")
    a = make_transactions(1, date(2026, 1, 2), 36, a_open)
    b = make_transactions(2, date(2026, 2, 2), 24, b_open)
    draw_bank_a(OUT / "statement_bankA_jan2026.pdf", a, a_open)
    draw_bank_b(OUT / "statement_bankB_feb2026.pdf", b, b_open)
    tamper = next(i for i, t in enumerate(b) if t.debit and t.debit >= 10 and f"{t.debit:.2f}"[0] != f"{t.debit:.2f}"[1])
    (OUT / "tampered").mkdir(exist_ok=True)
    draw_bank_b(OUT / "tampered" / "statement_bankB_feb2026_tampered.pdf", b, b_open, tamper_index=tamper)
    write_truth(OUT / "truth_bankA_jan2026.csv", a)
    write_truth(OUT / "truth_bankB_feb2026.csv", b)
    print(f"wrote 3 PDFs + 2 truth CSVs ({len(a)} + {len(b)} transactions); tampered row index = {tamper}")

    import pymupdf  # PNG preview for the README
    for name in ("statement_bankA_jan2026", "statement_bankB_feb2026"):
        with pymupdf.open(OUT / f"{name}.pdf") as doc:
            doc[0].get_pixmap(dpi=60).save(OUT / f"preview_{name}.png")


if __name__ == "__main__":
    main()
