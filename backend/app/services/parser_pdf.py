"""PDF invoice parser — best-effort extraction with pdfplumber."""

import re

import pdfplumber

from app.services.parser_xml import InvoiceLine, ParsedInvoice


# Date patterns: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
DATE_PATTERNS = [
    (r"(\d{2})[/\-.](\d{2})[/\-.](\d{4})", "dmy"),  # DD/MM/YYYY
    (r"(\d{4})[/\-.](\d{2})[/\-.](\d{2})", "ymd"),  # YYYY-MM-DD
]

# Total amount patterns (French invoices)
TOTAL_EXCL_PATTERNS = [
    r"total\s*(?:H\.?T\.?V\.?A\.?|hors\s*tax|HT)\s*[:\s]*[€]?\s*([\d\s.,]+)",
    r"sous[- ]?total\s*[:\s]*[€]?\s*([\d\s.,]+)",
    r"total\s*(?:net|excl)\s*[:\s]*[€]?\s*([\d\s.,]+)",
]

TOTAL_INCL_PATTERNS = [
    r"total\s*(?:T\.?V\.?A\.?C\.?|T\.?T\.?C\.?|à\s*payer)\s*[:\s]*[€]?\s*([\d\s.,]+)",
    r"total\s*(?:incl|général)\s*[:\s]*[€]?\s*([\d\s.,]+)",
    r"montant\s*(?:total|dû|à\s*payer)\s*[:\s]*[€]?\s*([\d\s.,]+)",
]


def _parse_amount(text: str) -> float | None:
    """Parse a French-formatted amount (1.234,56 or 1 234,56)."""
    text = text.strip().replace(" ", "").replace("€", "")
    # French: 1.234,56 → 1234.56
    if "," in text:
        parts = text.rsplit(",", 1)
        integer_part = parts[0].replace(".", "")
        return float(f"{integer_part}.{parts[1]}")
    elif text:
        return float(text.replace(".", "", text.count(".") - 1) if text.count(".") > 1 else text)
    return None


def _extract_date(text: str) -> str | None:
    """Extract the first date found in text, return as ISO format."""
    for pattern, fmt in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            if fmt == "dmy":
                day, month, year = match.groups()
                return f"{year}-{month}-{day}"
            elif fmt == "ymd":
                year, month, day = match.groups()
                return f"{year}-{month}-{day}"
    return None


def _extract_amount(text: str, patterns: list[str]) -> float | None:
    """Try to extract an amount matching one of the patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _parse_amount(match.group(1))
    return None


def _try_extract_lines_from_tables(pdf: pdfplumber.PDF) -> list[InvoiceLine]:
    """Try to extract invoice lines from PDF tables."""
    lines: list[InvoiceLine] = []

    for page in pdf.pages:
        tables = page.extract_tables()
        if not tables:
            continue

        for table in tables:
            if not table or len(table) < 2:
                continue

            # Try to identify header row and column positions
            header = table[0]
            if header is None:
                continue

            # Normalize header cells
            header_lower = [
                (cell or "").strip().lower() for cell in header
            ]

            # Find column indices
            desc_idx = None
            qty_idx = None
            unit_price_idx = None
            total_idx = None

            for i, h in enumerate(header_lower):
                if any(kw in h for kw in ["description", "désignation", "article", "produit", "libellé", "nom"]):
                    desc_idx = i
                elif any(kw in h for kw in ["quantité", "qté", "qty", "nombre"]):
                    qty_idx = i
                elif any(kw in h for kw in ["prix unit", "p.u.", "pu", "unitaire"]):
                    unit_price_idx = i
                elif any(kw in h for kw in ["montant", "total", "prix"]) and total_idx is None:
                    total_idx = i

            if desc_idx is None:
                continue

            # Parse data rows
            for row in table[1:]:
                if row is None or len(row) <= desc_idx:
                    continue

                desc = (row[desc_idx] or "").strip()
                if not desc or len(desc) < 2:
                    continue

                qty = None
                if qty_idx is not None and qty_idx < len(row) and row[qty_idx]:
                    try:
                        qty = _parse_amount(row[qty_idx].strip())
                    except (ValueError, AttributeError):
                        pass

                unit_price = None
                if unit_price_idx is not None and unit_price_idx < len(row) and row[unit_price_idx]:
                    try:
                        unit_price = _parse_amount(row[unit_price_idx].strip())
                    except (ValueError, AttributeError):
                        pass

                total_price = None
                if total_idx is not None and total_idx < len(row) and row[total_idx]:
                    try:
                        total_price = _parse_amount(row[total_idx].strip())
                    except (ValueError, AttributeError):
                        pass

                # If we have unit_price and qty but no total, compute it
                if total_price is None and unit_price is not None and qty is not None:
                    total_price = round(unit_price * qty, 2)

                # If we have total and qty but no unit_price, compute it
                if unit_price is None and total_price is not None and qty and qty > 0:
                    unit_price = round(total_price / qty, 4)

                lines.append(InvoiceLine(
                    description=desc,
                    quantity=qty,
                    unit=None,
                    unit_price=unit_price,
                    total_price=total_price,
                    vat_percent=None,
                ))

    return lines


async def parse_pdf(file_path: str) -> ParsedInvoice:
    """Parse a PDF invoice with best-effort extraction.

    Tries table extraction first, then falls back to raw text.
    Never raises — always returns a ParsedInvoice, possibly with lines=[] and raw_text.
    """
    raw_text = ""

    try:
        with pdfplumber.open(file_path) as pdf:
            # Extract all text
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"

            # Extract supplier (usually in first few lines)
            supplier_name = None
            text_lines = raw_text.strip().split("\n")
            if text_lines:
                # Skip very short lines, take first substantial line as supplier
                for line in text_lines[:5]:
                    cleaned = line.strip()
                    if len(cleaned) > 3 and not cleaned.startswith("Facture"):
                        supplier_name = cleaned
                        break

            # Extract date
            invoice_date = _extract_date(raw_text)

            # Extract totals
            total_excl_vat = _extract_amount(raw_text, TOTAL_EXCL_PATTERNS)
            total_incl_vat = _extract_amount(raw_text, TOTAL_INCL_PATTERNS)

            # Try to extract lines from tables
            lines = _try_extract_lines_from_tables(pdf)

    except Exception:
        # PDF parsing should never crash — return what we have
        return ParsedInvoice(
            format="pdf",
            raw_text=raw_text if raw_text else f"Failed to parse PDF: {file_path}",
            lines=[],
        )

    return ParsedInvoice(
        supplier_name=supplier_name,
        invoice_date=invoice_date,
        total_excl_vat=total_excl_vat,
        total_incl_vat=total_incl_vat,
        lines=lines,
        format="pdf",
        raw_text=raw_text if not lines else None,  # Include raw text only if no lines extracted
    )
