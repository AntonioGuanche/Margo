"""CRUD routes for recipes + dashboard."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient
from app.models.restaurant import Restaurant
from app.schemas.recipe import (
    DashboardResponse,
    RecipeCreate,
    RecipeIngredientResponse,
    RecipeListItem,
    RecipeListResponse,
    RecipeResponse,
    RecipeUpdate,
)
from app.services.costing import calculate_food_cost, get_margin_status, recalculate_recipe

router = APIRouter()


def _build_recipe_list_item(recipe: Recipe) -> RecipeListItem:
    """Build a RecipeListItem from a Recipe ORM object."""
    target = recipe.target_margin if recipe.target_margin is not None else 30.0
    return RecipeListItem(
        id=recipe.id,
        name=recipe.name,
        selling_price=recipe.selling_price,
        category=recipe.category,
        target_margin=recipe.target_margin,
        food_cost=recipe.food_cost,
        food_cost_percent=recipe.food_cost_percent,
        margin_status=get_margin_status(recipe.food_cost_percent, target),
        created_at=recipe.created_at,
    )


def _build_recipe_response(recipe: Recipe) -> RecipeResponse:
    """Build a RecipeResponse with ingredient details from a Recipe ORM object."""
    target = recipe.target_margin if recipe.target_margin is not None else 30.0

    ingredient_responses = []
    for ri in recipe.recipe_ingredients:
        unit_cost = ri.ingredient.current_price
        line_cost = round(ri.quantity * unit_cost, 4) if unit_cost is not None else None
        ingredient_responses.append(
            RecipeIngredientResponse(
                id=ri.id,
                ingredient_id=ri.ingredient_id,
                ingredient_name=ri.ingredient.name,
                quantity=ri.quantity,
                unit=ri.unit,
                unit_cost=unit_cost,
                line_cost=line_cost,
            )
        )

    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        selling_price=recipe.selling_price,
        category=recipe.category,
        target_margin=recipe.target_margin,
        food_cost=recipe.food_cost,
        food_cost_percent=recipe.food_cost_percent,
        margin_status=get_margin_status(recipe.food_cost_percent, target),
        ingredients=ingredient_responses,
        created_at=recipe.created_at,
    )


@router.get("", response_model=RecipeListResponse)
async def list_recipes(
    search: str | None = Query(default=None, max_length=255),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="name", pattern="^(name|food_cost_percent)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> RecipeListResponse:
    """List recipes for the current restaurant."""
    base_query = select(Recipe).where(Recipe.restaurant_id == restaurant.id)

    if search:
        base_query = base_query.where(Recipe.name.ilike(f"%{search}%"))

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Sorting
    sort_column = Recipe.name if sort_by == "name" else Recipe.food_cost_percent
    if sort_order == "desc":
        sort_column = sort_column.desc().nulls_last()
    else:
        sort_column = sort_column.asc().nulls_last()

    items_query = base_query.order_by(sort_column).offset(skip).limit(limit)
    result = await db.execute(items_query)
    recipes = result.scalars().all()

    return RecipeListResponse(
        items=[_build_recipe_list_item(r) for r in recipes],
        total=total,
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> RecipeResponse:
    """Get a single recipe with full ingredient details."""
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
        )
        .where(Recipe.id == recipe_id, Recipe.restaurant_id == restaurant.id)
    )
    recipe = result.scalar_one_or_none()

    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable",
        )

    return _build_recipe_response(recipe)


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    data: RecipeCreate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> RecipeResponse:
    """Create a recipe with ingredients, calculate food cost."""
    # Verify all ingredients belong to this restaurant
    ingredient_ids = [ri.ingredient_id for ri in data.ingredients]
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id.in_(ingredient_ids),
            Ingredient.restaurant_id == restaurant.id,
        )
    )
    found_ingredients = {ing.id: ing for ing in result.scalars().all()}

    missing = set(ingredient_ids) - set(found_ingredients.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ingrédients introuvables: {sorted(missing)}",
        )

    # Calculate food cost
    ingredients_with_prices = [
        (ri.quantity, found_ingredients[ri.ingredient_id].current_price)
        for ri in data.ingredients
    ]
    food_cost, food_cost_percent = calculate_food_cost(ingredients_with_prices, data.selling_price)

    # Create recipe
    recipe = Recipe(
        restaurant_id=restaurant.id,
        name=data.name,
        selling_price=data.selling_price,
        category=data.category,
        target_margin=data.target_margin,
        food_cost=food_cost,
        food_cost_percent=food_cost_percent,
    )
    db.add(recipe)
    await db.flush()

    # Create recipe ingredients
    for ri_data in data.ingredients:
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ri_data.ingredient_id,
            quantity=ri_data.quantity,
            unit=ri_data.unit,
        )
        db.add(ri)

    await db.flush()

    # Reload with ingredients for response
    await db.refresh(recipe)
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
        )
        .where(Recipe.id == recipe.id)
    )
    recipe = result.scalar_one()

    return _build_recipe_response(recipe)


@router.put("/{recipe_id}", response_model=RecipeResponse)
async def update_recipe(
    recipe_id: int,
    data: RecipeUpdate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> RecipeResponse:
    """Update a recipe. If ingredients provided, replace all of them."""
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
        )
        .where(Recipe.id == recipe_id, Recipe.restaurant_id == restaurant.id)
    )
    recipe = result.scalar_one_or_none()

    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable",
        )

    # Update scalar fields
    update_data = data.model_dump(exclude_unset=True, exclude={"ingredients"})
    for field, value in update_data.items():
        setattr(recipe, field, value)

    # Replace ingredients if provided
    if data.ingredients is not None:
        # Verify all ingredients belong to this restaurant
        ingredient_ids = [ri.ingredient_id for ri in data.ingredients]
        ing_result = await db.execute(
            select(Ingredient).where(
                Ingredient.id.in_(ingredient_ids),
                Ingredient.restaurant_id == restaurant.id,
            )
        )
        found_ingredients = {ing.id: ing for ing in ing_result.scalars().all()}

        missing = set(ingredient_ids) - set(found_ingredients.keys())
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ingrédients introuvables: {sorted(missing)}",
            )

        # Delete old recipe ingredients
        await db.execute(
            delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        )

        # Create new ones
        for ri_data in data.ingredients:
            ri = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ri_data.ingredient_id,
                quantity=ri_data.quantity,
                unit=ri_data.unit,
            )
            db.add(ri)

        await db.flush()

    # Recalculate food cost
    await recalculate_recipe(db, recipe.id)

    # Reload for response
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
        )
        .where(Recipe.id == recipe.id)
    )
    recipe = result.scalar_one()

    return _build_recipe_response(recipe)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a recipe."""
    result = await db.execute(
        select(Recipe).where(
            Recipe.id == recipe_id, Recipe.restaurant_id == restaurant.id
        )
    )
    recipe = result.scalar_one_or_none()

    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recette introuvable",
        )

    await db.delete(recipe)
    await db.flush()


