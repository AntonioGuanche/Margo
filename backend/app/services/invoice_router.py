"""Invoice format detection and routing to the appropriate parser."""

from app.services.parser_xml import InvoiceLine, ParsedInvoice

# Image extensions for OCR routing
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


async def parse_invoice_file(
    file_path: str,
    filename: str,
    known_products: list[str] | None = None,
) -> ParsedInvoice:
    """Detect format and route to the correct parser.

    Detection by extension AND content:
    - .xml OR content starts with "<?xml" → XML parser
    - .pdf → PDF parser (with OCR fallback if no lines extracted)
    - .jpg/.png/.webp → OCR via Claude Vision
    - Otherwise → OCR fallback
    """
    filename_lower = filename.lower()

    # Detect by extension first
    if filename_lower.endswith(".xml"):
        from app.services.parser_xml import parse_ubl_xml
        return await parse_ubl_xml(file_path)

    if filename_lower.endswith(".pdf"):
        from app.services.parser_pdf import parse_pdf
        result = await parse_pdf(file_path)
        # PDF fallback: if pdfplumber extracted zero lines, try OCR
        if not result.lines:
            from app.services.ocr import extract_invoice_from_image
            ocr_result = await extract_invoice_from_image(file_path, known_products=known_products)
            if ocr_result.lines:
                return ocr_result
        return result

    # Image extensions → OCR
    if any(filename_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
        from app.services.ocr import extract_invoice_from_image
        return await extract_invoice_from_image(file_path, known_products=known_products)

    # Detect by content (first bytes)
    try:
        with open(file_path, "rb") as f:
            header = f.read(10)

        if header.startswith(b"<?xml") or header.startswith(b"\xef\xbb\xbf<?"):
            from app.services.parser_xml import parse_ubl_xml
            return await parse_ubl_xml(file_path)

        if header.startswith(b"%PDF"):
            from app.services.parser_pdf import parse_pdf
            result = await parse_pdf(file_path)
            if not result.lines:
                from app.services.ocr import extract_invoice_from_image
                ocr_result = await extract_invoice_from_image(file_path, known_products=known_products)
                if ocr_result.lines:
                    return ocr_result
            return result
    except Exception:
        pass

    # Unknown → try OCR as last resort
    from app.services.ocr import extract_invoice_from_image
    return await extract_invoice_from_image(file_path, known_products=known_products)
