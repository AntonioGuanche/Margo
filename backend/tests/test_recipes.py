"""Tests for recipe CRUD endpoints."""

import pytest
from httpx import AsyncClient

from app.models.ingredient import Ingredient


@pytest.fixture
async def ingredients(db_session, restaurant) -> list[Ingredient]:
    """Create test ingredients with prices."""
    items = [
        Ingredient(
            restaurant_id=restaurant.id,
            name="Tomates",
            unit="kg",
            current_price=3.50,
        ),
        Ingredient(
            restaurant_id=restaurant.id,
            name="Mozzarella",
            unit="kg",
            current_price=12.00,
        ),
        Ingredient(
            restaurant_id=restaurant.id,
            name="Basilic",
            unit="piece",
            current_price=None,
        ),
    ]
    for item in items:
        db_session.add(item)
    await db_session.flush()
    for item in items:
        await db_session.refresh(item)
    return items


def _recipe_payload(ingredients: list[Ingredient]) -> dict:
    """Build a standard recipe create payload."""
    return {
        "name": "Salade Caprese",
        "selling_price": 14.50,
        "category": "Entrée",
        "ingredients": [
            {"ingredient_id": ingredients[0].id, "quantity": 0.2, "unit": "kg"},
            {"ingredient_id": ingredients[1].id, "quantity": 0.15, "unit": "kg"},
        ],
    }


