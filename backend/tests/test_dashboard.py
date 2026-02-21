"""Tests for dashboard endpoint."""

import pytest
from httpx import AsyncClient

from app.models.ingredient import Ingredient


@pytest.fixture
async def dashboard_ingredients(db_session, restaurant) -> list[Ingredient]:
    """Create ingredients for dashboard tests."""
    items = [
        Ingredient(restaurant_id=restaurant.id, name="Farine", unit="kg", current_price=1.50),
        Ingredient(restaurant_id=restaurant.id, name="Beurre", unit="kg", current_price=8.00),
        Ingredient(restaurant_id=restaurant.id, name="Sucre", unit="kg", current_price=2.00),
    ]
    for item in items:
        db_session.add(item)
    await db_session.flush()
    for item in items:
        await db_session.refresh(item)
    return items


async def test_dashboard_empty(client: AsyncClient, auth_headers: dict):
    """No recipes → total=0, average=None."""
    response = await client.get("/api/recipes/dashboard/overview", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_recipes"] == 0
    assert data["average_food_cost_percent"] is None
    assert data["recipes_green"] == 0
    assert data["recipes_orange"] == 0
    assert data["recipes_red"] == 0
    assert data["recipes"] == []


async def test_dashboard_with_recipes(
    client: AsyncClient, auth_headers: dict, dashboard_ingredients: list[Ingredient]
):
    """3 recipes → verify average, counts, sorting."""
    ing = dashboard_ingredients

    # Green recipe: food cost = 0.1 * 1.50 = 0.15, selling = 10 → 1.5%
    await client.post(
        "/api/recipes",
        json={
            "name": "Plat Vert",
            "selling_price": 10.0,
            "ingredients": [{"ingredient_id": ing[0].id, "quantity": 0.1, "unit": "kg"}],
        },
        headers=auth_headers,
    )

    # Orange recipe: food cost = 1.0 * 8.00 = 8.00, selling = 25 → 32%
    await client.post(
        "/api/recipes",
        json={
            "name": "Plat Orange",
            "selling_price": 25.0,
            "ingredients": [{"ingredient_id": ing[1].id, "quantity": 1.0, "unit": "kg"}],
        },
        headers=auth_headers,
    )

    # Red recipe: food cost = 2.0 * 8.00 = 16.00, selling = 40 → 40%
    await client.post(
        "/api/recipes",
        json={
            "name": "Plat Rouge",
            "selling_price": 40.0,
            "ingredients": [{"ingredient_id": ing[1].id, "quantity": 2.0, "unit": "kg"}],
        },
        headers=auth_headers,
    )

    response = await client.get("/api/recipes/dashboard/overview", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_recipes"] == 3
    assert data["recipes_green"] == 1
    assert data["recipes_orange"] == 1
    assert data["recipes_red"] == 1
    assert data["average_food_cost_percent"] is not None

    # Average: (1.5 + 32.0 + 40.0) / 3 ≈ 24.5
    assert abs(data["average_food_cost_percent"] - 24.5) < 1.0

    # Sorted worst first (desc by food_cost_percent)
    percents = [r["food_cost_percent"] for r in data["recipes"]]
    assert percents[0] >= percents[1] >= percents[2]


async def test_dashboard_protected(client: AsyncClient):
    """Without token → 401."""
    response = await client.get("/api/recipes/dashboard/overview")
    assert response.status_code == 401
