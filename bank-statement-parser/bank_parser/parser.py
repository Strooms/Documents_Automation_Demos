"""Column-aware parsing of bank statement PDFs.

Instead of splitting text lines on whitespace (which cannot tell a debit from a credit when only
one amount is printed), we use word coordinates from pdfplumber: the header row ("Date",
"Description"/"Details", "Debit", "Credit" or "Amount", "Balance") defines the columns, and every
amount-looking word is assigned to the header column whose right edge is closest.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

import pdfplumber

AMOUNT_WORD = re.compile(r"^-?\d{1,3}(?:,\d{3})*\.\d{2}$|^-?\d+\.\d{2}$")
DATE_FORMATS = ("%d %b %Y", "%d/%m/%Y", "%Y-%m-%d")  # all-numeric dates are read day-first
NUMERIC_HEADERS = {"debit", "credit", "amount", "balance"}
DESC_HEADERS = {"description", "details", "narrative"}
SKIP_LINE = re.compile(r"page\s+\d+\s+of\s+\d+|opening balance|closing balance|continued", re.I)
LABELLED_BALANCE = re.compile(r"^(opening|closing)\s+balance\b.*?(-?\d[\d,]*\.\d{2})\s*$", re.I)
MAX_COLUMN_DISTANCE = 30  # points between an amount's right edge and its header's right edge


@dataclass
class Transaction:
    date: str  # ISO
    description: str
    debit: Optional[Decimal]
    credit: Optional[Decimal]
    balance: Optional[Decimal]
    source_file: str = ""
    page: int = 1


@dataclass
class Statement:
    source_file: str
    layout: str  # 'signed-amount' or 'debit-credit'
    opening_balance: Optional[Decimal]
    closing_balance: Optional[Decimal]
    transactions: List[Transaction] = field(default_factory=list)


def _to_decimal(word: str) -> Decimal:
    return Decimal(word.replace(",", ""))


def _parse_date(text: str) -> Optional[str]:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _group_lines(words: List[dict], tolerance: float = 3.0) -> List[List[dict]]:
    """Group words into visual lines by their vertical position."""
    lines: List[List[dict]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= tolerance:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(ln, key=lambda w: w["x0"]) for ln in lines]


@dataclass
class _Columns:
    desc_x0: float
    numeric: Dict[str, float]  # header name -> right edge (x1)

    @property
    def layout(self) -> str:
        return "debit-credit" if "debit" in self.numeric else "signed-amount"


def _read_header(line: List[dict]) -> Optional[_Columns]:
    names = {w["text"].lower(): w for w in line}
    if "date" not in names or "balance" not in names:
        return None
    desc = next((names[n] for n in DESC_HEADERS if n in names), None)
    numeric = {n: names[n]["x1"] for n in NUMERIC_HEADERS if n in names}
    if desc is None or len(numeric) < 2:
        return None
    return _Columns(desc_x0=desc["x0"], numeric=numeric)


def _nearest_column(word: dict, cols: _Columns) -> Optional[str]:
    name, dist = min(((n, abs(word["x1"] - x1)) for n, x1 in cols.numeric.items()), key=lambda t: t[1])
    return name if dist <= MAX_COLUMN_DISTANCE else None


def parse_statement(path: str) -> Statement:
    stmt = Statement(source_file=path.split("/")[-1], layout="unknown", opening_balance=None, closing_balance=None)
    cols: Optional[_Columns] = None
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            last: Optional[Transaction] = None
            for line in _group_lines(page.extract_words()):
                text = " ".join(w["text"] for w in line)

                m = LABELLED_BALANCE.match(text)
                if m:
                    value = _to_decimal(m.group(2))
                    if m.group(1).lower() == "opening":
                        stmt.opening_balance = value
                    else:
                        stmt.closing_balance = value
                    last = None
                    continue

                header = _read_header(line)
                if header:
                    cols = header
                    stmt.layout = cols.layout
                    last = None
                    continue
                if cols is None:
                    continue  # still above the table

                date_words = [w for w in line if w["x1"] <= cols.desc_x0 + 1]
                iso = _parse_date(" ".join(w["text"] for w in date_words)) if date_words else None

                if iso:
                    stmt.transactions.append(last := _build_transaction(line, cols, iso, stmt.source_file, page_no))
                elif last is not None and not SKIP_LINE.search(text) and not any(
                    AMOUNT_WORD.match(w["text"]) for w in line
                ):
                    last.description += " " + text  # wrapped description line
                else:
                    last = None
    return stmt


def _build_transaction(line: List[dict], cols: _Columns, iso: str, source: str, page_no: int) -> Transaction:
    values: Dict[str, Decimal] = {}
    desc_words = []
    for w in line:
        if w["x1"] <= cols.desc_x0 + 1:
            continue  # date column
        column = _nearest_column(w, cols) if AMOUNT_WORD.match(w["text"]) else None
        if column:
            values[column] = _to_decimal(w["text"])
        else:
            desc_words.append(w["text"])

    debit = credit = None
    if cols.layout == "debit-credit":
        debit, credit = values.get("debit"), values.get("credit")
    elif "amount" in values:
        amount = values["amount"]
        debit, credit = (-amount, None) if amount < 0 else (None, amount)
    return Transaction(iso, " ".join(desc_words), debit, credit, values.get("balance"), source, page_no)
