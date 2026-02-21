"""OCR invoice extraction via Claude Vision."""

import base64
import json
import logging
import mimetypes
from pathlib import Path

import anthropic

from app.config import settings
from app.services.parser_xml import InvoiceLine, ParsedInvoice

logger = logging.getLogger(__name__)

OCR_SYSTEM_PROMPT = """Tu es un assistant spécialisé dans l'extraction de données de factures \
fournisseurs pour restaurants. On te montre la photo d'une facture.

Extrais les informations suivantes :
- supplier_name : nom du fournisseur
- invoice_number : numéro de facture
- invoice_date : date (format YYYY-MM-DD)
- total_excl_vat : total HTVA
- total_incl_vat : total TVAC
- lines : liste des lignes avec pour chacune :
  - description : nom du produit
  - quantity : quantité (nombre)
  - unit : unité (kg, g, L, pce, etc.)
  - unit_price : prix unitaire HTVA
  - total_price : prix total ligne HTVA

Réponds UNIQUEMENT en JSON valide, sans markdown, sans commentaire.
Format :
{
  "supplier_name": "...",
  "invoice_number": "...",
  "invoice_date": "YYYY-MM-DD",
  "total_excl_vat": 0.00,
  "total_incl_vat": 0.00,
  "lines": [
    {"description": "...", "quantity": 0, "unit": "...", \
"unit_price": 0.00, "total_price": 0.00}
  ]
}
Si quelque chose est illisible, mets null.
Si ce n'est pas une facture, retourne {"error": "Image non reconnue"}."""


def _parse_json_response(text: str) -> dict | list:
    """Parse JSON response, handling markdown code block wrapping."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # Remove ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


async def extract_invoice_from_image(image_path: str) -> ParsedInvoice:
    """Send image to Claude Vision for structured extraction.

    Returns a ParsedInvoice with extracted data, or an empty one
    with raw_text explaining the failure.
    """
    if not settings.anthropic_api_key:
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text="Clé API Anthropic non configurée. Impossible d'utiliser l'OCR.",
        )

    # Read and encode image
    path = Path(image_path)
    if not path.exists():
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text=f"Fichier image introuvable : {image_path}",
        )

    # Check file size and resize if > 5MB
    file_size = path.stat().st_size
    if file_size > 20 * 1024 * 1024:  # 20MB hard limit
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text="Image trop grande (> 20 MB). Veuillez réduire la taille.",
        )

    image_data = path.read_bytes()

    # Resize if > 5MB using Pillow
    if file_size > 5 * 1024 * 1024:
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            # Reduce by half until under 5MB
            while len(image_data) > 5 * 1024 * 1024:
                new_size = (img.width // 2, img.height // 2)
                img = img.resize(new_size, Image.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                image_data = buffer.getvalue()
        except Exception as e:
            logger.warning(f"Could not resize image: {e}")

    image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

    # Detect mime type
    mime_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    if mime_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        mime_type = "image/jpeg"

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=OCR_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extrais les données de cette facture.",
                        },
                    ],
                }
            ],
        )

        response_text = response.content[0].text
        data = _parse_json_response(response_text)

        # Check for error response
        if isinstance(data, dict) and "error" in data:
            return ParsedInvoice(
                format="image",
                lines=[],
                raw_text=data["error"],
            )

        # Convert to ParsedInvoice
        lines = []
        for item in data.get("lines", []):
            lines.append(InvoiceLine(
                description=item.get("description", "Unknown"),
                quantity=item.get("quantity"),
                unit=item.get("unit"),
                unit_price=item.get("unit_price"),
                total_price=item.get("total_price"),
            ))

        return ParsedInvoice(
            supplier_name=data.get("supplier_name"),
            invoice_number=data.get("invoice_number"),
            invoice_date=data.get("invoice_date"),
            total_excl_vat=data.get("total_excl_vat"),
            total_incl_vat=data.get("total_incl_vat"),
            lines=lines,
            format="image",
        )

    except json.JSONDecodeError as e:
        logger.error(f"OCR JSON parse error: {e}")
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text=f"Extraction OCR échouée : réponse JSON invalide",
        )
    except anthropic.APIError as e:
        logger.error(f"Claude API error during OCR: {e}")
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text=f"Extraction OCR échouée : erreur API Claude",
        )
    except Exception as e:
        logger.error(f"Unexpected OCR error: {e}")
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text=f"Extraction OCR échouée : {type(e).__name__}",
        )
