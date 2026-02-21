"""Tests for UBL XML invoice parser."""

import tempfile
from pathlib import Path

import pytest

from app.services.parser_xml import parse_ubl_xml

FIXTURES = Path(__file__).parent / "fixtures"


async def test_parse_ubl_valid():
    """Parse a valid UBL XML invoice — 2 lines, correct supplier and totals."""
    result = await parse_ubl_xml(str(FIXTURES / "test_invoice.xml"))

    assert result.format == "xml"
    assert result.supplier_name == "Boucherie Dupont"
    assert result.invoice_number == "INV-2024-001"
    assert result.invoice_date == "2024-12-15"
    assert result.total_excl_vat == 75.00
    assert result.total_incl_vat == 90.75
    assert len(result.lines) == 2


async def test_parse_ubl_extracts_prices():
    """Verify unit_price and total_price per line."""
    result = await parse_ubl_xml(str(FIXTURES / "test_invoice.xml"))

    line1 = result.lines[0]
    assert line1.description == "Boeuf haché"
    assert line1.quantity == 5.0
    assert line1.unit == "kg"
    assert line1.unit_price == 12.00
    assert line1.total_price == 60.00

    line2 = result.lines[1]
    assert line2.description == "Lard fumé"
    assert line2.quantity == 2.0
    assert line2.unit == "kg"
    assert line2.unit_price == 7.50
    assert line2.total_price == 15.00


async def test_parse_ubl_invalid():
    """Non-XML file should raise ValueError."""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w") as f:
        f.write("This is not XML at all!")
        f.flush()

        with pytest.raises(ValueError, match="Invalid XML"):
            await parse_ubl_xml(f.name)


async def test_parse_ubl_not_invoice():
    """Valid XML but not a UBL Invoice should raise ValueError."""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w") as f:
        f.write('<?xml version="1.0"?><Root><Data>hello</Data></Root>')
        f.flush()

        with pytest.raises(ValueError, match="Not a UBL Invoice"):
            await parse_ubl_xml(f.name)
