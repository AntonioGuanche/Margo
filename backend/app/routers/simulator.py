"""Simulator endpoints — "what if" analysis for recipes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.recipe import Recipe, RecipeIngredient
from app.models.restaurant import Restaurant
from app.schemas.simulator import (
    SimulateRequest,
    SimulateResponse,
    SimulatedIngredient,
    SimulationState,
)
from app.services.costing import convert_quantity, get_margin_status, recalculate_recipe

router = APIRouter()


def _build_state(
    selling_price: float,
    ingredients_data: list[dict],
    target_margin: float,
) -> SimulationState:
    """Build a SimulationState from selling price and ingredient details."""
    food_cost = 0.0
    sim_ingredients = []

    for ing in ingredients_data:
        line_cost = None
        if ing["unit_price"] is not None:
            converted_qty = convert_quantity(ing["quantity"], ing["unit"], ing["ingredient_unit"])
            line_cost = round(converted_qty * ing["unit_price"], 4)
            food_cost += line_cost

        sim_ingredients.append(
            SimulatedIngredient(
                ingredient_id=ing["ingredient_id"],
                ingredient_name=ing["ingredient_name"],
                quantity=ing["quantity"],
                unit=ing["unit"],
                unit_price=ing["unit_price"],
                line_cost=line_cost,
                changed=ing.get("changed", False),
            )
        )

    food_cost = round(food_cost, 4)
    food_cost_percent = round((food_cost / selling_price) * 100, 2) if selling_price > 0 else 0.0
    gross_margin = round(selling_price - food_cost, 2)
    margin_status = get_margin_status(food_cost_percent, target_margin)

    return SimulationState(
        selling_price=selling_price,
        food_cost=food_cost,
        food_cost_percent=food_cost_percent,
        margin_status=margin_status,
        gross_margin=gross_margin,
        ingredients=sim_ingredients,
    )


async def _get_recipe_with_ingredients(
    db: AsyncSession, recipe_id: int, restaurant_id: int
) -> Recipe:
    """Fetch recipe with eagerly loaded ingredients, or raise 404."""
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(
                RecipeIngredient.ingredient
            )
        )
        .where(Recipe.id == recipe_id, Recipe.restaurant_id == restaurant_id)
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable",
        )
    return recipe


@router.post("/{recipe_id}/simulate", response_model=SimulateResponse)
async def simulate(
    recipe_id: int,
    body: SimulateRequest,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> SimulateResponse:
    """Simulate changes to a recipe without modifying anything in DB.

    Returns current vs simulated state side by side.
    """
    recipe = await _get_recipe_with_ingredients(db, recipe_id, restaurant.id)
    target = recipe.target_margin if recipe.target_margin is not None else 30.0

    # Build adjustments lookup
    adjustments = {}
    if body.ingredient_adjustments:
        for adj in body.ingredient_adjustments:
            adjustments[adj.ingredient_id] = adj

    # Build current and simulated ingredient data
    current_ingredients = []
    simulated_ingredients = []

    for ri in recipe.recipe_ingredients:
        unit_price = ri.ingredient.current_price

        current_ingredients.append({
            "ingredient_id": ri.ingredient_id,
            "ingredient_name": ri.ingredient.name,
            "quantity": ri.quantity,
            "unit": ri.unit,
            "ingredient_unit": ri.ingredient.unit,
            "unit_price": unit_price,
            "changed": False,
        })

        # Apply adjustments for simulation
        sim_quantity = ri.quantity
        sim_unit_price = unit_price
        changed = False

        if ri.ingredient_id in adjustments:
            adj = adjustments[ri.ingredient_id]
            if adj.new_quantity is not None:
                sim_quantity = adj.new_quantity
                changed = True
            if adj.new_unit_price is not None:
                sim_unit_price = adj.new_unit_price
                changed = True

        simulated_ingredients.append({
            "ingredient_id": ri.ingredient_id,
            "ingredient_name": ri.ingredient.name,
            "quantity": sim_quantity,
            "unit": ri.unit,
            "ingredient_unit": ri.ingredient.unit,
            "unit_price": sim_unit_price,
            "changed": changed,
        })

    # Build states
    current_state = _build_state(recipe.selling_price, current_ingredients, target)
    sim_selling_price = body.new_selling_price or recipe.selling_price
    simulated_state = _build_state(sim_selling_price, simulated_ingredients, target)

    # Monthly impact
    monthly_impact = None
    if body.estimated_weekly_sales is not None:
        old_margin = current_state.gross_margin
        new_margin = simulated_state.gross_margin
        monthly_impact = round((new_margin - old_margin) * body.estimated_weekly_sales * 4, 2)

    return SimulateResponse(
        recipe_name=recipe.name,
        current=current_state,
        simulated=simulated_state,
        monthly_impact=monthly_impact,
    )


@router.post("/{recipe_id}/apply-simulation", response_model=SimulateResponse)
async def apply_simulation(
    recipe_id: int,
    body: SimulateRequest,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> SimulateResponse:
    """Apply simulation changes to the recipe in DB.

    Updates selling_price and/or ingredient quantities.
    """
    recipe = await _get_recipe_with_ingredients(db, recipe_id, restaurant.id)
    target = recipe.target_margin if recipe.target_margin is not None else 30.0

    # Apply selling price change
    if body.new_selling_price is not None:
        recipe.selling_price = body.new_selling_price

    # Apply ingredient adjustments
    if body.ingredient_adjustments:
        adjustments = {adj.ingredient_id: adj for adj in body.ingredient_adjustments}
        for ri in recipe.recipe_ingredients:
            if ri.ingredient_id in adjustments:
                adj = adjustments[ri.ingredient_id]
                if adj.new_quantity is not None:
                    ri.quantity = adj.new_quantity

    await db.flush()

    # Recalculate food cost
    await recalculate_recipe(db, recipe.id)

    # Reload for response
    recipe = await _get_recipe_with_ingredients(db, recipe_id, restaurant.id)

    # Build response (current = simulated since changes are applied)
    ingredients_data = []
    for ri in recipe.recipe_ingredients:
        ingredients_data.append({
            "ingredient_id": ri.ingredient_id,
            "ingredient_name": ri.ingredient.name,
            "quantity": ri.quantity,
            "unit": ri.unit,
            "ingredient_unit": ri.ingredient.unit,
            "unit_price": ri.ingredient.current_price,
            "changed": False,
        })

    state = _build_state(recipe.selling_price, ingredients_data, target)

    return SimulateResponse(
        recipe_name=recipe.name,
        current=state,
        simulated=state,
        monthly_impact=None,
    )
