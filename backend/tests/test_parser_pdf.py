"""Tests for PDF invoice parser."""

import tempfile

from app.services.parser_pdf import parse_pdf


async def test_parse_pdf_graceful_failure():
    """Corrupted/invalid file should return ParsedInvoice with lines=[] and raw_text, never crash."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode="wb") as f:
        f.write(b"This is definitely not a PDF file!")
        f.flush()

        result = await parse_pdf(f.name)

    assert result.format == "pdf"
    assert result.lines == []
    assert result.raw_text is not None  # Should have some error/debug text


async def test_parse_pdf_returns_parsed_invoice():
    """Even with a minimal/empty PDF, parser should return a valid ParsedInvoice."""
    # Create a minimal valid PDF (just the header, no content)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode="wb") as f:
        # Write minimal PDF structure
        f.write(b"%PDF-1.4\n")
        f.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        f.write(b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n")
        f.write(b"xref\n0 3\n")
        f.write(b"0000000000 65535 f \n")
        f.write(b"0000000009 00000 n \n")
        f.write(b"0000000058 00000 n \n")
        f.write(b"trailer\n<< /Root 1 0 R /Size 3 >>\n")
        f.write(b"startxref\n109\n%%EOF\n")
        f.flush()

        result = await parse_pdf(f.name)

    assert result.format == "pdf"
    # Should not crash, may have empty lines
    assert isinstance(result.lines, list)
