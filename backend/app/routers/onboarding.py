"""Onboarding routes — AI-powered menu extraction and batch recipe creation."""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.middleware.plan_limits import require_recipe_quota
from app.middleware.rate_limit import check_ai_rate_limit, check_upload_rate_limit
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient
from app.models.restaurant import Restaurant
from app.schemas.onboarding import (
    DishWithSuggestions,
    ExtractedDish,
    MenuExtractionResponse,
    OnboardingConfirmRequest,
    OnboardingConfirmResponse,
    SuggestIngredientsRequest,
    SuggestIngredientsResponse,
)
from app.services.costing import calculate_food_cost, normalize_to_base_unit
from app.services.onboarding_ai import extract_menu_from_image, suggest_ingredients_batch
from app.services.storage import save_upload
from app.services.utils import guess_ingredient_category

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/extract-menu", response_model=MenuExtractionResponse)
async def extract_menu(
    file: UploadFile,
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> MenuExtractionResponse:
    """Upload a menu image and extract dishes using AI."""
    # Rate limits
    check_upload_rate_limit(restaurant.id)
    check_ai_rate_limit(restaurant.id)

    allowed_types = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if not file.content_type or (
        not file.content_type.startswith("image/") and file.content_type not in allowed_types
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Le fichier doit être une image (JPEG, PNG, WebP) ou un PDF.",
        )

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        size_mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux ({size_mb:.1f} MB). Maximum : 10 MB.",
        )
    await file.seek(0)

    # Save the uploaded file
    image_path = await save_upload(file, subfolder="menus")

    # Extract dishes using AI
    try:
        raw_dishes = await extract_menu_from_image(image_path)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    dishes = [
        ExtractedDish(
            name=d.get("name", ""),
            price=d.get("price"),
            category=d.get("category"),
        )
        for d in raw_dishes
        if d.get("name")
    ]

    return MenuExtractionResponse(dishes=dishes, image_path=image_path)


@router.post("/suggest-ingredients", response_model=SuggestIngredientsResponse)
async def suggest_ingredients(
    request: SuggestIngredientsRequest,
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> SuggestIngredientsResponse:
    """Suggest ingredients for a list of dishes using AI."""
    check_ai_rate_limit(restaurant.id)
    dishes_data = [
        {"name": d.name, "category": d.category}
        for d in request.dishes
    ]

    suggestions = await suggest_ingredients_batch(dishes_data)

    result_dishes = []
    for dish in request.dishes:
        dish_ingredients = suggestions.get(dish.name, [])
        result_dishes.append(
            DishWithSuggestions(
                name=dish.name,
                price=dish.price,
                category=dish.category,
                ingredients=[
                    {"name": ing["name"], "quantity": ing["quantity"], "unit": ing["unit"]}
                    for ing in dish_ingredients
                ],
            )
        )

    return SuggestIngredientsResponse(dishes=result_dishes)


@router.post("/confirm", response_model=OnboardingConfirmResponse)
async def confirm_onboarding(
    request: OnboardingConfirmRequest,
    restaurant: Restaurant = Depends(require_recipe_quota),
    db: AsyncSession = Depends(get_db),
) -> OnboardingConfirmResponse:
    """Confirm onboarding: create ingredients and recipes in one transaction."""
    recipes_created = 0
    ingredients_created = 0

    for dish in request.dishes:
        recipe_ingredients_data = []

        # Auto-inject ingredient for purchased items (is_homemade=False) with no ingredients
        if not dish.is_homemade and len(dish.ingredients) == 0:
            from app.schemas.onboarding import OnboardingIngredient
            dish.ingredients = [
                OnboardingIngredient(name=dish.name, quantity=1, unit="piece")
            ]

        for ing_data in dish.ingredients:
            # Look for existing ingredient (case-insensitive)
            result = await db.execute(
                select(Ingredient).where(
                    Ingredient.restaurant_id == restaurant.id,
                    func.lower(Ingredient.name) == ing_data.name.lower(),
                )
            )
            ingredient = result.scalar_one_or_none()

            if ingredient is None:
                # Create new ingredient (without price — will be set from invoices)
                guessed_cat = guess_ingredient_category(ing_data.name)
                # Normalize unit to base (kg, l, piece)
                base_unit, _ = normalize_to_base_unit(ing_data.unit, None)
                ingredient = Ingredient(
                    restaurant_id=restaurant.id,
                    name=ing_data.name,
                    unit=base_unit,
                    category=guessed_cat,
                )
                db.add(ingredient)
                await db.flush()
                await db.refresh(ingredient)
                ingredients_created += 1

            recipe_ingredients_data.append({
                "ingredient_id": ingredient.id,
                "quantity": ing_data.quantity,
                "unit": ing_data.unit,
            })

        # Calculate food cost (will be None/partial if no prices)
        ingredients_with_prices = []
        for ri_data in recipe_ingredients_data:
            ing_result = await db.execute(
                select(Ingredient).where(Ingredient.id == ri_data["ingredient_id"])
            )
            ing = ing_result.scalar_one()
            ingredients_with_prices.append((ri_data["quantity"], ing.current_price))

        food_cost, food_cost_percent = calculate_food_cost(
            ingredients_with_prices, dish.selling_price
        )

        # Create recipe
        recipe = Recipe(
            restaurant_id=restaurant.id,
            name=dish.name,
            selling_price=dish.selling_price,
            category=dish.category,
            is_homemade=dish.is_homemade,
            food_cost=food_cost,
            food_cost_percent=food_cost_percent,
        )
        db.add(recipe)
        await db.flush()

        # Create recipe ingredients
        for ri_data in recipe_ingredients_data:
            ri = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ri_data["ingredient_id"],
                quantity=ri_data["quantity"],
                unit=ri_data["unit"],
            )
            db.add(ri)

        await db.flush()
        recipes_created += 1

    return OnboardingConfirmResponse(
        recipes_created=recipes_created,
        ingredients_created=ingredients_created,
    )
