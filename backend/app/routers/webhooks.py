"""Webhook endpoints — not JWT-protected, secured by shared secrets."""

import base64
import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.email_inbound import InboundEmail, process_inbound_email

logger = logging.getLogger(__name__)

router = APIRouter()


class EmailAttachmentPayload(BaseModel):
    filename: str
    content: str  # base64-encoded
    content_type: str


class EmailInboundPayload(BaseModel):
    """Simplified inbound email payload (Resend format will be adapted later)."""

    from_email: str  # field name "from" is reserved, using from_email
    to: str
    subject: str
    attachments: list[EmailAttachmentPayload] = []

    model_config = {"populate_by_name": True}


class EmailInboundResponse(BaseModel):
    invoices_created: int
    invoice_ids: list[int]


@router.post("/email-inbound", response_model=EmailInboundResponse)
async def email_inbound_webhook(
    body: EmailInboundPayload,
    db: AsyncSession = Depends(get_db),
    x_webhook_secret: str | None = Header(None),
) -> EmailInboundResponse:
    """Webhook for inbound emails with invoice attachments.

    Protected by X-Webhook-Secret header (not JWT).
    """
    # Verify webhook secret
    expected_secret = settings.inbound_email_webhook_secret
    if not expected_secret:
        raise HTTPException(
            status_code=503,
            detail="Webhook email non configuré.",
        )

    if x_webhook_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Secret invalide.")

    # Convert payload to InboundEmail
    attachments = []
    for att in body.attachments:
        try:
            content_bytes = base64.b64decode(att.content)
        except Exception:
            logger.warning(f"Failed to decode attachment: {att.filename}")
            continue

        attachments.append({
            "filename": att.filename,
            "content_type": att.content_type,
            "content_bytes": content_bytes,
        })

    email = InboundEmail(
        from_email=body.from_email,
        to_email=body.to,
        subject=body.subject,
        attachments=attachments,
    )

    invoice_ids = await process_inbound_email(db, email)

    return EmailInboundResponse(
        invoices_created=len(invoice_ids),
        invoice_ids=invoice_ids,
    )
