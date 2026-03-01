"""Admin router — founder-only endpoints for user management."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_admin
from app.models.ingredient import Ingredient
from app.models.invoice import Invoice
from app.models.recipe import Recipe
from app.models.restaurant import Restaurant
from app.services.costing import normalize_to_base_unit, recalculate_recipe

router = APIRouter()


# --- Schemas ---


class AdminUserUpdate(BaseModel):
    plan: str | None = None


# --- Endpoints ---


@router.get("/check")
async def admin_check(
    restaurant: Restaurant = Depends(get_admin),
) -> dict:
    """Return 200 if the current user is an admin, 403 otherwise."""
    return {"is_admin": True}


@router.get("/stats")
async def admin_stats(
    restaurant: Restaurant = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return global platform statistics."""
    now = func.now()

    total_restaurants = select(func.count(Restaurant.id)).scalar_subquery()
    active_7d = (
        select(func.count(Restaurant.id))
        .where(Restaurant.updated_at >= now - timedelta(days=7))
        .scalar_subquery()
    )
    active_30d = (
        select(func.count(Restaurant.id))
        .where(Restaurant.updated_at >= now - timedelta(days=30))
        .scalar_subquery()
    )
    total_recipes = select(func.count(Recipe.id)).scalar_subquery()
    total_ingredients = select(func.count(Ingredient.id)).scalar_subquery()
    total_invoices = select(func.count(Invoice.id)).scalar_subquery()
    confirmed_invoices = (
        select(func.count(Invoice.id))
        .where(Invoice.status == "confirmed")
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            total_restaurants,
            active_7d,
            active_30d,
            total_recipes,
            total_ingredients,
            total_invoices,
            confirmed_invoices,
        )
    )
    row = result.one()

    # Plan distribution
    plan_result = await db.execute(
        select(Restaurant.plan, func.count(Restaurant.id)).group_by(Restaurant.plan)
    )
    plans = {plan: count for plan, count in plan_result.all()}

    return {
        "total_restaurants": row[0],
        "active_7d": row[1],
        "active_30d": row[2],
        "plans": plans,
        "total_recipes": row[3],
        "total_ingredients": row[4],
        "total_invoices": row[5],
        "confirmed_invoices": row[6],
    }


@router.get("/users")
async def admin_users(
    restaurant: Restaurant = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return all restaurants with their counters."""
    # Sub-queries for counts
    recipes_count = (
        select(func.count(Recipe.id))
        .where(Recipe.restaurant_id == Restaurant.id)
        .correlate(Restaurant)
        .scalar_subquery()
    )
    ingredients_count = (
        select(func.count(Ingredient.id))
        .where(Ingredient.restaurant_id == Restaurant.id)
        .correlate(Restaurant)
        .scalar_subquery()
    )
    invoices_count = (
        select(func.count(Invoice.id))
        .where(Invoice.restaurant_id == Restaurant.id)
        .correlate(Restaurant)
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            Restaurant.id,
            Restaurant.name,
            Restaurant.owner_email,
            Restaurant.plan,
            Restaurant.created_at,
            Restaurant.updated_at,
            recipes_count.label("recipes_count"),
            ingredients_count.label("ingredients_count"),
            invoices_count.label("invoices_count"),
        ).order_by(Restaurant.created_at.desc())
    )

    users = []
    for row in result.all():
        users.append(
            {
                "id": row[0],
                "name": row[1],
                "owner_email": row[2],
                "plan": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
                "recipes_count": row[6],
                "ingredients_count": row[7],
                "invoices_count": row[8],
            }
        )

    return {"users": users}


@router.patch("/users/{restaurant_id}")
async def admin_update_user(
    restaurant_id: int,
    data: AdminUserUpdate,
    admin: Restaurant = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a restaurant's plan."""
    target = await db.get(Restaurant, restaurant_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant introuvable",
        )

    if data.plan is not None:
        target.plan = data.plan

    await db.flush()

    return {
        "id": target.id,
        "name": target.name,
        "owner_email": target.owner_email,
        "plan": target.plan,
    }


@router.post("/users/{restaurant_id}/normalize-units")
async def admin_normalize_units(
    restaurant_id: int,
    admin: Restaurant = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Normalize all ingredient units to base (kg, l, piece) and recalculate recipes for a specific restaurant."""
    # Verify target restaurant exists
    target = await db.get(Restaurant, restaurant_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant introuvable",
        )

    # Fetch all ingredients for this restaurant
    result = await db.execute(
        select(Ingredient).where(Ingredient.restaurant_id == restaurant_id)
    )
    ingredients = result.scalars().all()

    details = []
    ingredients_fixed = 0

    for ing in ingredients:
        base_unit, base_price = normalize_to_base_unit(ing.unit, ing.current_price)
        if base_unit != ing.unit or base_price != ing.current_price:
            details.append(
                {
                    "name": ing.name,
                    "old_unit": ing.unit,
                    "old_price": ing.current_price,
                    "new_unit": base_unit,
                    "new_price": base_price,
                }
            )
            ing.unit = base_unit
            ing.current_price = base_price
            ingredients_fixed += 1

    await db.flush()

    # Recalculate ALL recipes for this restaurant
    recipe_result = await db.execute(
        select(Recipe.id).where(Recipe.restaurant_id == restaurant_id)
    )
    recipe_ids = recipe_result.scalars().all()

    for rid in recipe_ids:
        await recalculate_recipe(db, rid)

    await db.flush()

    return {
        "ingredients_fixed": ingredients_fixed,
        "ingredients_total": len(ingredients),
        "recipes_recalculated": len(recipe_ids),
        "details": details,
    }


@router.post("/recalculate-all-food-costs")
async def recalculate_all_food_costs(
    admin: Restaurant = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fix packaging units on ingredients, then recalculate ALL recipe food costs."""
    import re

    # Phase 1: Fix ingredients with packaging units (e.g., "40x100gr" → "piece")
    packaging_re = re.compile(r'^\d+\s*[xX×]\s*\d+\s*(?:g|gr|kg|ml|cl|l)\s*$', re.IGNORECASE)

    result = await db.execute(select(Ingredient))
    all_ingredients = result.scalars().all()

    ingredients_fixed = 0
    for ing in all_ingredients:
        if ing.unit and packaging_re.match(ing.unit):
            new_unit, new_price = normalize_to_base_unit(ing.unit, ing.current_price)
            ing.unit = new_unit
            ing.current_price = new_price
            ingredients_fixed += 1

    await db.flush()

    # Phase 2: Recalculate all recipes
    result = await db.execute(select(Recipe.id))
    recipe_ids = result.scalars().all()

    for recipe_id in recipe_ids:
        await recalculate_recipe(db, recipe_id)

    await db.flush()

    return {"ingredients_fixed": ingredients_fixed, "recalculated": len(recipe_ids)}
