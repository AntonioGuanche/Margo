"""Inbound email processing — extract attachments and create invoices."""

import base64
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.restaurant import Restaurant
from app.services.invoice_router import parse_invoice_file
from app.services.matching import match_invoice_lines
from app.services.storage import UPLOAD_DIR

logger = logging.getLogger(__name__)

# Supported attachment MIME types
SUPPORTED_TYPES = {
    "application/pdf",
    "application/xml",
    "text/xml",
    "image/jpeg",
    "image/png",
    "image/webp",
}

# Supported extensions (fallback when MIME type is generic)
SUPPORTED_EXTENSIONS = {".pdf", ".xml", ".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class InboundEmail:
    """Parsed inbound email."""

    from_email: str
    to_email: str  # factures@heymargo.be or factures+{restaurant_id}@heymargo.be
    subject: str
    attachments: list[dict] = field(default_factory=list)
    # Each attachment: {filename, content_type, content_bytes}


def _is_supported_attachment(filename: str, content_type: str) -> bool:
    """Check if attachment is a supported format."""
    if content_type in SUPPORTED_TYPES:
        return True
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def _extract_restaurant_id_from_email(to_email: str) -> int | None:
    """Extract restaurant_id from factures+{id}@heymargo.be."""
    match = re.match(r"factures\+(\d+)@", to_email, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


async def _identify_restaurant(
    db: AsyncSession, email: InboundEmail
) -> Restaurant | None:
    """Identify the restaurant from the email.

    Option A: by sender email (from_email == restaurant.owner_email)
    Option B: by recipient (factures+{restaurant_id}@heymargo.be)
    """
    # Option B: by recipient address
    restaurant_id = _extract_restaurant_id_from_email(email.to_email)
    if restaurant_id:
        restaurant = await db.get(Restaurant, restaurant_id)
        if restaurant:
            return restaurant

    # Option A: by sender email
    result = await db.execute(
        select(Restaurant).where(Restaurant.owner_email == email.from_email)
    )
    restaurant = result.scalar_one_or_none()
    return restaurant


async def _save_attachment(filename: str, content_bytes: bytes) -> str:
    """Save email attachment bytes to disk."""
    folder = UPLOAD_DIR / "invoices"
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}_{filename}"
    path = folder / safe_name
    path.write_bytes(content_bytes)
    return str(path)


async def process_inbound_email(
    db: AsyncSession, email: InboundEmail
) -> list[int]:
    """Process an inbound email with invoice attachment(s).

    1. Identify the restaurant (by sender or recipient)
    2. For each supported attachment: save, parse, match, create Invoice
    3. Return list of created invoice IDs

    Unsupported attachments (.doc, .zip, etc.) are silently ignored.
    """
    # Identify restaurant
    restaurant = await _identify_restaurant(db, email)
    if restaurant is None:
        logger.warning(
            f"Inbound email from {email.from_email} to {email.to_email}: "
            f"no matching restaurant found, ignoring."
        )
        return []

    created_ids: list[int] = []

    for attachment in email.attachments:
        filename = attachment.get("filename", "unknown")
        content_type = attachment.get("content_type", "application/octet-stream")
        content_bytes = attachment.get("content_bytes")

        # Decode base64 if content is a string
        if isinstance(content_bytes, str):
            try:
                content_bytes = base64.b64decode(content_bytes)
            except Exception:
                logger.warning(f"Failed to decode base64 attachment: {filename}")
                continue

        if content_bytes is None:
            continue

        if not _is_supported_attachment(filename, content_type):
            logger.info(f"Skipping unsupported attachment: {filename} ({content_type})")
            continue

        # Save file
        file_path = await _save_attachment(filename, content_bytes)

        # Parse
        parsed = await parse_invoice_file(file_path, filename)

        # Match lines
        match_results = await match_invoice_lines(db, restaurant.id, parsed.lines)

        # Build serializable line data
        line_dicts = []
        for mr in match_results:
            line_dicts.append({
                "description": mr.invoice_line.description,
                "quantity": mr.invoice_line.quantity,
                "unit": mr.invoice_line.unit,
                "unit_price": mr.invoice_line.unit_price,
                "total_price": mr.invoice_line.total_price,
                "matched_ingredient_id": mr.matched_ingredient_id,
                "matched_ingredient_name": mr.matched_ingredient_name,
                "match_confidence": mr.confidence,
                "suggestions": mr.suggestions,
            })

        # Create Invoice
        import datetime as dt
        invoice = Invoice(
            restaurant_id=restaurant.id,
            image_url=file_path,
            supplier_name=parsed.supplier_name or email.subject,
            invoice_date=(
                dt.date.fromisoformat(parsed.invoice_date)
                if parsed.invoice_date
                else None
            ),
            source="email",
            format=parsed.format,
            status="pending_review",
            extracted_lines=line_dicts,
            total_amount=parsed.total_incl_vat or parsed.total_excl_vat,
        )
        db.add(invoice)
        await db.flush()
        await db.refresh(invoice)
        created_ids.append(invoice.id)

        logger.info(
            f"Email invoice created: id={invoice.id}, "
            f"restaurant={restaurant.id}, file={filename}"
        )

    return created_ids
