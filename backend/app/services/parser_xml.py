"""UBL 2.1 / Peppol XML invoice parser."""

from dataclasses import dataclass, field

from lxml import etree


@dataclass
class InvoiceLine:
    """A single line item from a parsed invoice."""

    description: str
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    vat_percent: float | None = None
    units_per_package: int | None = None


@dataclass
class ParsedInvoice:
    """Unified invoice parsing result."""

    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None  # ISO YYYY-MM-DD
    total_excl_vat: float | None = None
    total_incl_vat: float | None = None
    lines: list[InvoiceLine] = field(default_factory=list)
    format: str = "xml"
    raw_text: str | None = None


# UBL 2.1 namespaces
NS = {
    "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}

# Common unit code mappings (UBL unitCode → friendly name)
UNIT_MAP = {
    "KGM": "kg",
    "GRM": "g",
    "LTR": "l",
    "CLT": "cl",
    "MLT": "ml",
    "C62": "pièce",
    "EA": "pièce",
    "H87": "pièce",
    "MTR": "m",
    "BX": "boîte",
    "PK": "paquet",
}


def _text(element: etree._Element | None) -> str | None:
    """Safely extract text from an XML element."""
    if element is not None and element.text:
        return element.text.strip()
    return None


def _float(element: etree._Element | None) -> float | None:
    """Safely extract float from an XML element."""
    text = _text(element)
    if text:
        try:
            return float(text)
        except ValueError:
            return None
    return None


async def parse_ubl_xml(file_path: str) -> ParsedInvoice:
    """Parse a UBL 2.1 / Peppol XML invoice file.

    Extracts supplier, invoice number, date, totals, and line items.
    Raises ValueError if the file is not valid UBL XML.
    """
    try:
        tree = etree.parse(file_path)  # noqa: S320
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML file: {e}") from e

    root = tree.getroot()

    # Check if this is a UBL invoice (with or without namespace)
    root_tag = root.tag
    if "Invoice" not in root_tag:
        raise ValueError(f"Not a UBL Invoice document. Root element: {root_tag}")

    # Detect namespace usage
    has_ns = root.nsmap or "urn:oasis:names:specification:ubl:schema:xsd:" in root_tag

    # Helper to find elements with or without namespaces
    def find(parent: etree._Element, xpath_ns: str, xpath_nons: str) -> etree._Element | None:
        result = parent.find(xpath_ns, NS)
        if result is None:
            result = parent.find(xpath_nons)
        return result

    def findall(parent: etree._Element, xpath_ns: str, xpath_nons: str) -> list:
        result = parent.findall(xpath_ns, NS)
        if not result:
            result = parent.findall(xpath_nons)
        return result

    # --- Extract header ---
    supplier_name = None
    supplier_party = find(
        root,
        ".//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name",
        ".//AccountingSupplierParty/Party/PartyName/Name",
    )
    supplier_name = _text(supplier_party)

    invoice_number = _text(find(root, "cbc:ID", "ID"))
    invoice_date = _text(find(root, "cbc:IssueDate", "IssueDate"))

    # --- Extract totals ---
    total_excl_vat = _float(find(
        root,
        ".//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount",
        ".//LegalMonetaryTotal/TaxExclusiveAmount",
    ))
    total_incl_vat = _float(find(
        root,
        ".//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount",
        ".//LegalMonetaryTotal/TaxInclusiveAmount",
    ))

    # --- Extract lines ---
    invoice_lines = findall(root, "cac:InvoiceLine", "InvoiceLine")
    lines: list[InvoiceLine] = []

    for inv_line in invoice_lines:
        # Description: Item/Name or Item/Description
        item_name = _text(find(inv_line, "cac:Item/cbc:Name", "Item/Name"))
        if not item_name:
            item_name = _text(find(inv_line, "cac:Item/cbc:Description", "Item/Description"))
        if not item_name:
            item_name = "Unknown item"

        # Quantity + unit
        qty_elem = find(inv_line, "cbc:InvoicedQuantity", "InvoicedQuantity")
        quantity = _float(qty_elem)
        unit = None
        if qty_elem is not None:
            unit_code = qty_elem.get("unitCode", "")
            unit = UNIT_MAP.get(unit_code, unit_code.lower() if unit_code else None)

        # Prices
        unit_price = _float(find(inv_line, "cac:Price/cbc:PriceAmount", "Price/PriceAmount"))
        total_price = _float(find(inv_line, "cbc:LineExtensionAmount", "LineExtensionAmount"))

        # VAT
        vat_percent = _float(find(
            inv_line,
            ".//cac:TaxTotal/cac:TaxSubtotal/cbc:Percent",
            ".//TaxTotal/TaxSubtotal/Percent",
        ))

        lines.append(InvoiceLine(
            description=item_name,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            total_price=total_price,
            vat_percent=vat_percent,
        ))

    return ParsedInvoice(
        supplier_name=supplier_name,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        total_excl_vat=total_excl_vat,
        total_incl_vat=total_incl_vat,
        lines=lines,
        format="xml",
    )
