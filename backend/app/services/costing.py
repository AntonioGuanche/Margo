"""Food cost calculation and cascade recalculation service."""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient


# Conversion factors: from_unit → (base_unit, factor)
# Weight base = kg, Volume base = l
UNIT_TO_BASE: dict[str, tuple[str, float]] = {
    # Weight
    "g": ("kg", 0.001),
    "kg": ("kg", 1.0),
    # Volume
    "ml": ("l", 0.001),
    "cl": ("l", 0.01),
    "l": ("l", 1.0),
    # Countable
    "piece": ("piece", 1.0),
    "pce": ("piece", 1.0),
}


# Regex for packaging formats: "40x100gr", "24x125ml", "36x80gr", "54x55ml", "25X120GR"
_PACKAGING_RE = re.compile(
    r'^(\d+)\s*[xX×]\s*(\d+)\s*(g|gr|kg|ml|cl|l)\s*$'
)


def normalize_to_base_unit(unit: str, price: float | None) -> tuple[str, float | None]:
    """Normalize unit and price to base unit (kg, l, piece).

    Ingredient prices are ALWAYS stored in base units.

    Standard units:
        ("g", 0.024)   → ("kg", 24.0)      # 0.024 €/g × 1000 = 24 €/kg
        ("kg", 24.0)   → ("kg", 24.0)       # already base
        ("ml", 0.005)  → ("l", 5.0)         # 0.005 €/ml × 1000 = 5 €/l
        ("cl", 0.05)   → ("l", 5.0)         # 0.05 €/cl × 100 = 5 €/l
        ("l", 5.0)     → ("l", 5.0)         # already base
        ("piece", 3.5) → ("piece", 3.50)    # already base

    Packaging formats (NxM<unit>) → price per piece:
        ("40x100gr", 20.53) → ("piece", 0.51325)  # 20.53 / 40 = 0.51 €/piece
        ("24x125ml", 36.48) → ("piece", 1.52)     # 36.48 / 24 = 1.52 €/piece
        ("54x55ml", 34.55)  → ("piece", 0.6398)   # 34.55 / 54 = 0.64 €/piece
        ("36x80gr", 37.90)  → ("piece", 1.0528)   # 37.90 / 36 = 1.05 €/piece
    """
    unit = unit.lower().strip()

    # 1. Check packaging format first: "40x100gr" → count × sub-units
    pkg_match = _PACKAGING_RE.match(unit)
    if pkg_match:
        count = int(pkg_match.group(1))
        # Price per piece = total price / number of pieces
        if count > 0 and price is not None:
            return "piece", round(price / count, 6)
        return "piece", price

    # 2. Standard unit lookup
    info = UNIT_TO_BASE.get(unit)

    if info is None:
        return unit, price  # Unknown unit, leave as-is

    base_unit, factor = info

    if factor == 1.0 and unit == base_unit:
        return unit, price  # Already base unit

    # Normalize price: price_per_sub_unit / factor = price_per_base_unit
    normalized_price = round(price / factor, 6) if price is not None else None

    return base_unit, normalized_price


def convert_quantity(qty: float, from_unit: str, to_unit: str) -> float:
    """Convert quantity from from_unit to to_unit.

    Examples:
        convert_quantity(80, "g", "kg") → 0.08
        convert_quantity(500, "ml", "l") → 0.5
        convert_quantity(33, "cl", "l") → 0.33
        convert_quantity(1, "kg", "kg") → 1.0
        convert_quantity(1, "piece", "piece") → 1.0

    Returns qty unchanged if units are incompatible or unknown.
    """
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    if from_unit == to_unit:
        return qty

    from_info = UNIT_TO_BASE.get(from_unit)
    to_info = UNIT_TO_BASE.get(to_unit)

    if from_info is None or to_info is None:
        return qty  # Unknown unit, don't convert

    from_base, from_factor = from_info
    to_base, to_factor = to_info

    if from_base != to_base:
        return qty  # Incompatible (e.g., g vs l), don't convert

    # Convert: qty in from_unit → base → to_unit
    return qty * from_factor / to_factor


def calculate_food_cost(
    ingredients_with_prices: list[tuple[float, str, float | None, str]],
    #                                 qty    ri_unit  price    ing_unit
    selling_price: float,
) -> tuple[float | None, float | None]:
    """Calculate food cost for a recipe with unit conversion.

    Args:
        ingredients_with_prices: list of (quantity, recipe_unit, unit_price, ingredient_unit).
        selling_price: the recipe selling price.

    Returns:
        (food_cost_total, food_cost_percent) or (None, None) if no prices available.
    """
    total = 0.0
    has_any_price = False

    for quantity, recipe_unit, unit_price, ingredient_unit in ingredients_with_prices:
        if unit_price is not None:
            converted_qty = convert_quantity(quantity, recipe_unit, ingredient_unit)
            total += converted_qty * unit_price
            has_any_price = True

    if not has_any_price:
        return None, None

    food_cost_percent = (total / selling_price) * 100 if selling_price > 0 else None
    return round(total, 4), round(food_cost_percent, 2) if food_cost_percent is not None else None


def get_margin_status(food_cost_percent: float | None, target: float = 30.0) -> str:
    """Return margin status based on food cost percent.

    green: < target
    orange: target to target + 5
    red: > target + 5
    """
    if food_cost_percent is None:
        return "green"

    if food_cost_percent < target:
        return "green"
    elif food_cost_percent <= target + 5:
        return "orange"
    else:
        return "red"


async def recalculate_recipe(db: AsyncSession, recipe_id: int) -> None:
    """Recalculate and save food_cost + food_cost_percent for a recipe.

    Uses calculate_food_cost() with unit conversion for ALL recipes
    (both homemade and bought products).
    """
    result = await db.execute(
        select(Recipe)
        .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
        .where(Recipe.id == recipe_id)
        .execution_options(populate_existing=True)
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        return

    # Calculate food cost using unit conversion for ALL recipes
    ingredients_with_prices = [
        (ri.quantity, ri.unit, ri.ingredient.current_price, ri.ingredient.unit)
        for ri in recipe.recipe_ingredients
    ]
    food_cost, food_cost_percent = calculate_food_cost(
        ingredients_with_prices, recipe.selling_price
    )

    recipe.food_cost = food_cost
    recipe.food_cost_percent = food_cost_percent

    await db.flush()


async def recalculate_recipes_for_ingredient(db: AsyncSession, ingredient_id: int) -> None:
    """When an ingredient price changes, recalculate ALL recipes using it."""
    result = await db.execute(
        select(RecipeIngredient.recipe_id)
        .where(RecipeIngredient.ingredient_id == ingredient_id)
        .distinct()
    )
    recipe_ids = result.scalars().all()

    for recipe_id in recipe_ids:
        await recalculate_recipe(db, recipe_id)
