"""Onboarding routes — AI-powered menu extraction and batch recipe creation."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
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
from app.services.costing import calculate_food_cost
from app.services.onboarding_ai import extract_menu_from_image, suggest_ingredients_batch
from app.services.storage import save_upload

router = APIRouter()


@router.post("/extract-menu", response_model=MenuExtractionResponse)
async def extract_menu(
    file: UploadFile,
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> MenuExtractionResponse:
    """Upload a menu image and extract dishes using AI."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit être une image (JPEG, PNG, etc.)",
        )

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
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> OnboardingConfirmResponse:
    """Confirm onboarding: create ingredients and recipes in one transaction."""
    recipes_created = 0
    ingredients_created = 0

    for dish in request.dishes:
        recipe_ingredients_data = []

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
                ingredient = Ingredient(
                    restaurant_id=restaurant.id,
                    name=ing_data.name,
                    unit=ing_data.unit,
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