@router.get("/dashboard/overview", response_model=DashboardResponse)
async def get_dashboard(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Dashboard overview: average food cost, counts by status, recipes sorted worst-first."""
    result = await db.execute(
        select(Recipe).where(Recipe.restaurant_id == restaurant.id)
    )
    recipes = result.scalars().all()

    total = len(recipes)
    recipes_with_cost = [r for r in recipes if r.food_cost_percent is not None]

    avg_food_cost = None
    if recipes_with_cost:
        avg_food_cost = round(
            sum(r.food_cost_percent for r in recipes_with_cost) / len(recipes_with_cost), 2
        )

    # Count by margin status
    green = orange = red = 0
    for r in recipes:
        target = r.target_margin if r.target_margin is not None else 30.0
        s = get_margin_status(r.food_cost_percent, target)
        if s == "green":
            green += 1
        elif s == "orange":
            orange += 1
        else:
            red += 1

    # Sort by food_cost_percent descending (worst first), nulls last
    sorted_recipes = sorted(
        recipes,
        key=lambda r: (r.food_cost_percent is None, -(r.food_cost_percent or 0)),
    )

    return DashboardResponse(
        average_food_cost_percent=avg_food_cost,
        total_recipes=total,
        recipes_green=green,
        recipes_orange=orange,
        recipes_red=red,
        recipes=[_build_recipe_list_item(r) for r in sorted_recipes],
    )
