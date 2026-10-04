"""Rule-based field extraction from invoice text."""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from .ocr import read_pdf_text
from .parsing import DATE_RE, MONEY, MONEY_RE, detect_currency, parse_amount, parse_date

_TITLE_WORDS = re.compile(r"\b(tax\s+invoice|invoice|rechnung)\b", re.I)
# key/value fragments that can share a text line with the vendor name in two-column layouts
_META_FRAGMENT = re.compile(
    r"(invoice\s*(?:no\.?|number|#)\s*[:#]?\s*\S+|(?:invoice\s+)?date\s*:?\s*" + DATE_RE.pattern + ")", re.I
)
_COMPANY_SUFFIX = re.compile(r"\b(ltd|llc|inc|gmbh|co\.?|corp|bv|pt|plc)\b\.?", re.I)

_INVOICE_NO = re.compile(
    r"(?:invoice\s*(?:no\.?|number|#)|inv\s*#|invoice\s*:)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]*)", re.I
)
_DATE_LABEL = re.compile(r"\b(date|issued)\b", re.I)

_SUBTOTAL = re.compile(r"^(sub\s?-?total|net(?:\s+amount)?)\b", re.I)
_TAX = re.compile(r"^(?:sales\s+)?(tax|vat|gst)\b", re.I)
_TOTAL = re.compile(r"^(grand\s+total|total(?:\s+due)?|amount\s+due|balance\s+due)\b", re.I)
_TRAILING_MONEY = re.compile(rf"({MONEY})\s*$")

_ITEM_DESC_FIRST = re.compile(
    rf"^(?P<desc>.+?)\s+(?P<qty>\d+(?:\.\d+)?)\s+(?P<unit>{MONEY})\s+(?P<amount>{MONEY})$"
)
_ITEM_QTY_FIRST = re.compile(
    rf"^(?P<qty>\d+(?:\.\d+)?)\s+(?P<desc>.+?)\s+(?P<unit>{MONEY})\s+(?P<amount>{MONEY})$"
)


def _lines(text: str) -> List[str]:
    return [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines() if ln.strip()]


def _find_vendor(lines: List[str]) -> Optional[str]:
    """Label first ('From:'), then first line with a company suffix, then first non-title line."""
    for i, ln in enumerate(lines):
        m = re.match(r"^(?:from|seller|vendor|supplier)\s*:\s*(.*)$", ln, re.I)
        if m:
            return m.group(1).strip() or (lines[i + 1] if i + 1 < len(lines) else None)
    candidates = []
    for ln in lines[:12]:
        cleaned = _TITLE_WORDS.sub("", _META_FRAGMENT.sub("", ln)).strip(" /-:")
        if cleaned and not re.match(r"^bill\s*to\b", cleaned, re.I):
            candidates.append(cleaned)
    for c in candidates:
        if _COMPANY_SUFFIX.search(c):
            return c
    return candidates[0] if candidates else None


def _find_invoice_number(lines: List[str]) -> Optional[str]:
    for ln in lines:
        m = _INVOICE_NO.search(ln)
        if m:
            return m.group(1)
    return None


def _find_date(lines: List[str]) -> Optional[str]:
    """Prefer a labelled 'Date'/'Issued' line (never 'Due date'); else the first date found."""
    for ln in lines:
        if _DATE_LABEL.search(ln) and not re.search(r"\bdue\b", ln, re.I):
            m = DATE_RE.search(ln)
            if m and parse_date(m.group(0)):
                return parse_date(m.group(0))
    for ln in lines:
        if not re.search(r"\bdue\b", ln, re.I):
            m = DATE_RE.search(ln)
            if m and parse_date(m.group(0)):
                return parse_date(m.group(0))
    return None


def _money_at_end(line: str) -> Optional[Decimal]:
    m = _TRAILING_MONEY.search(line)
    return parse_amount(m.group(1)) if m else None


def _find_totals(lines: List[str]) -> Dict[str, Optional[Decimal]]:
    out: Dict[str, Optional[Decimal]] = {"subtotal": None, "tax": None, "total": None}
    for ln in lines:
        value = _money_at_end(ln)
        if value is None:
            continue
        if _SUBTOTAL.match(ln):
            out["subtotal"] = value
        elif _TAX.match(ln):
            out["tax"] = value
        elif _TOTAL.match(ln):
            out["total"] = value  # last match wins (grand total is printed last)
    return out


def _is_totals_line(ln: str) -> bool:
    return bool(_SUBTOTAL.match(ln) or _TAX.match(ln) or _TOTAL.match(ln))


def _find_line_items(lines: List[str]) -> List[Dict]:
    """Parse table rows between the table header and the first totals line."""
    qty_first = False
    start = 0
    for i, ln in enumerate(lines):
        qty = re.search(r"\b(qty|quantity)\b", ln, re.I)
        name = re.search(r"\b(description|item)\b", ln, re.I)
        if qty and name:  # this is the table header row
            start = i + 1
            qty_first = qty.start() < name.start()
            break
    items = []
    for ln in lines[start:]:
        if _is_totals_line(ln):
            break
        m = (_ITEM_QTY_FIRST if qty_first else _ITEM_DESC_FIRST).match(ln)
        if m:
            items.append(
                {
                    "description": m["desc"].strip(),
                    "quantity": float(m["qty"]),
                    "unit_price": float(parse_amount(m["unit"])),
                    "amount": float(parse_amount(m["amount"])),
                }
            )
    return items


def parse_invoice_text(text: str) -> Dict:
    lines = _lines(text)
    totals = _find_totals(lines)
    tax_rate = None
    for ln in lines:
        if _TAX.match(ln):
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", ln)
            if m:
                tax_rate = float(m.group(1).replace(",", "."))
    return {
        "vendor": _find_vendor(lines),
        "invoice_number": _find_invoice_number(lines),
        "invoice_date": _find_date(lines),
        "currency": detect_currency(text),
        "line_items": _find_line_items(lines),
        "subtotal": float(totals["subtotal"]) if totals["subtotal"] is not None else None,
        "tax_rate_percent": tax_rate,
        "tax": float(totals["tax"]) if totals["tax"] is not None else None,
        "total": float(totals["total"]) if totals["total"] is not None else None,
    }


def extract_invoice(pdf_path: str) -> Dict:
    """Extract one invoice PDF into a dict (adds source_file and extraction_method)."""
    text, method = read_pdf_text(str(pdf_path))
    result = parse_invoice_text(text)
    return {"source_file": Path(pdf_path).name, "extraction_method": method, **result}
