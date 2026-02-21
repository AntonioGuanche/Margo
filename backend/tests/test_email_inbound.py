"""Tests for inbound email webhook."""

import base64
from pathlib import Path

import pytest

from app.models.restaurant import Restaurant

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def webhook_secret(monkeypatch):
    """Set a test webhook secret."""
    monkeypatch.setattr("app.config.settings.inbound_email_webhook_secret", "test-secret-123")
    return "test-secret-123"


@pytest.fixture
def xml_invoice_base64():
    """Return the test XML invoice as base64."""
    xml_path = FIXTURES / "test_invoice.xml"
    return base64.b64encode(xml_path.read_bytes()).decode("utf-8")


async def test_webhook_valid_email(
    client, db_session, restaurant, auth_headers, webhook_secret, xml_invoice_base64
):
    """POST webhook with PDF in base64 → invoice created, source='email'."""
    resp = await client.post(
        "/webhooks/email-inbound",
        json={
            "from_email": restaurant.owner_email,
            "to": "factures@margo.be",
            "subject": "Facture INV-2024-001",
            "attachments": [
                {
                    "filename": "facture.xml",
                    "content": xml_invoice_base64,
                    "content_type": "application/xml",
                }
            ],
        },
        headers={"X-Webhook-Secret": webhook_secret},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["invoices_created"] == 1
    assert len(data["invoice_ids"]) == 1

    # Verify invoice created with source=email
    invoice_resp = await client.get(
        f"/api/invoices/{data['invoice_ids'][0]}",
        headers=auth_headers,
    )
    assert invoice_resp.status_code == 200
    invoice = invoice_resp.json()
    assert invoice["source"] == "email"
    assert invoice["status"] == "pending_review"


async def test_webhook_identifies_restaurant(
    client, db_session, restaurant, webhook_secret, xml_invoice_base64
):
    """Restaurant identified by owner_email."""
    resp = await client.post(
        "/webhooks/email-inbound",
        json={
            "from_email": restaurant.owner_email,
            "to": "factures@margo.be",
            "subject": "Facture",
            "attachments": [
                {
                    "filename": "facture.xml",
                    "content": xml_invoice_base64,
                    "content_type": "application/xml",
                }
            ],
        },
        headers={"X-Webhook-Secret": webhook_secret},
    )

    assert resp.status_code == 200
    assert resp.json()["invoices_created"] == 1


async def test_webhook_invalid_secret(client, webhook_secret):
    """Wrong secret → 401."""
    resp = await client.post(
        "/webhooks/email-inbound",
        json={
            "from_email": "someone@test.com",
            "to": "factures@margo.be",
            "subject": "Test",
            "attachments": [],
        },
        headers={"X-Webhook-Secret": "wrong-secret"},
    )

    assert resp.status_code == 401


async def test_webhook_no_attachments(
    client, db_session, restaurant, webhook_secret
):
    """Email without attachments → 200 but 0 invoices."""
    resp = await client.post(
        "/webhooks/email-inbound",
        json={
            "from_email": restaurant.owner_email,
            "to": "factures@margo.be",
            "subject": "Just a message",
            "attachments": [],
        },
        headers={"X-Webhook-Secret": webhook_secret},
    )

    assert resp.status_code == 200
    assert resp.json()["invoices_created"] == 0


async def test_webhook_unsupported_attachment(
    client, db_session, restaurant, webhook_secret
):
    """Unsupported file type (.doc) → ignored."""
    fake_doc = base64.b64encode(b"Not a real doc").decode("utf-8")

    resp = await client.post(
        "/webhooks/email-inbound",
        json={
            "from_email": restaurant.owner_email,
            "to": "factures@margo.be",
            "subject": "Facture",
            "attachments": [
                {
                    "filename": "document.doc",
                    "content": fake_doc,
                    "content_type": "application/msword",
                }
            ],
        },
        headers={"X-Webhook-Secret": webhook_secret},
    )

    assert resp.status_code == 200
    assert resp.json()["invoices_created"] == 0
