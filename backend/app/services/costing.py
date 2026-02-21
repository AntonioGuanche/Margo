"""Food cost calculation and cascade recalculation service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient


def calculate_food_cost(
    ingredients_with_prices: list[tuple[float, float | None]],
    selling_price: float,
) -> tuple[float | None, float | None]:
    """Calculate food cost for a recipe.

    Args:
        ingredients_with_prices: list of (quantity, unit_price) tuples.
        selling_price: the recipe selling price.

    Returns:
        (food_cost_total, food_cost_percent) or (None, None) if no prices available.
    """
    total = 0.0
    has_any_price = False

    for quantity, unit_price in ingredients_with_prices:
        if unit_price is not None:
            total += quantity * unit_price
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
    """Recalculate and save food_cost + food_cost_percent for a recipe."""
    result = await db.execute(
        select(Recipe)
        .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
        .where(Recipe.id == recipe_id)
        .execution_options(populate_existing=True)
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        return

    ingredients_with_prices = [
        (ri.quantity, ri.ingredient.current_price)
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