async def test_create_recipe(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """POST with 2 ingredients → 201, food_cost calculated."""
    payload = _recipe_payload(ingredients)
    response = await client.post("/api/recipes", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Salade Caprese"
    assert data["selling_price"] == 14.50
    assert data["category"] == "Entrée"
    assert data["food_cost"] is not None
    # 0.2 * 3.50 + 0.15 * 12.00 = 0.70 + 1.80 = 2.50
    assert abs(data["food_cost"] - 2.50) < 0.01
    # food_cost_percent = 2.50 / 14.50 * 100 ≈ 17.24
    assert data["food_cost_percent"] is not None
    assert abs(data["food_cost_percent"] - 17.24) < 0.1
    assert data["margin_status"] == "green"
    assert len(data["ingredients"]) == 2


async def test_create_recipe_no_ingredients(client: AsyncClient, auth_headers: dict):
    """POST homemade recipe with empty ingredients → 400."""
    payload = {
        "name": "Test",
        "selling_price": 10.0,
        "is_homemade": True,
        "ingredients": [],
    }
    response = await client.post("/api/recipes", json=payload, headers=auth_headers)
    assert response.status_code == 400

    # Bought product with no ingredients → allowed (201)
    payload_bought = {
        "name": "Test Bought",
        "selling_price": 5.0,
        "is_homemade": False,
        "ingredients": [],
    }
    response = await client.post("/api/recipes", json=payload_bought, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["is_homemade"] is False


async def test_get_recipe_with_costs(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """GET → ingredient_name, unit_cost, line_cost present."""
    payload = _recipe_payload(ingredients)
    create_resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    recipe_id = create_resp.json()["id"]

    response = await client.get(f"/api/recipes/{recipe_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert len(data["ingredients"]) == 2
    tomate_ing = next(i for i in data["ingredients"] if i["ingredient_name"] == "Tomates")
    assert tomate_ing["unit_cost"] == 3.50
    assert abs(tomate_ing["line_cost"] - 0.70) < 0.01

    mozza_ing = next(i for i in data["ingredients"] if i["ingredient_name"] == "Mozzarella")
    assert mozza_ing["unit_cost"] == 12.00
    assert abs(mozza_ing["line_cost"] - 1.80) < 0.01


async def test_list_recipes(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """Create 3 recipes → GET list → 3 items."""
    for i in range(3):
        payload = {
            "name": f"Plat {i}",
            "selling_price": 10.0 + i,
            "ingredients": [
                {"ingredient_id": ingredients[0].id, "quantity": 0.1, "unit": "kg"},
            ],
        }
        await client.post("/api/recipes", json=payload, headers=auth_headers)

    response = await client.get("/api/recipes", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


async def test_list_recipes_sort_by_food_cost(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """Verify sorting by food_cost_percent."""
    # Create recipes with different food costs
    for price in [10.0, 20.0, 5.0]:
        payload = {
            "name": f"Plat {price}",
            "selling_price": price,
            "ingredients": [
                {"ingredient_id": ingredients[0].id, "quantity": 0.5, "unit": "kg"},
            ],
        }
        await client.post("/api/recipes", json=payload, headers=auth_headers)

    response = await client.get(
        "/api/recipes?sort_by=food_cost_percent&sort_order=desc", headers=auth_headers
    )
    data = response.json()
    percents = [item["food_cost_percent"] for item in data["items"]]
    assert percents == sorted(percents, reverse=True)


async def test_update_recipe_ingredients(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """PUT with new ingredients → food_cost recalculated."""
    payload = _recipe_payload(ingredients)
    create_resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    recipe_id = create_resp.json()["id"]
    original_cost = create_resp.json()["food_cost"]

    # Replace with just mozzarella, more quantity
    update_payload = {
        "ingredients": [
            {"ingredient_id": ingredients[1].id, "quantity": 0.5, "unit": "kg"},
        ],
    }
    response = await client.put(
        f"/api/recipes/{recipe_id}", json=update_payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    # New cost: 0.5 * 12.00 = 6.00
    assert abs(data["food_cost"] - 6.00) < 0.01
    assert data["food_cost"] != original_cost
    assert len(data["ingredients"]) == 1


async def test_update_recipe_price(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """Change selling_price → food_cost_percent changes."""
    payload = _recipe_payload(ingredients)
    create_resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    recipe_id = create_resp.json()["id"]
    original_percent = create_resp.json()["food_cost_percent"]

    # Double the selling price
    response = await client.put(
        f"/api/recipes/{recipe_id}",
        json={"selling_price": 29.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["food_cost_percent"] < original_percent


async def test_delete_recipe(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """DELETE → 204 → GET → 404."""
    payload = _recipe_payload(ingredients)
    create_resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    recipe_id = create_resp.json()["id"]

    response = await client.delete(f"/api/recipes/{recipe_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/recipes/{recipe_id}", headers=auth_headers)
    assert response.status_code == 404


async def test_cascade_recalculate(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """Modify ingredient price → recipe food_cost updates."""
    payload = _recipe_payload(ingredients)
    create_resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    recipe_id = create_resp.json()["id"]
    original_cost = create_resp.json()["food_cost"]

    # Double the price of Tomates
    await client.put(
        f"/api/ingredients/{ingredients[0].id}",
        json={"current_price": 7.00},
        headers=auth_headers,
    )

    # Check recipe was recalculated
    response = await client.get(f"/api/recipes/{recipe_id}", headers=auth_headers)
    data = response.json()
    # New cost: 0.2 * 7.00 + 0.15 * 12.00 = 1.40 + 1.80 = 3.20
    assert abs(data["food_cost"] - 3.20) < 0.01
    assert data["food_cost"] != original_cost


async def test_recipe_without_prices(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """Ingredients without prices → food_cost = None."""
    # Basilic has no price
    payload = {
        "name": "Salade Basilic",
        "selling_price": 8.0,
        "ingredients": [
            {"ingredient_id": ingredients[2].id, "quantity": 1.0, "unit": "piece"},
        ],
    }
    response = await client.post("/api/recipes", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["food_cost"] is None
    assert data["food_cost_percent"] is None


async def test_unit_conversion_g_to_kg(client: AsyncClient, auth_headers: dict, db_session, restaurant):
    """80g of an ingredient at 24€/kg → food_cost = 1.92€, not 1920€."""
    fromage = Ingredient(
        restaurant_id=restaurant.id,
        name="Fromage râpé",
        unit="kg",
        current_price=24.0,
    )
    db_session.add(fromage)
    await db_session.flush()
    await db_session.refresh(fromage)

    payload = {
        "name": "Croque Monsieur",
        "selling_price": 12.0,
        "ingredients": [
            {"ingredient_id": fromage.id, "quantity": 80, "unit": "g"},
        ],
    }
    resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()

    # 80g → 0.08kg × 24€/kg = 1.92€
    assert abs(data["food_cost"] - 1.92) < 0.01
    assert abs(data["food_cost_percent"] - 16.0) < 0.1

    # Check unit_cost_unit field
    ing = data["ingredients"][0]
    assert ing["unit_cost_unit"] == "kg"
    assert ing["unit_cost"] == 24.0
    assert abs(ing["line_cost"] - 1.92) < 0.01


async def test_unit_conversion_cl_to_l(client: AsyncClient, auth_headers: dict, db_session, restaurant):
    """33cl of an ingredient at 2.50€/l → food_cost = 0.825€."""
    lait = Ingredient(
        restaurant_id=restaurant.id,
        name="Lait",
        unit="l",
        current_price=2.50,
    )
    db_session.add(lait)
    await db_session.flush()
    await db_session.refresh(lait)

    payload = {
        "name": "Chocolat chaud",
        "selling_price": 5.0,
        "ingredients": [
            {"ingredient_id": lait.id, "quantity": 33, "unit": "cl"},
        ],
    }
    resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()

    # 33cl → 0.33l × 2.50€/l = 0.825€
    assert abs(data["food_cost"] - 0.825) < 0.01

    ing = data["ingredients"][0]
    assert ing["unit_cost_unit"] == "l"


async def test_unit_conversion_same_unit(client: AsyncClient, auth_headers: dict, ingredients: list[Ingredient]):
    """Same unit (kg→kg) still works correctly."""
    payload = _recipe_payload(ingredients)
    resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()

    # 0.2kg × 3.50€/kg + 0.15kg × 12.00€/kg = 0.70 + 1.80 = 2.50
    assert abs(data["food_cost"] - 2.50) < 0.01
    # unit_cost_unit should be the ingredient's unit
    assert data["ingredients"][0]["unit_cost_unit"] == "kg"


async def test_cascade_recalculate_with_conversion(
    client: AsyncClient, auth_headers: dict, db_session, restaurant
):
    """Price change → cascade recalculate with unit conversion."""
    beurre = Ingredient(
        restaurant_id=restaurant.id,
        name="Beurre",
        unit="kg",
        current_price=10.0,
    )
    db_session.add(beurre)
    await db_session.flush()
    await db_session.refresh(beurre)

    # Recipe uses 200g
    payload = {
        "name": "Tartine",
        "selling_price": 6.0,
        "ingredients": [
            {"ingredient_id": beurre.id, "quantity": 200, "unit": "g"},
        ],
    }
    create_resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    recipe_id = create_resp.json()["id"]
    # 200g → 0.2kg × 10€/kg = 2.0€
    assert abs(create_resp.json()["food_cost"] - 2.0) < 0.01

    # Update beurre price to 15€/kg
    await client.put(
        f"/api/ingredients/{beurre.id}",
        json={"current_price": 15.0},
        headers=auth_headers,
    )

    # Check recipe recalculated: 200g → 0.2kg × 15€/kg = 3.0€
    resp = await client.get(f"/api/recipes/{recipe_id}", headers=auth_headers)
    assert abs(resp.json()["food_cost"] - 3.0) < 0.01


async def test_recalculate_all(client: AsyncClient, auth_headers: dict, db_session, restaurant):
    """POST /api/recipes/recalculate-all → all recipes food costs updated."""
    # Create ingredient
    fromage = Ingredient(
        restaurant_id=restaurant.id,
        name="Fromage test",
        unit="kg",
        current_price=20.0,
    )
    db_session.add(fromage)
    await db_session.flush()
    await db_session.refresh(fromage)

    # Create 2 recipes with stale food costs (simulating pre-conversion bug)
    from app.models.recipe import Recipe, RecipeIngredient

    r1 = Recipe(
        restaurant_id=restaurant.id,
        name="Plat A",
        selling_price=10.0,
        is_homemade=True,
        food_cost=999.0,  # intentionally wrong
        food_cost_percent=999.0,
    )
    r2 = Recipe(
        restaurant_id=restaurant.id,
        name="Plat B",
        selling_price=8.0,
        is_homemade=True,
        food_cost=999.0,
        food_cost_percent=999.0,
    )
    db_session.add_all([r1, r2])
    await db_session.flush()
    await db_session.refresh(r1)
    await db_session.refresh(r2)

    # Add 100g of fromage to each recipe
    for recipe in [r1, r2]:
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=fromage.id,
            quantity=100,
            unit="g",
        )
        db_session.add(ri)
    await db_session.flush()

    # Call recalculate-all
    resp = await client.post("/api/recipes/recalculate-all", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["recalculated"] == 2

    # Verify recalculated: 100g → 0.1kg × 20€/kg = 2.0€
    await db_session.refresh(r1)
    assert r1.food_cost == pytest.approx(2.0, abs=0.01)
    assert r1.food_cost_percent == pytest.approx(20.0, abs=0.1)

    await db_session.refresh(r2)
    assert r2.food_cost == pytest.approx(2.0, abs=0.01)
    assert r2.food_cost_percent == pytest.approx(25.0, abs=0.1)


async def test_cross_restaurant_isolation(client: AsyncClient, db_session, auth_headers: dict, ingredients: list[Ingredient]):
    """Cannot access recipes from another restaurant."""
    from app.models.restaurant import Restaurant
    from app.services.auth import create_access_token

    # Create recipe for test restaurant
    payload = _recipe_payload(ingredients)
    create_resp = await client.post("/api/recipes", json=payload, headers=auth_headers)
    recipe_id = create_resp.json()["id"]

    # Create another restaurant
    other = Restaurant(name="Autre Restaurant", owner_email="other@heymargo.be")
    db_session.add(other)
    await db_session.flush()
    await db_session.refresh(other)
    other_token = create_access_token(other.id, other.owner_email)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Try to access the recipe from another restaurant
    response = await client.get(f"/api/recipes/{recipe_id}", headers=other_headers)
    assert response.status_code == 404

    # List should be empty for the other restaurant
    response = await client.get("/api/recipes", headers=other_headers)
    assert response.json()["total"] == 0
