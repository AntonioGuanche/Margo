"""Tests for onboarding endpoints (AI mocked)."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from app.models.ingredient import Ingredient


# --- Fixtures ---

@pytest.fixture
def mock_extract(monkeypatch):
    """Mock AI menu extraction — patch where it's imported (router module)."""
    async def fake_extract(image_path):
        return [
            {"name": "Carbonnade flamande", "price": 19.50, "category": "plat"},
            {"name": "Dame blanche", "price": 8.50, "category": "dessert"},
        ]
    monkeypatch.setattr("app.routers.onboarding.extract_menu_from_image", fake_extract)


@pytest.fixture
def mock_suggest(monkeypatch):
    """Mock AI ingredient suggestion — patch where it's imported (router module)."""
    async def fake_suggest(dish_name, category=None):
        suggestions = {
            "Carbonnade flamande": [
                {"name": "Boeuf", "quantity": 250, "unit": "g"},
                {"name": "Bière brune", "quantity": 15, "unit": "cl"},
                {"name": "Oignons", "quantity": 150, "unit": "g"},
            ],
            "Dame blanche": [
                {"name": "Glace vanille", "quantity": 150, "unit": "g"},
                {"name": "Chocolat", "quantity": 50, "unit": "g"},
            ],
        }
        return suggestions.get(dish_name, [])

    async def fake_batch(dishes):
        result = {}
        for d in dishes:
            result[d["name"]] = await fake_suggest(d["name"], d.get("category"))
        return result

    monkeypatch.setattr("app.routers.onboarding.suggest_ingredients_batch", fake_batch)


@pytest.fixture
def test_image_path():
    """Path to a minimal test JPEG."""
    return Path(__file__).parent / "fixtures" / "test_menu.jpg"


# --- Tests ---

async def test_extract_menu(
    client: AsyncClient, auth_headers: dict, mock_extract, test_image_path: Path
):
    """Upload an image → 200, returns list of dishes (mocked)."""
    with open(test_image_path, "rb") as f:
        response = await client.post(
            "/api/onboarding/extract-menu",
            headers=auth_headers,
            files={"file": ("menu.jpg", f, "image/jpeg")},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["dishes"]) == 2
    assert data["dishes"][0]["name"] == "Carbonnade flamande"
    assert data["dishes"][0]["price"] == 19.50
    assert data["dishes"][1]["name"] == "Dame blanche"
    assert data["image_path"]  # path is set


async def test_suggest_ingredients(
    client: AsyncClient, auth_headers: dict, mock_suggest
):
    """Send 2 dishes → 200, returns ingredients for each."""
    response = await client.post(
        "/api/onboarding/suggest-ingredients",
        headers=auth_headers,
        json={
            "dishes": [
                {"name": "Carbonnade flamande", "price": 19.50, "category": "plat"},
                {"name": "Dame blanche", "price": 8.50, "category": "dessert"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["dishes"]) == 2

    carbo = data["dishes"][0]
    assert carbo["name"] == "Carbonnade flamande"
    assert len(carbo["ingredients"]) == 3
    assert carbo["ingredients"][0]["name"] == "Boeuf"

    dame = data["dishes"][1]
    assert dame["name"] == "Dame blanche"
    assert len(dame["ingredients"]) == 2


async def test_confirm_creates_recipes_and_ingredients(
    client: AsyncClient, auth_headers: dict, db_session
):
    """Confirm with 2 dishes → recipes and ingredients created in DB."""
    response = await client.post(
        "/api/onboarding/confirm",
        headers=auth_headers,
        json={
            "dishes": [
                {
                    "name": "Carbonnade flamande",
                    "selling_price": 19.50,
                    "category": "plat",
                    "ingredients": [
                        {"name": "Boeuf", "quantity": 250, "unit": "g"},
                        {"name": "Bière brune", "quantity": 15, "unit": "cl"},
                    ],
                },
                {
                    "name": "Dame blanche",
                    "selling_price": 8.50,
                    "category": "dessert",
                    "ingredients": [
                        {"name": "Glace vanille", "quantity": 150, "unit": "g"},
                        {"name": "Chocolat", "quantity": 50, "unit": "g"},
                    ],
                },
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["recipes_created"] == 2
    assert data["ingredients_created"] == 4

    # Verify recipes exist
    recipes_resp = await client.get("/api/recipes", headers=auth_headers)
    assert recipes_resp.json()["total"] == 2


async def test_confirm_reuses_existing_ingredients(
    client: AsyncClient, auth_headers: dict, db_session, restaurant
):
    """Create ingredient 'Boeuf' first, then confirm → no duplicate."""
    # Pre-create Boeuf
    existing = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf",
        unit="g",
        current_price=15.0,
    )
    db_session.add(existing)
    await db_session.flush()

    response = await client.post(
        "/api/onboarding/confirm",
        headers=auth_headers,
        json={
            "dishes": [
                {
                    "name": "Steak frites",
                    "selling_price": 22.00,
                    "category": "plat",
                    "ingredients": [
                        {"name": "Boeuf", "quantity": 300, "unit": "g"},
                        {"name": "Pommes de terre", "quantity": 200, "unit": "g"},
                    ],
                },
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["recipes_created"] == 1
    assert data["ingredients_created"] == 1  # Only Pommes de terre, Boeuf already exists


async def test_confirm_empty(client: AsyncClient, auth_headers: dict):
    """Confirm with empty dishes → 0 recipes, 0 ingredients."""
    response = await client.post(
        "/api/onboarding/confirm",
        headers=auth_headers,
        json={"dishes": []},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["recipes_created"] == 0
    assert data["ingredients_created"] == 0


async def test_extract_menu_no_file(client: AsyncClient, auth_headers: dict):
    """POST without file → 422."""
    response = await client.post(
        "/api/onboarding/extract-menu",
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_onboarding_protected(client: AsyncClient):
    """Without token → 401."""
    response = await client.post("/api/onboarding/extract-menu")
    assert response.status_code == 401

    response = await client.post("/api/onboarding/suggest-ingredients", json={"dishes": []})
    assert response.status_code == 401

    response = await client.post("/api/onboarding/confirm", json={"dishes": []})
    assert response.status_code == 401
