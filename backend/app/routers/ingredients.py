"""CRUD routes for ingredients."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.ingredient import Ingredient
from app.models.recipe import RecipeIngredient
from app.models.restaurant import Restaurant
from app.models.invoice import Invoice
from app.models.price_history import IngredientPriceHistory
from app.schemas.ingredient import (
    IngredientCreate,
    IngredientListResponse,
    IngredientResponse,
    IngredientUpdate,
    PriceHistoryEntry,
    PriceHistoryResponse,
)
from app.services.costing import recalculate_recipes_for_ingredient

router = APIRouter()


@router.get("", response_model=IngredientListResponse)
async def list_ingredients(
    search: str | None = Query(default=None, max_length=255),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> IngredientListResponse:
    """List ingredients for the current restaurant, with optional search."""
    base_query = select(Ingredient).where(Ingredient.restaurant_id == restaurant.id)

    if search:
        base_query = base_query.where(Ingredient.name.ilike(f"%{search}%"))

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginated results
    items_query = base_query.order_by(Ingredient.name).offset(skip).limit(limit)
    result = await db.execute(items_query)
    items = result.scalars().all()

    return IngredientListResponse(
        items=[IngredientResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> IngredientResponse:
    """Get a single ingredient by ID."""
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.restaurant_id == restaurant.id,
        )
    )
    ingredient = result.scalar_one_or_none()

    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrédient introuvable",
        )

    return IngredientResponse.model_validate(ingredient)


@router.post("", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    data: IngredientCreate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> IngredientResponse:
    """Create a new ingredient for the current restaurant."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name=data.name,
        unit=data.unit,
        current_price=data.current_price,
        supplier_name=data.supplier_name,
        last_updated=func.now() if data.current_price is not None else None,
    )

    db.add(ingredient)

    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un ingrédient nommé '{data.name}' existe déjà",
        )

    await db.refresh(ingredient)
    return IngredientResponse.model_validate(ingredient)


@router.put("/{ingredient_id}", response_model=IngredientResponse)
async def update_ingredient(
    ingredient_id: int,
    data: IngredientUpdate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> IngredientResponse:
    """Update an existing ingredient (partial update)."""
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.restaurant_id == restaurant.id,
        )
    )
    ingredient = result.scalar_one_or_none()

    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrédient introuvable",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Track if price changed to update last_updated
    price_changed = "current_price" in update_data and update_data["current_price"] != ingredient.current_price

    for field, value in update_data.items():
        setattr(ingredient, field, value)

    if price_changed:
        ingredient.last_updated = func.now()

    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un ingrédient nommé '{data.name}' existe déjà",
        )

    # Cascade recalculate all recipes using this ingredient
    if price_changed:
        await recalculate_recipes_for_ingredient(db, ingredient_id)

    await db.refresh(ingredient)
    return IngredientResponse.model_validate(ingredient)


@router.get("/{ingredient_id}/price-history", response_model=PriceHistoryResponse)
async def get_price_history(
    ingredient_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> PriceHistoryResponse:
    """Get price history for an ingredient, sorted by date desc."""
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.restaurant_id == restaurant.id,
        )
    )
    ingredient = result.scalar_one_or_none()

    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrédient introuvable",
        )

    # Query price history with invoice join for supplier_name
    from sqlalchemy.orm import selectinload
    history_result = await db.execute(
        select(IngredientPriceHistory)
        .options(selectinload(IngredientPriceHistory.invoice))
        .where(IngredientPriceHistory.ingredient_id == ingredient_id)
        .order_by(IngredientPriceHistory.date.desc())
    )
    history_entries = history_result.scalars().all()

    history = [
        PriceHistoryEntry(
            price=entry.price,
            date=entry.date,
            invoice_id=entry.invoice_id,
            supplier_name=entry.invoice.supplier_name if entry.invoice else None,
            created_at=entry.created_at,
        )
        for entry in history_entries
    ]

    return PriceHistoryResponse(
        ingredient_name=ingredient.name,
        current_price=ingredient.current_price,
        history=history,
    )


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingredient(
    ingredient_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an ingredient."""
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.restaurant_id == restaurant.id,
        )
    )
    ingredient = result.scalar_one_or_none()

    if ingredient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrédient introuvable",
        )

    # Check if ingredient is used in any recipe
    usage_result = await db.execute(
        select(func.count()).select_from(
            select(RecipeIngredient).where(
                RecipeIngredient.ingredient_id == ingredient_id
            ).subquery()
        )
    )
    usage_count = usage_result.scalar_one()
    if usage_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cet ingrédient est utilisé dans {usage_count} recette{'s' if usage_count > 1 else ''}. Retire-le des recettes avant de le supprimer.",
        )

    await db.delete(ingredient)
    await db.flush()
