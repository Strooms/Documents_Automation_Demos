"""Generate 4 synthetic invoice PDFs with different layouts + a ground-truth file.

All names, numbers and addresses are invented. Layouts:
  1. classic   - header left/right, "Description | Qty | Unit Price | Amount"
  2. modern    - "From:" block, quantity-first table, labels "Net / Sales Tax / Amount Due",
                 and a deliberate arithmetic error in the printed total (to test validation)
  3. european  - day-first date, 1.234,56 number style, EUR, "VAT"
  4. scanned   - the classic layout rasterised to an image-only PDF (needs OCR)

Usage: python scripts/generate_samples.py
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent.parent / "samples"
PAGE_W, PAGE_H = 595, 842  # A4 in points
CENT = Decimal("0.01")


@dataclass
class Invoice:
    file: str
    layout: str
    vendor: str
    address: List[str]
    bill_to: List[str]
    number: str
    date_iso: str
    date_text: str
    currency: str
    symbol: str
    eu_numbers: bool
    items: List[Tuple[str, str, str]]  # description, qty, unit price (as strings)
    tax_label: str
    tax_rate: Decimal
    printed_total_error: Decimal = Decimal("0")
    extra: List[str] = field(default_factory=list)

    def lines(self):
        rows = []
        for desc, qty, unit in self.items:
            amount = (Decimal(qty) * Decimal(unit)).quantize(CENT, ROUND_HALF_UP)
            rows.append((desc, Decimal(qty), Decimal(unit), amount))
        return rows

    def totals(self):
        subtotal = sum((r[3] for r in self.lines()), Decimal("0"))
        tax = (subtotal * self.tax_rate / 100).quantize(CENT, ROUND_HALF_UP)
        return subtotal, tax, subtotal + tax

    def fmt(self, x: Decimal, symbol: bool = False) -> str:
        s = f"{x:,.2f}"
        if self.eu_numbers:
            s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{self.symbol} {s}" if symbol and self.eu_numbers else (f"{self.symbol}{s}" if symbol else s)

    def fmt_qty(self, q: Decimal) -> str:
        return format(q.normalize(), "f")


# ---- drawing ops: (kind, x, y_from_top, text, size, bold, align) -----------------------------
Op = Tuple


def text(x, y, s, size=10, bold=False, align="l") -> Op:
    return ("text", x, y, s, size, bold, align)


def rule(y, x0=50, x1=545) -> Op:
    return ("rule", x0, y, x1)


def layout_classic(inv: Invoice) -> List[Op]:
    ops = [text(50, 62, inv.vendor, 15, True), text(545, 62, "INVOICE", 20, True, "r")]
    ops += [text(50, 80 + 12 * i, a, 9) for i, a in enumerate(inv.address)]
    ops += [
        text(545, 90, f"Invoice No: {inv.number}", 10, False, "r"),
        text(545, 104, f"Date: {inv.date_text}", 10, False, "r"),
        text(545, 118, "Due Date: 30 days after invoice date", 10, False, "r"),
        text(50, 150, "Bill To:", 10, True),
    ]
    ops += [text(50, 164 + 12 * i, b, 10) for i, b in enumerate(inv.bill_to)]
    y = 225
    ops += [text(50, y, "Description", 10, True), text(360, y, "Qty", 10, True, "r"),
            text(450, y, "Unit Price", 10, True, "r"), text(545, y, "Amount", 10, True, "r"), rule(y + 5)]
    for desc, qty, unit, amount in inv.lines():
        y += 20
        ops += [text(50, y, desc), text(360, y, inv.fmt_qty(qty), align="r"),
                text(450, y, inv.fmt(unit), align="r"), text(545, y, inv.fmt(amount), align="r")]
    subtotal, tax, total = inv.totals()
    y += 12
    ops.append(rule(y))
    for label, value, bold in ((f"Subtotal", subtotal, False),
                               (f"{inv.tax_label} ({inv.tax_rate.normalize()}%)", tax, False),
                               ("Total", total + inv.printed_total_error, True)):
        y += 20
        ops += [text(450, y, label, 10, bold, "r"), text(545, y, inv.fmt(value, True), 10, bold, "r")]
    ops += [text(50, 760, line, 9) for line in inv.extra]
    return ops


def layout_modern(inv: Invoice) -> List[Op]:
    subtotal, tax, total = inv.totals()
    ops = [text(50, 60, "TAX INVOICE", 22, True),
           text(350, 60, f"Invoice # {inv.number}", 10),
           text(350, 74, f"Issued {inv.date_text}", 10),
           text(350, 88, "Payment terms: Net 30", 10),
           text(50, 110, "From:", 10, True)]
    ops += [text(50, 124 + 12 * i, l, 10) for i, l in enumerate([inv.vendor] + inv.address)]
    ops += [text(300, 170, "Bill To:", 10, True)]
    ops += [text(300, 184 + 12 * i, b, 10) for i, b in enumerate(inv.bill_to)]
    y = 250
    ops += [text(50, y, "Qty", 10, True), text(95, y, "Item", 10, True),
            text(450, y, "Rate", 10, True, "r"), text(545, y, "Total", 10, True, "r"), rule(y + 5)]
    for desc, qty, unit, amount in inv.lines():
        y += 20
        ops += [text(50, y, inv.fmt_qty(qty)), text(95, y, desc),
                text(450, y, inv.fmt(unit), align="r"), text(545, y, inv.fmt(amount), align="r")]
    y += 12
    ops.append(rule(y))
    for label, value, bold in (("Net", subtotal, False),
                               (f"{inv.tax_label} {inv.tax_rate.normalize()}%", tax, False),
                               ("Amount Due", total + inv.printed_total_error, True)):
        y += 20
        ops += [text(450, y, label, 10, bold, "r"), text(545, y, inv.fmt(value, True), 10, bold, "r")]
    ops += [text(50, 760, line, 9) for line in inv.extra]
    return ops


def layout_european(inv: Invoice) -> List[Op]:
    subtotal, tax, total = inv.totals()
    ops = [text(50, 55, "Rechnung / Invoice", 20, True),
           text(545, 90, inv.vendor, 12, True, "r")]
    ops += [text(545, 104 + 12 * i, a, 9, False, "r") for i, a in enumerate(inv.address)]
    ops += [text(50, 90, f"Invoice Number: {inv.number}"), text(50, 104, f"Date: {inv.date_text}"),
            text(50, 150, "Bill To:", 10, True)]
    ops += [text(50, 164 + 12 * i, b, 10) for i, b in enumerate(inv.bill_to)]
    y = 225
    ops += [text(50, y, "Description", 10, True), text(380, y, "Qty", 10, True, "r"),
            text(465, y, "Unit Price", 10, True, "r"), text(545, y, "Amount", 10, True, "r"), rule(y + 5)]
    for desc, qty, unit, amount in inv.lines():
        y += 20
        ops += [text(50, y, desc), text(380, y, inv.fmt_qty(qty), align="r"),
                text(465, y, inv.fmt(unit), align="r"), text(545, y, inv.fmt(amount), align="r")]
    y += 12
    ops.append(rule(y))
    for label, value, bold in (("Subtotal", subtotal, False),
                               (f"{inv.tax_label} {inv.tax_rate.normalize()}%", tax, False),
                               ("Total", total, True)):
        y += 20
        ops += [text(465, y, label, 10, bold, "r"), text(545, y, inv.fmt(value, True), 10, bold, "r")]
    ops += [text(50, 760, line, 9) for line in inv.extra]
    return ops


# ---- backends ----------------------------------------------------------------------------
def render_vector(ops: List[Op], path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("Synthetic invoice (demo)")
    for op in ops:
        if op[0] == "rule":
            _, x0, y, x1 = op
            c.line(x0, PAGE_H - y, x1, PAGE_H - y)
            continue
        _, x, y, s, size, bold, align = op
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        if align == "r":
            c.drawRightString(x, PAGE_H - y, s)
        else:
            c.drawString(x, PAGE_H - y, s)
    c.save()


def _font(size: float, bold: bool) -> ImageFont.FreeTypeFont:
    name = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    for base in ("/usr/share/fonts/truetype/liberation/", "/usr/share/fonts/truetype/dejavu/"):
        for fname in (name, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
            if (Path(base) / fname).exists():
                return ImageFont.truetype(str(Path(base) / fname), int(size))
    raise RuntimeError("No TTF font found (install fonts-liberation or fonts-dejavu)")


def render_scanned(ops: List[Op], path: Path, dpi: int = 200) -> None:
    """Rasterise the ops (no text layer), add slight blur + 0.4 degree skew, wrap in an image-only PDF."""
    k = dpi / 72
    img = Image.new("L", (int(PAGE_W * k), int(PAGE_H * k)), 255)
    d = ImageDraw.Draw(img)
    for op in ops:
        if op[0] == "rule":
            _, x0, y, x1 = op
            d.line([(x0 * k, y * k), (x1 * k, y * k)], fill=0, width=2)
            continue
        _, x, y, s, size, bold, align = op
        font = _font(size * k, bold)
        w = d.textlength(s, font=font)
        d.text(((x * k - w) if align == "r" else x * k, y * k), s, font=font, fill=0, anchor="ls")
    img = img.filter(ImageFilter.GaussianBlur(0.6)).rotate(0.4, fillcolor=255, resample=Image.BICUBIC)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.drawImage(ImageReader(buf), 0, 0, PAGE_W, PAGE_H)
    c.save()


# ---- the four synthetic invoices ----------------------------------------------------------
def build_invoices() -> List[Invoice]:
    return [
        Invoice("invoice_01_classic.pdf", "classic", "Northwind Synthetic Supplies Ltd",
                ["12 Example Road", "Sampletown 00000", "Demo Country"],
                ["Acme Demo Corp", "99 Placeholder Ave", "Testville"],
                "INV-2026-0142", "2026-03-14", "2026-03-14", "USD", "$", False,
                [("Office chair, ergonomic", "4", "129.50"), ("Standing desk frame", "2", "310.00"),
                 ("Cable management kit", "10", "7.25")],
                "Tax", Decimal("8")),
        Invoice("invoice_02_modern_total_error.pdf", "modern", "Brightside Demo Studio LLC",
                ["400 Fictional Blvd", "Mocktown 11111"],
                ["Globex Sample Inc", "1 Imaginary Way"],
                "AC-77831", "2026-03-18", "18 Mar 2026", "USD", "$", False,
                [("Logo design package", "1", "450.00"), ("Social media templates", "6", "35.00"),
                 ("Stock photo licences", "3", "12.50")],
                "Sales Tax", Decimal("10"),
                printed_total_error=Decimal("10.00"),
                extra=["NOTE (synthetic test): printed total deliberately off by 10.00 to exercise validation."]),
        Invoice("invoice_03_european.pdf", "european", "Beispiel Büro GmbH",
                ["Musterstraße 1", "00000 Beispielstadt"],
                ["Demo Handels AG", "Testgasse 7"],
                "R-2026/0099", "2026-03-05", "05/03/2026", "EUR", "€", True,
                [("Beratung (Stunden)", "12.5", "95.00"), ("Reisekosten Pauschale", "1", "240.00"),
                 ("Lizenz Jahresgebühr", "3", "1280.40")],
                "VAT", Decimal("19")),
        Invoice("invoice_04_scanned.pdf", "classic", "Lumen Paper Co.",
                ["7 Fabricated Lane", "Nowhere 22222"],
                ["Initech Sample LLC", "5 Dummy Street"],
                "SC-5521", "2026-03-09", "March 9, 2026", "USD", "$", False,
                [("Copy paper A4 (box)", "5", "24.00"), ("Whiteboard markers", "12", "1.85"),
                 ("Binder clips (pack)", "8", "3.40")],
                "Tax", Decimal("5")),
    ]


LAYOUTS = {"classic": layout_classic, "modern": layout_modern, "european": layout_european}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    truth = {}
    for inv in build_invoices():
        ops = LAYOUTS[inv.layout](inv)
        path = OUT / inv.file
        (render_scanned if "scanned" in inv.file else render_vector)(ops, path)
        subtotal, tax, total = inv.totals()
        truth[inv.file] = {
            "vendor": inv.vendor,
            "invoice_number": inv.number,
            "invoice_date": inv.date_iso,
            "currency": inv.currency,
            "subtotal": float(subtotal),
            "tax": float(tax),
            "total": float(total + inv.printed_total_error),  # what is *printed* on the document
            "line_item_count": len(inv.items),
            "expected_validation": "FLAGGED" if inv.printed_total_error else "OK",
        }
        print("wrote", path.name)
    import pymupdf  # PNG previews for the README

    for name in ("invoice_01_classic", "invoice_04_scanned"):
        with pymupdf.open(OUT / f"{name}.pdf") as doc:
            doc[0].get_pixmap(dpi=60).save(OUT / f"preview_{name}.png")
    (OUT / "expected.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
