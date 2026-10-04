"""Small parsing helpers: money, dates, currency."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

# A money token always ends in a 2-digit fraction (e.g. 1,234.50 or 1.234,50).
MONEY = r"(?:[$€£]\s?)?\d[\d.,]*[.,]\d{2}"
MONEY_RE = re.compile(MONEY)

# Day-first is assumed for all-numeric dates with "/" or "." (documented limitation).
_DATE_FORMATS = ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%d.%m.%Y")
DATE_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}"
    r"|\d{1,2}[/.]\d{1,2}[/.]\d{4}"
)


def parse_amount(token: str) -> Decimal:
    """Parse '1,234.50', '1.234,50', '$ 12.00' ... into a Decimal.

    The last separator is treated as the decimal mark (MONEY guarantees 2 decimals).
    """
    s = re.sub(r"[^\d.,-]", "", token)
    sep = max(s.rfind(","), s.rfind("."))
    integer = re.sub(r"[.,]", "", s[:sep])
    return Decimal(f"{integer}.{s[sep + 1:]}")


def parse_date(text: str) -> Optional[str]:
    """Return an ISO date (YYYY-MM-DD) or None."""
    text = re.sub(r"\s+", " ", text.strip())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def detect_currency(text: str) -> Optional[str]:
    code = re.search(r"\b(USD|EUR|GBP|IDR|AUD|CAD)\b", text)
    if code:
        return code.group(1)
    for symbol, iso in (("€", "EUR"), ("£", "GBP"), ("$", "USD")):
        if symbol in text:
            return iso
    return None
