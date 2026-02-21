"""AI services for menu extraction and ingredient suggestion using Claude."""

import asyncio
import base64
import json
import logging
import mimetypes
from pathlib import Path

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM_PROMPT = """Tu es un assistant spécialisé dans la restauration belge.
On te montre la photo d'une carte de restaurant.
Extrais TOUS les plats avec leur prix.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans commentaire.
Format : [{"name": "Nom du plat", "price": 19.50, "category": "plat"}]
Les catégories possibles : "entrée", "plat", "dessert", "boisson", "autre"
Si tu ne vois pas le prix, mets null.
Si la photo est illisible ou ce n'est pas une carte, retourne []."""

SUGGEST_SYSTEM_PROMPT = """Tu es un chef belge expérimenté. Pour le plat "{dish_name}" \
(catégorie : {category}), propose la liste d'ingrédients \
avec les quantités pour UNE portion.

Réponds UNIQUEMENT en JSON valide, sans markdown, sans commentaire.
Format : [{{"name": "Boeuf", "quantity": 250, "unit": "g"}}]
Unités possibles : g, kg, cl, l, piece
Sois réaliste sur les quantités pour un restaurant belge.
Inclus les ingrédients principaux ET les condiments/bases \
(beurre, huile, sel, poivre ne sont PAS nécessaires — \
concentre-toi sur les ingrédients qui coûtent quelque chose)."""

# Demo data when no API key is configured
DEMO_DISHES = [
    {"name": "Carbonnade flamande", "price": 19.50, "category": "plat"},
    {"name": "Moules-frites", "price": 22.00, "category": "plat"},
    {"name": "Croquettes aux crevettes", "price": 14.50, "category": "entrée"},
    {"name": "Dame blanche", "price": 8.50, "category": "dessert"},
    {"name": "Gaufre de Liège", "price": 7.00, "category": "dessert"},
]

DEMO_INGREDIENTS: dict[str, list[dict]] = {
    "Carbonnade flamande": [
        {"name": "Boeuf", "quantity": 250, "unit": "g"},
        {"name": "Bière brune", "quantity": 15, "unit": "cl"},
        {"name": "Oignons", "quantity": 150, "unit": "g"},
        {"name": "Pain d'épices", "quantity": 30, "unit": "g"},
    ],
    "Moules-frites": [
        {"name": "Moules", "quantity": 500, "unit": "g"},
        {"name": "Céleri", "quantity": 50, "unit": "g"},
        {"name": "Pommes de terre", "quantity": 200, "unit": "g"},
        {"name": "Vin blanc", "quantity": 10, "unit": "cl"},
    ],
    "Croquettes aux crevettes": [
        {"name": "Crevettes grises", "quantity": 100, "unit": "g"},
        {"name": "Beurre", "quantity": 40, "unit": "g"},
        {"name": "Farine", "quantity": 30, "unit": "g"},
        {"name": "Lait", "quantity": 15, "unit": "cl"},
    ],
    "Dame blanche": [
        {"name": "Glace vanille", "quantity": 150, "unit": "g"},
        {"name": "Chocolat", "quantity": 50, "unit": "g"},
        {"name": "Crème fraîche", "quantity": 10, "unit": "cl"},
    ],
    "Gaufre de Liège": [
        {"name": "Pâte à gaufre", "quantity": 150, "unit": "g"},
        {"name": "Sucre perlé", "quantity": 30, "unit": "g"},
        {"name": "Chantilly", "quantity": 50, "unit": "g"},
    ],
}


def _is_demo_mode() -> bool:
    """Check if we should use demo data instead of calling Claude."""
    return not settings.anthropic_api_key


def _get_client() -> anthropic.AsyncAnthropic:
    """Create an Anthropic client."""
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _parse_json_response(text: str) -> list[dict]:
    """Parse JSON from Claude's response, handling potential markdown wrapping."""
    text = text.strip()
    # Remove markdown code block if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    return json.loads(text)


async def extract_menu_from_image(image_path: str) -> list[dict]:
    """Extract dishes from a menu image using Claude Vision.

    Args:
        image_path: Path to the menu image file.

    Returns:
        List of dicts with name, price, category.
    """
    if _is_demo_mode():
        logger.info("Demo mode: returning fake menu extraction")
        return DEMO_DISHES

    # Read image and encode to base64
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    media_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"

    client = _get_client()

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=EXTRACT_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extrais les plats de cette carte de restaurant.",
                        },
                    ],
                }
            ],
        )

        response_text = message.content[0].text
        dishes = _parse_json_response(response_text)
        return dishes

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        raise ValueError("L'IA n'a pas pu extraire les plats. Réessayez avec une photo plus nette.")
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise ValueError(f"Erreur de l'API Claude: {e}")


async def suggest_ingredients(dish_name: str, category: str | None = None) -> list[dict]:
    """Suggest ingredients for a dish using Claude.

    Args:
        dish_name: Name of the dish.
        category: Optional category (entrée, plat, dessert, etc.).

    Returns:
        List of dicts with name, quantity, unit.
    """
    if _is_demo_mode():
        logger.info(f"Demo mode: returning fake ingredients for {dish_name}")
        return DEMO_INGREDIENTS.get(dish_name, [
            {"name": "Ingrédient principal", "quantity": 200, "unit": "g"},
            {"name": "Accompagnement", "quantity": 100, "unit": "g"},
        ])

    client = _get_client()
    prompt = SUGGEST_SYSTEM_PROMPT.format(
        dish_name=dish_name,
        category=category or "non spécifiée",
    )

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        response_text = message.content[0].text
        ingredients = _parse_json_response(response_text)
        return ingredients

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ingredients for '{dish_name}': {e}")
        return []
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error for '{dish_name}': {e}")
        return []


async def suggest_ingredients_batch(dishes: list[dict]) -> dict[str, list[dict]]:
    """Suggest ingredients for multiple dishes in parallel.

    Uses a semaphore to limit concurrency to 5.

    Args:
        dishes: List of dicts with at least 'name' and optionally 'category'.

    Returns:
        Dict mapping dish name to list of ingredient suggestions.
    """
    semaphore = asyncio.Semaphore(5)
    results: dict[str, list[dict]] = {}

    async def _suggest_one(dish: dict) -> tuple[str, list[dict]]:
        async with semaphore:
            name = dish["name"]
            category = dish.get("category")
            try:
                ingredients = await suggest_ingredients(name, category)
                return name, ingredients
            except Exception as e:
                logger.error(f"Failed to suggest ingredients for '{name}': {e}")
                return name, []

    tasks = [_suggest_one(dish) for dish in dishes]
    completed = await asyncio.gather(*tasks)

    for name, ingredients in completed:
        results[name] = ingredients

    return results
