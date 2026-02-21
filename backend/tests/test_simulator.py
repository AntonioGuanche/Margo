"""Tests for recipe simulator."""

import pytest

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient
from app.models.restaurant import Restaurant
from app.services.auth import create_access_token


async def _create_recipe_with_ingredients(db_session, restaurant):
    """Helper: create a recipe with 2 ingredients."""
    ing1 = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf",
        unit="kg",
        current_price=20.0,
    )
    ing2 = Ingredient(
        restaurant_id=restaurant.id,
        name="Pomme de terre",
        unit="kg",
        current_price=2.0,
    )
    db_session.add_all([ing1, ing2])
    await db_session.flush()
    await db_session.refresh(ing1)
    await db_session.refresh(ing2)

    recipe = Recipe(
        restaurant_id=restaurant.id,
        name="Steak-frites",
        selling_price=25.0,
        food_cost=7.0,
        food_cost_percent=28.0,
    )
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    ri1 = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ing1.id,
        quantity=0.25,
        unit="kg",
    )
    ri2 = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ing2.id,
        quantity=0.5,
        unit="kg",
    )
    db_session.add_all([ri1, ri2])
    await db_session.flush()

    return recipe, ing1, ing2


async def test_simulate_price_change(
    client, db_session, restaurant, auth_headers
):
    """Increase selling_price → food_cost_percent decreases."""
    recipe, ing1, ing2 = await _create_recipe_with_ingredients(
        db_session, restaurant
    )

    resp = await client.post(
        f"/api/recipes/{recipe.id}/simulate",
        json={"new_selling_price": 30.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["recipe_name"] == "Steak-frites"
    # Current: food_cost = 0.25*20 + 0.5*2 = 6.0, selling = 25 → 24%
    assert data["current"]["selling_price"] == 25.0
    assert data["current"]["food_cost"] == 6.0

    # Simulated: same food cost, selling = 30 → 20%
    assert data["simulated"]["selling_price"] == 30.0
    assert data["simulated"]["food_cost"] == 6.0
    assert data["simulated"]["food_cost_percent"] == 20.0


async def test_simulate_portion_change(
    client, db_session, restaurant, auth_headers
):
    """Reduce ingredient quantity → food_cost decreases."""
    recipe, ing1, ing2 = await _create_recipe_with_ingredients(
        db_session, restaurant
    )

    resp = await client.post(
        f"/api/recipes/{recipe.id}/simulate",
        json={
            "ingredient_adjustments": [
                {"ingredient_id": ing1.id, "new_quantity": 0.2},  # reduce beef from 0.25 to 0.2
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Current: 0.25*20 + 0.5*2 = 6.0
    assert data["current"]["food_cost"] == 6.0

    # Simulated: 0.2*20 + 0.5*2 = 5.0
    assert data["simulated"]["food_cost"] == 5.0
    # One ingredient should be marked as changed
    changed = [i for i in data["simulated"]["ingredients"] if i["changed"]]
    assert len(changed) == 1
    assert changed[0]["ingredient_name"] == "Boeuf"


async def test_simulate_monthly_impact(
    client, db_session, restaurant, auth_headers
):
    """With weekly_sales → monthly_impact calculated."""
    recipe, ing1, ing2 = await _create_recipe_with_ingredients(
        db_session, restaurant
    )

    resp = await client.post(
        f"/api/recipes/{recipe.id}/simulate",
        json={
            "new_selling_price": 30.0,
            "estimated_weekly_sales": 50,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Current margin: 25 - 6 = 19
    # Simulated margin: 30 - 6 = 24
    # Monthly impact: (24 - 19) * 50 * 4 = 1000
    assert data["monthly_impact"] == 1000.0


async def test_simulate_no_changes(
    client, db_session, restaurant, auth_headers
):
    """Simulate without modifications → current == simulated."""
    recipe, ing1, ing2 = await _create_recipe_with_ingredients(
        db_session, restaurant
    )

    resp = await client.post(
        f"/api/recipes/{recipe.id}/simulate",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["current"]["food_cost"] == data["simulated"]["food_cost"]
    assert data["current"]["selling_price"] == data["simulated"]["selling_price"]
    assert data["current"]["food_cost_percent"] == data["simulated"]["food_cost_percent"]


async def test_apply_simulation(
    client, db_session, restaurant, auth_headers
):
    """Apply simulation → recipe actually modified in DB."""
    recipe, ing1, ing2 = await _create_recipe_with_ingredients(
        db_session, restaurant
    )

    resp = await client.post(
        f"/api/recipes/{recipe.id}/apply-simulation",
        json={
            "new_selling_price": 30.0,
            "ingredient_adjustments": [
                {"ingredient_id": ing1.id, "new_quantity": 0.2},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify changes were applied
    assert data["current"]["selling_price"] == 30.0

    # Verify in DB
    recipe_resp = await client.get(
        f"/api/recipes/{recipe.id}", headers=auth_headers
    )
    recipe_data = recipe_resp.json()
    assert recipe_data["selling_price"] == 30.0
    # Beef should be 0.2 now
    beef = [i for i in recipe_data["ingredients"] if i["ingredient_name"] == "Boeuf"]
    assert beef[0]["quantity"] == 0.2


async def test_simulate_cross_restaurant(
    client, db_session, restaurant, auth_headers
):
    """Simulate recipe of another restaurant → 404."""
    # Create another restaurant
    other = Restaurant(name="Autre", owner_email="other@heymargo.be")
    db_session.add(other)
    await db_session.flush()
    await db_session.refresh(other)

    recipe = Recipe(
        restaurant_id=other.id,
        name="Secret Recipe",
        selling_price=50.0,
    )
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    resp = await client.post(
        f"/api/recipes/{recipe.id}/simulate",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 404
