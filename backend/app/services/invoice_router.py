"""Invoice format detection and routing to the appropriate parser."""

from app.services.parser_xml import InvoiceLine, ParsedInvoice


async def parse_invoice_file(file_path: str, filename: str) -> ParsedInvoice:
    """Detect format and route to the correct parser.

    Detection by extension AND content:
    - .xml OR content starts with "<?xml" → XML parser
    - .pdf OR content starts with "%PDF" → PDF parser
    - Otherwise → image placeholder (OCR in Sprint 5)
    """
    filename_lower = filename.lower()

    # Detect by extension first
    if filename_lower.endswith(".xml"):
        from app.services.parser_xml import parse_ubl_xml
        return await parse_ubl_xml(file_path)

    if filename_lower.endswith(".pdf"):
        from app.services.parser_pdf import parse_pdf
        return await parse_pdf(file_path)

    # Detect by content (first bytes)
    try:
        with open(file_path, "rb") as f:
            header = f.read(10)

        if header.startswith(b"<?xml") or header.startswith(b"\xef\xbb\xbf<?"):
            # UTF-8 BOM + XML
            from app.services.parser_xml import parse_ubl_xml
            return await parse_ubl_xml(file_path)

        if header.startswith(b"%PDF"):
            from app.services.parser_pdf import parse_pdf
            return await parse_pdf(file_path)
    except Exception:
        pass

    # Image or unknown → placeholder for OCR (Sprint 5)
    return ParsedInvoice(
        format="image",
        lines=[],
        raw_text="Image invoice — OCR processing not yet available.",
    )
