"""OCR invoice extraction via Claude Vision (images + PDF)."""

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
fournisseurs pour restaurants belges (brasseries, distributeurs boissons, grossistes alimentaires).

Extrais les informations suivantes :
- supplier_name : nom du FOURNISSEUR (celui qui envoie la facture, souvent en haut à gauche ou dans l'en-tête).
  Attention : ne pas confondre avec le client (le restaurant qui reçoit la facture).
- invoice_number : numéro de facture
- invoice_date : date de facture (format YYYY-MM-DD)
- total_excl_vat : total HTVA (hors taxes)
- total_incl_vat : total TVAC / NET A PAYER
- lines : liste des lignes PRODUITS avec pour chacune :
  - description : nom du produit (ex: "STELLA ARTOIS 20L IFK", "LEFFE BLONDE 6% 24/3")
  - quantity : quantité commandée (nombre positif). Pour les vidanges/retours (quantité négative), utilise un nombre négatif.
  - unit : unité si identifiable (fût, casier, bouteille, carton, L, kg, pce), sinon null
  - unit_price : prix unitaire HTVA (hors accises si applicable)
  - total_price : prix total ligne HTVA (= prix unitaire × quantité)
  - units_per_package : nombre d'unités par conditionnement si identifiable (ex: "24/3" → 24, "6x25cl" → 6). Null si non identifiable ou si c'est un fût/bag-in-box.

IMPORTANT :
- Les factures de boissons belges ont souvent des colonnes "Hors Accises" et "Accises" — utilise le prix HORS accises comme unit_price.
- Inclus les lignes de vidanges/consignes (avec quantité négative et prix négatif).
- Si la facture contient plusieurs borderaux/livraisons (ex: ** 2521154 ** et ** 2521680 **), extrais TOUTES les lignes de tous les borderaux.
- Ignore les lignes qui sont juste des notes texte (ex: "ENLEVE DIRNK DE SENSENRUTH") ou les listes de marques/augmentations.
- La page 2 contient souvent un récapitulatif TVA et des informations de paiement — pas de lignes produit à extraire.

Réponds UNIQUEMENT en JSON valide, sans markdown, sans commentaire.
Format :
{
  "supplier_name": "...",
  "invoice_number": "...",
  "invoice_date": "YYYY-MM-DD",
  "total_excl_vat": 0.00,
  "total_incl_vat": 0.00,
  "lines": [
    {"description": "...", "quantity": 0, "unit": "...", "unit_price": 0.00, "total_price": 0.00, "units_per_package": null}
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


def _build_content_block(file_data: bytes, mime_type: str) -> dict:
    """Build the appropriate content block for Claude API (image or document)."""
    data_b64 = base64.standard_b64encode(file_data).decode("utf-8")

    if mime_type == "application/pdf":
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": data_b64,
            },
        }
    else:
        # Ensure valid image mime type
        if mime_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            mime_type = "image/jpeg"
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": data_b64,
            },
        }


async def extract_invoice_from_image(image_path: str) -> ParsedInvoice:
    """Send image or PDF to Claude for structured extraction.

    Supports: JPEG, PNG, WebP, GIF (as images) and PDF (as documents).
    Returns a ParsedInvoice with extracted data, or an empty one
    with raw_text explaining the failure.
    """
    if not settings.anthropic_api_key:
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text="Clé API Anthropic non configurée. Impossible d'utiliser l'OCR.",
        )

    # Read file
    path = Path(image_path)
    if not path.exists():
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text=f"Fichier introuvable : {image_path}",
        )

    # Check file size
    file_size = path.stat().st_size
    if file_size > 20 * 1024 * 1024:  # 20MB hard limit
        return ParsedInvoice(
            format="image",
            lines=[],
            raw_text="Fichier trop grand (> 20 MB). Veuillez réduire la taille.",
        )

    file_data = path.read_bytes()

    # Detect mime type
    mime_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    is_pdf = mime_type == "application/pdf" or str(path).lower().endswith(".pdf")

    if is_pdf:
        mime_type = "application/pdf"
    elif file_size > 5 * 1024 * 1024:
        # Resize large images (not PDFs) using Pillow
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(file_data))
            while len(file_data) > 5 * 1024 * 1024:
                new_size = (img.width // 2, img.height // 2)
                img = img.resize(new_size, Image.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                file_data = buffer.getvalue()
        except Exception as e:
            logger.warning(f"Could not resize image: {e}")

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        content_block = _build_content_block(file_data, mime_type)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=OCR_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        content_block,
                        {
                            "type": "text",
                            "text": "Extrais les données de cette facture fournisseur.",
                        },
                    ],
                }
            ],
        )

        response_text = response.content[0].text
        logger.info(
            "OCR extraction complete (%s, %d bytes) — response length: %d chars",
            mime_type, file_size, len(response_text),
        )
        data = _parse_json_response(response_text)

        # Check for error response
        if isinstance(data, dict) and "error" in data:
            return ParsedInvoice(
                format="pdf" if is_pdf else "image",
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
                units_per_package=item.get("units_per_package"),
            ))

        fmt = "pdf" if is_pdf else "image"
        return ParsedInvoice(
            supplier_name=data.get("supplier_name"),
            invoice_number=data.get("invoice_number"),
            invoice_date=data.get("invoice_date"),
            total_excl_vat=data.get("total_excl_vat"),
            total_incl_vat=data.get("total_incl_vat"),
            lines=lines,
            format=fmt,
        )

    except json.JSONDecodeError as e:
        logger.error(f"OCR JSON parse error: {e}")
        return ParsedInvoice(
            format="pdf" if is_pdf else "image",
            lines=[],
            raw_text="Extraction OCR échouée : réponse JSON invalide",
        )
    except anthropic.APIError as e:
        logger.error(f"Claude API error during OCR: {e}")
        return ParsedInvoice(
            format="pdf" if is_pdf else "image",
            lines=[],
            raw_text=f"Extraction OCR échouée : erreur API Claude",
        )
    except Exception as e:
        logger.error(f"Unexpected OCR error: {e}")
        return ParsedInvoice(
            format="pdf" if is_pdf else "image",
            lines=[],
            raw_text=f"Extraction OCR échouée : {type(e).__name__}",
        )
