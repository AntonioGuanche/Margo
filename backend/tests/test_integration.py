"""End-to-end integration tests — full flows across multiple endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient


FIXTURES = Path(__file__).parent / "fixtures"


async def test_full_onboarding_flow(client, db_session, restaurant, auth_headers):
    """Login → extract menu (mocked) → suggest ingredients (mocked) → confirm → dashboard shows recipes."""

    # Mock Claude API for menu extraction
    mock_dishes = [
        {"name": "Carbonara", "price": 16.50, "category": "Pâtes"},
        {"name": "Tiramisu", "price": 9.00, "category": "Desserts"},
    ]

    with patch(
        "app.routers.onboarding.extract_menu_from_image",
        new_callable=AsyncMock,
        return_value=mock_dishes,
    ):
        # Create a dummy image file for upload
        resp = await client.post(
            "/api/onboarding/extract-menu",
            files={"file": ("menu.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["dishes"]) == 2
        assert data["dishes"][0]["name"] == "Carbonara"

    # Mock suggestions
    mock_suggestions = {
        "Carbonara": [
            {"name": "Spaghetti", "quantity": 0.15, "unit": "kg"},
            {"name": "Lardons", "quantity": 0.1, "unit": "kg"},
        ],
        "Tiramisu": [
            {"name": "Mascarpone", "quantity": 0.15, "unit": "kg"},
        ],
    }

    with patch(
        "app.routers.onboarding.suggest_ingredients_batch",
        new_callable=AsyncMock,
        return_value=mock_suggestions,
    ):
        resp = await client.post(
            "/api/onboarding/suggest-ingredients",
            json={
                "dishes": [
                    {"name": "Carbonara", "price": 16.50, "category": "Pâtes"},
                    {"name": "Tiramisu", "price": 9.00, "category": "Desserts"},
                ]
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        suggested = resp.json()["dishes"]
        assert len(suggested) == 2

    # Confirm onboarding → creates ingredients and recipes
    resp = await client.post(
        "/api/onboarding/confirm",
        json={
            "dishes": [
                {
                    "name": "Carbonara",
                    "selling_price": 16.50,
                    "category": "Pâtes",
                    "ingredients": [
                        {"name": "Spaghetti", "quantity": 0.15, "unit": "kg"},
                        {"name": "Lardons", "quantity": 0.1, "unit": "kg"},
                    ],
                },
                {
                    "name": "Tiramisu",
                    "selling_price": 9.00,
                    "category": "Desserts",
                    "ingredients": [
                        {"name": "Mascarpone", "quantity": 0.15, "unit": "kg"},
                    ],
                },
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    confirm_data = resp.json()
    assert confirm_data["recipes_created"] == 2
    assert confirm_data["ingredients_created"] == 3

    # Dashboard should show the recipes
    resp = await client.get(
        "/api/recipes/dashboard/overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    dashboard = resp.json()
    assert dashboard["total_recipes"] == 2


async def test_full_invoice_flow(client, db_session, restaurant, auth_headers):
    """Upload XML → review → confirm → prices updated → alerts created → food cost recalculated."""

    # Create ingredient with known price
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf haché",
        unit="kg",
        current_price=10.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Create a recipe using this ingredient
    recipe = Recipe(
        restaurant_id=restaurant.id,
        name="Burger",
        selling_price=15.0,
        food_cost=2.0,
        food_cost_percent=13.33,
    )
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=0.2,
        unit="kg",
    )
    db_session.add(ri)
    await db_session.flush()

    # Upload invoice
    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
        resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("invoice.xml", f, "application/xml")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    invoice_id = resp.json()["invoice_id"]

    # Confirm with higher price (20% increase → critical alert)
    resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Boeuf haché",
                    "ingredient_id": ingredient.id,
                    "unit_price": 12.0,
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    confirm = resp.json()
    assert confirm["prices_updated"] == 1
    assert confirm["recipes_recalculated"] >= 1

    # Check alerts were created
    resp = await client.get("/api/alerts", headers=auth_headers)
    assert resp.status_code == 200
    alerts = resp.json()
    assert alerts["total"] > 0
    # Should have critical alert (20% increase)
    severities = [a["severity"] for a in alerts["items"]]
    assert "critical" in severities

    # Verify ingredient price was updated
    resp = await client.get(
        f"/api/ingredients/{ingredient.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["current_price"] == 12.0

    # Verify recipe food cost was recalculated
    resp = await client.get(
        f"/api/recipes/{recipe.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    recipe_data = resp.json()
    # 0.2 * 12.0 = 2.4 → 2.4/15.0 = 16%
    assert recipe_data["food_cost"] == 2.4
    assert abs(recipe_data["food_cost_percent"] - 16.0) < 0.1


async def test_simulator_flow(client, db_session, restaurant, auth_headers):
    """Create recipe → simulate changes → apply → verify modifications persisted."""

    # Create ingredient
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Saumon",
        unit="kg",
        current_price=25.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Create recipe
    resp = await client.post(
        "/api/recipes",
        json={
            "name": "Saumon grillé",
            "selling_price": 22.0,
            "category": "Poissons",
            "ingredients": [
                {"ingredient_id": ingredient.id, "quantity": 0.18, "unit": "kg"},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    recipe_id = resp.json()["id"]

    # Simulate — raise selling price
    resp = await client.post(
        f"/api/recipes/{recipe_id}/simulate",
        json={
            "new_selling_price": 26.0,
            "estimated_weekly_sales": 40,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    sim = resp.json()
    assert sim["current"]["selling_price"] == 22.0
    assert sim["simulated"]["selling_price"] == 26.0
    assert sim["simulated"]["food_cost_percent"] < sim["current"]["food_cost_percent"]
    assert sim["monthly_impact"] is not None
    assert sim["monthly_impact"] > 0  # Positive impact (more margin)

    # Apply the simulation
    resp = await client.post(
        f"/api/recipes/{recipe_id}/apply-simulation",
        json={
            "new_selling_price": 26.0,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Verify changes persisted
    resp = await client.get(
        f"/api/recipes/{recipe_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["selling_price"] == 26.0
