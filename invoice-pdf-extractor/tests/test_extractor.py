import json
from decimal import Decimal
from pathlib import Path

import pytest

from invoice_extractor import extract_invoice, validate_invoice
from invoice_extractor.extract import parse_invoice_text
from invoice_extractor.ocr import tesseract_available
from invoice_extractor.parsing import parse_amount, parse_date

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
EXPECTED = json.loads((SAMPLES / "expected.json").read_text(encoding="utf-8"))
FIELDS = ["vendor", "invoice_number", "invoice_date", "currency", "subtotal", "tax", "total"]


@pytest.mark.parametrize("token,value", [
    ("1,234.50", "1234.50"), ("1.234,50", "1234.50"), ("$12.00", "12.00"),
    ("€ 3.841,20", "3841.20"), ("0.99", "0.99"),
])
def test_parse_amount(token, value):
    assert parse_amount(token) == Decimal(value)


@pytest.mark.parametrize("text,iso", [
    ("2026-03-14", "2026-03-14"), ("18 Mar 2026", "2026-03-18"),
    ("March 9, 2026", "2026-03-09"), ("05/03/2026", "2026-03-05"), ("31.12.2026", "2026-12-31"),
])
def test_parse_date(text, iso):
    assert parse_date(text) == iso


def test_due_date_is_ignored():
    text = "ACME Ltd\nInvoice No: X-1\nDue Date: 2026-04-30\nDate: 2026-03-01\n"
    assert parse_invoice_text(text)["invoice_date"] == "2026-03-01"


@pytest.mark.parametrize("name", [n for n in EXPECTED if "scanned" not in n])
def test_text_pdfs_match_ground_truth(name):
    inv = extract_invoice(str(SAMPLES / name))
    assert inv["extraction_method"] == "text"
    for f in FIELDS:
        assert inv[f] == EXPECTED[name][f], f
    assert len(inv["line_items"]) == EXPECTED[name]["line_item_count"]
    assert validate_invoice(inv)["status"] == EXPECTED[name]["expected_validation"]


@pytest.mark.skipif(not tesseract_available(), reason="tesseract not installed")
def test_scanned_pdf_uses_ocr_and_matches():
    name = "invoice_04_scanned.pdf"
    inv = extract_invoice(str(SAMPLES / name))
    assert inv["extraction_method"] == "ocr"
    for f in FIELDS:
        assert inv[f] == EXPECTED[name][f], f
    assert validate_invoice(inv)["status"] == "OK"


def test_validation_flags_wrong_total_and_bad_line():
    inv = {
        "vendor": "V", "invoice_number": "1", "invoice_date": "2026-01-01",
        "line_items": [{"description": "a", "quantity": 2, "unit_price": 5.0, "amount": 11.0}],
        "subtotal": 11.0, "tax": 1.0, "total": 99.0,
    }
    issues = validate_invoice(inv)["issues"]
    assert any(i.startswith("line_1_amount_mismatch") for i in issues)
    assert any(i.startswith("total_mismatch") for i in issues)


def test_validation_flags_missing_fields():
    result = validate_invoice({"line_items": []})
    assert result["status"] == "FLAGGED"
    assert "missing_field:total" in result["issues"]
