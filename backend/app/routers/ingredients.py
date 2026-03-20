"""CRUD routes for ingredients."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.ingredient import Ingredient
from app.models.ingredient_alias import IngredientAlias
from app.models.invoice import Invoice
from app.models.price_history import IngredientPriceHistory
from app.models.recipe import Recipe, RecipeIngredient
from app.models.restaurant import Restaurant
from app.schemas.ingredient import (
    BatchRecipesRequest,
    BatchRecipesResponse,
    IngredientCreate,
    IngredientListResponse,
    IngredientRecipeItem,
    IngredientRecipesResponse,
    IngredientResponse,
    IngredientUpdate,
    LastConfirmedLinksRequest,
    PriceHistoryEntry,
    PriceHistoryResponse,
)
from app.services.costing import convert_quantity, normalize_to_base_unit, recalculate_recipe, recalculate_recipes_for_ingredient
from app.services.utils import guess_ingredient_category

router = APIRouter()


@router.get("", response_model=IngredientListResponse)
async def list_ingredients(
    search: str | None = Query(default=None, max_length=255),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
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

    # Backfill: auto-categorize ingredients that have no category
    needs_flush = False
    for ing in items:
        if ing.category is None:
            guessed = guess_ingredient_category(ing.name)
            if guessed:
                ing.category = guessed
                needs_flush = True
    if needs_flush:
        await db.flush()

    return IngredientListResponse(
        items=[IngredientResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post("/recipes-batch", response_model=BatchRecipesResponse)
async def get_recipes_batch(
    body: BatchRecipesRequest,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> BatchRecipesResponse:
    """Get recipes for multiple ingredients at once (for invoice review)."""
    if not body.ingredient_ids:
        return BatchRecipesResponse(results={})

    rows = await db.execute(
        select(
            RecipeIngredient.ingredient_id,
            Recipe.id,
            Recipe.name,
            Recipe.category,
            RecipeIngredient.quantity,
            RecipeIngredient.unit,
        )
        .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
        .where(
            RecipeIngredient.ingredient_id.in_(body.ingredient_ids),
            Recipe.restaurant_id == restaurant.id,
        )
    )

    results: dict[int, list[IngredientRecipeItem]] = {
        iid: [] for iid in body.ingredient_ids
    }
    for row in rows.all():
        results[row.ingredient_id].append(
            IngredientRecipeItem(
                recipe_id=row.id,
                recipe_name=row.name,
                category=row.category,
                quantity=row.quantity,
                unit=row.unit,
            )
        )

    return BatchRecipesResponse(results=results)


@router.post("/last-confirmed-links", response_model=BatchRecipesResponse)
async def get_last_confirmed_links(
    body: LastConfirmedLinksRequest,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> BatchRecipesResponse:
    """Get recipe links from the LAST confirmed invoice for each ingredient.

    Respects user's previous choices (additions AND removals).
    Returns same shape as recipes-batch for frontend compatibility.
    Falls back to empty list if no confirmed history exists for an ingredient.
    """
    if not body.ingredient_ids:
        return BatchRecipesResponse(results={})

    # Find confirmed invoices, most recent first
    result = await db.execute(
        select(Invoice)
        .where(
            Invoice.restaurant_id == restaurant.id,
            Invoice.status == "confirmed",
        )
        .order_by(Invoice.created_at.desc())
        .limit(50)
    )
    confirmed_invoices = result.scalars().all()

    # For each ingredient_id, find the most recent confirmed line
    raw_links: dict[int, list[dict]] = {}
    remaining_ids = set(body.ingredient_ids)

    for invoice in confirmed_invoices:
        if not remaining_ids:
            break
        for line_dict in (invoice.extracted_lines or []):
            ing_id = line_dict.get("matched_ingredient_id")
            if ing_id not in remaining_ids:
                continue
            confirmed = line_dict.get("confirmed_recipe_links")
            if confirmed is not None:
                raw_links[ing_id] = confirmed
                remaining_ids.discard(ing_id)

    # Batch-resolve recipe names (avoid N+1)
    all_recipe_ids = set()
    for links in raw_links.values():
        for rl in links:
            rid = rl.get("recipe_id")
            if rid:
                all_recipe_ids.add(rid)

    recipe_names: dict[int, tuple[str, str | None]] = {}
    if all_recipe_ids:
        name_result = await db.execute(
            select(Recipe.id, Recipe.name, Recipe.category)
            .where(Recipe.id.in_(all_recipe_ids))
        )
        for row in name_result.all():
            recipe_names[row.id] = (row.name, row.category)

    # Build response (same shape as recipes-batch)
    results: dict[int, list[IngredientRecipeItem]] = {}
    for ing_id in body.ingredient_ids:
        if ing_id in raw_links:
            items = []
            for rl in raw_links[ing_id]:
                rid = rl.get("recipe_id")
                if rid and rid in recipe_names:
                    name, category = recipe_names[rid]
                    items.append(IngredientRecipeItem(
                        recipe_id=rid,
                        recipe_name=name,
                        category=category,
                        quantity=rl.get("quantity", 1),
                        unit=rl.get("unit", "piece"),
                    ))
            results[ing_id] = items
        else:
            results[ing_id] = []

    return BatchRecipesResponse(results=results)


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
    # Normalize to base unit (kg, l, piece)
    base_unit, base_price = normalize_to_base_unit(data.unit, data.current_price)

    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name=data.name,
        unit=base_unit,
        current_price=base_price,
        supplier_name=data.supplier_name,
        category=data.category,
        last_updated=func.now() if base_price is not None else None,
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

    # Handle unit and price changes
    if "unit" in update_data or "current_price" in update_data:
        old_unit = ingredient.unit
        new_unit = update_data.get("unit", old_unit)

        if "current_price" in update_data:
            # User explicitly provided a new price → normalize to base unit
            new_price = update_data["current_price"]
            base_unit, base_price = normalize_to_base_unit(new_unit, new_price)
            update_data["unit"] = base_unit
            update_data["current_price"] = base_price
        elif "unit" in update_data and new_unit != old_unit:
            # User only changed unit (no new price) → convert existing price
            if ingredient.current_price is not None:
                converted = convert_quantity(1, old_unit, new_unit)
                if converted != 1:  # units are compatible
                    # Convert price: €/old_unit → €/new_unit
                    # If old=kg new=g: 1kg = 1000g, so €/g = €/kg / 1000
                    update_data["current_price"] = round(
                        ingredient.current_price / converted, 6
                    )
            # Don't normalize — store in the unit the user chose

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


@router.get("/{ingredient_id}/recipes", response_model=IngredientRecipesResponse)
async def get_ingredient_recipes(
    ingredient_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> IngredientRecipesResponse:
    """Get recipes that use this ingredient (for auto-suggestion in invoice review)."""
    # Verify ingredient belongs to restaurant
    result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.restaurant_id == restaurant.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrédient introuvable",
        )

    # Query recipes linked to this ingredient
    rows = await db.execute(
        select(
            Recipe.id,
            Recipe.name,
            Recipe.category,
            RecipeIngredient.quantity,
            RecipeIngredient.unit,
        )
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .where(
            RecipeIngredient.ingredient_id == ingredient_id,
            Recipe.restaurant_id == restaurant.id,
        )
    )
    items = [
        IngredientRecipeItem(
            recipe_id=row.id,
            recipe_name=row.name,
            category=row.category,
            quantity=row.quantity,
            unit=row.unit,
        )
        for row in rows.all()
    ]
    return IngredientRecipesResponse(items=items)


@router.post("/{ingredient_id}/merge/{target_id}", response_model=IngredientResponse)
async def merge_ingredient(
    ingredient_id: int,
    target_id: int,
    db: AsyncSession = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> IngredientResponse:
    """Merge ingredient into target: transfer all recipe links, aliases, then delete source."""
    if ingredient_id == target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de fusionner un ingrédient avec lui-même.",
        )

    # Verify both ingredients belong to restaurant
    source_result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == ingredient_id,
            Ingredient.restaurant_id == restaurant.id,
        )
    )
    source = source_result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Ingrédient source introuvable.")

    target_result = await db.execute(
        select(Ingredient).where(
            Ingredient.id == target_id,
            Ingredient.restaurant_id == restaurant.id,
        )
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Ingrédient cible introuvable.")

    # Transfer recipe ingredients (skip duplicates — same recipe already has target)
    existing_links = await db.execute(
        select(RecipeIngredient.recipe_id).where(
            RecipeIngredient.ingredient_id == target_id
        )
    )
    existing_recipe_ids = set(existing_links.scalars().all())

    source_links = await db.execute(
        select(RecipeIngredient).where(
            RecipeIngredient.ingredient_id == ingredient_id
        )
    )
    affected_recipe_ids: set[int] = set()
    for ri in source_links.scalars().all():
        if ri.recipe_id not in existing_recipe_ids:
            ri.ingredient_id = target_id
            affected_recipe_ids.add(ri.recipe_id)
        else:
            await db.delete(ri)
            affected_recipe_ids.add(ri.recipe_id)

    # Transfer aliases
    await db.execute(
        update(IngredientAlias)
        .where(IngredientAlias.ingredient_id == ingredient_id)
        .values(ingredient_id=target_id)
    )

    # Transfer price history
    await db.execute(
        update(IngredientPriceHistory)
        .where(IngredientPriceHistory.ingredient_id == ingredient_id)
        .values(ingredient_id=target_id)
    )

    # Delete source ingredient
    await db.delete(source)
    await db.flush()

    # Recalculate affected recipes
    for recipe_id in affected_recipe_ids:
        await recalculate_recipe(db, recipe_id)

    await db.refresh(target)
    return IngredientResponse.model_validate(target)


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

    # Find recipes using this ingredient (for recalculation after removal)
    ri_result = await db.execute(
        select(RecipeIngredient.recipe_id).where(
            RecipeIngredient.ingredient_id == ingredient_id
        )
    )
    affected_recipe_ids = [row[0] for row in ri_result.all()]

    # Delete recipe_ingredient links (no ondelete=CASCADE on DB yet)
    if affected_recipe_ids:
        await db.execute(
            delete(RecipeIngredient).where(
                RecipeIngredient.ingredient_id == ingredient_id
            )
        )

    await db.delete(ingredient)
    await db.flush()

    # Recalculate food cost for affected recipes
    for recipe_id in affected_recipe_ids:
        await recalculate_recipe(db, recipe_id)
