"""Tests for OCR invoice extraction (mocked Claude Vision)."""

import pytest

from app.services.ocr import extract_invoice_from_image
from app.services.parser_xml import ParsedInvoice


@pytest.fixture
def mock_ocr_success(monkeypatch):
    """Mock Claude Vision to return a valid invoice extraction."""
    import app.services.ocr as ocr_module

    class FakeContent:
        text = '{"supplier_name": "Metro Cash & Carry", "invoice_number": "M-2024-5678", "invoice_date": "2024-12-20", "total_excl_vat": 245.50, "total_incl_vat": 297.06, "lines": [{"description": "Filet de poulet", "quantity": 10, "unit": "kg", "unit_price": 8.50, "total_price": 85.00}, {"description": "Huile d\'olive extra", "quantity": 5, "unit": "l", "unit_price": 6.90, "total_price": 34.50}]}'

    class FakeResponse:
        content = [FakeContent()]

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    monkeypatch.setattr(ocr_module, "anthropic", type("Module", (), {"Anthropic": FakeClient, "APIError": Exception})())
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "test-key")


@pytest.fixture
def mock_ocr_error(monkeypatch):
    """Mock Claude Vision API to return an image non reconnue response."""
    import app.services.ocr as ocr_module

    class FakeContent:
        text = '{"error": "Image non reconnue"}'

    class FakeResponse:
        content = [FakeContent()]

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    monkeypatch.setattr(ocr_module, "anthropic", type("Module", (), {"Anthropic": FakeClient, "APIError": Exception})())
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "test-key")


@pytest.fixture
def mock_ocr_api_failure(monkeypatch):
    """Mock Claude Vision API failure."""
    import app.services.ocr as ocr_module

    class APIError(Exception):
        pass

    class FakeMessages:
        def create(self, **kwargs):
            raise APIError("Service unavailable")

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    monkeypatch.setattr(ocr_module, "anthropic", type("Module", (), {"Anthropic": FakeClient, "APIError": APIError})())
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "test-key")


async def test_ocr_extract_success(tmp_path, mock_ocr_success):
    """Image → ParsedInvoice with lines (mocked)."""
    # Create a minimal test image
    test_image = tmp_path / "facture.jpg"
    test_image.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # Minimal JPEG header

    result = await extract_invoice_from_image(str(test_image))

    assert isinstance(result, ParsedInvoice)
    assert result.format == "image"
    assert result.supplier_name == "Metro Cash & Carry"
    assert result.invoice_number == "M-2024-5678"
    assert result.invoice_date == "2024-12-20"
    assert result.total_excl_vat == 245.50
    assert result.total_incl_vat == 297.06
    assert len(result.lines) == 2
    assert result.lines[0].description == "Filet de poulet"
    assert result.lines[0].quantity == 10
    assert result.lines[0].unit_price == 8.50


async def test_ocr_extract_invalid_image(tmp_path, mock_ocr_error):
    """Not a valid invoice image → empty ParsedInvoice with raw_text."""
    test_image = tmp_path / "photo.jpg"
    test_image.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    result = await extract_invoice_from_image(str(test_image))

    assert result.lines == []
    assert result.raw_text == "Image non reconnue"


async def test_ocr_api_failure(tmp_path, mock_ocr_api_failure):
    """API failure → graceful handling, no crash."""
    test_image = tmp_path / "facture.jpg"
    test_image.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    result = await extract_invoice_from_image(str(test_image))

    assert result.lines == []
    assert "échouée" in result.raw_text


async def test_ocr_no_api_key(tmp_path, monkeypatch):
    """No API key → clear error message, no crash."""
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "")

    test_image = tmp_path / "facture.jpg"
    test_image.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    result = await extract_invoice_from_image(str(test_image))

    assert result.lines == []
    assert "non configurée" in result.raw_text
