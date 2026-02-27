"""Tests for normalize_to_base_unit and full normalization scenarios."""

import pytest
from httpx import AsyncClient

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient
from app.services.costing import normalize_to_base_unit


# --- Unit tests for normalize_to_base_unit ---


def test_normalize_g_to_kg():
    unit, price = normalize_to_base_unit("g", 0.024)
    assert unit == "kg"
    assert price == 24.0


def test_normalize_kg_stays():
    unit, price = normalize_to_base_unit("kg", 24.0)
    assert unit == "kg"
    assert price == 24.0


def test_normalize_ml_to_l():
    unit, price = normalize_to_base_unit("ml", 0.005)
    assert unit == "l"
    assert price == 5.0


def test_normalize_cl_to_l():
    unit, price = normalize_to_base_unit("cl", 0.05)
    assert unit == "l"
    assert price == 5.0


def test_normalize_l_stays():
    unit, price = normalize_to_base_unit("l", 5.0)
    assert unit == "l"
    assert price == 5.0


def test_normalize_piece_stays():
    unit, price = normalize_to_base_unit("piece", 3.5)
    assert unit == "piece"
    assert price == 3.5


def test_normalize_pce_alias():
    unit, price = normalize_to_base_unit("pce", 3.5)
    assert unit == "piece"
    assert price == 3.5


def test_normalize_none_price():
    unit, price = normalize_to_base_unit("g", None)
    assert unit == "kg"
    assert price is None


def test_normalize_unknown_unit():
    unit, price = normalize_to_base_unit("botte", 2.0)
    assert unit == "botte"
    assert price == 2.0


# --- Integration: ingredient creation normalizes unit ---


async def test_create_ingredient_normalizes_g_to_kg(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """POST /api/ingredients with unit='g' normalizes to 'kg' and adjusts price."""
    resp = await client.post(
        "/api/ingredients",
        json={"name": "Fromage test", "unit": "g", "current_price": 0.024},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["unit"] == "kg"
    assert data["current_price"] == 24.0


async def test_create_ingredient_normalizes_cl_to_l(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """POST /api/ingredients with unit='cl' normalizes to 'l' and adjusts price."""
    resp = await client.post(
        "/api/ingredients",
        json={"name": "Vin rouge test", "unit": "cl", "current_price": 0.05},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["unit"] == "l"
    assert data["current_price"] == 5.0


async def test_create_ingredient_g_no_price(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """POST /api/ingredients with unit='g' and no price normalizes unit to 'kg'."""
    resp = await client.post(
        "/api/ingredients",
        json={"name": "Sel fin test", "unit": "g"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["unit"] == "kg"
    assert data["current_price"] is None


# --- Integration: update normalizes too ---


async def test_update_ingredient_normalizes_unit(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """PUT with unit='g' and price normalizes both."""
    # Create in kg first
    create_resp = await client.post(
        "/api/ingredients",
        json={"name": "Chocolat test", "unit": "kg", "current_price": 15.0},
        headers=auth_headers,
    )
    ingredient_id = create_resp.json()["id"]

    # Update with unit="g"
    resp = await client.put(
        f"/api/ingredients/{ingredient_id}",
        json={"unit": "g", "current_price": 0.018},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["unit"] == "kg"
    assert data["current_price"] == 18.0


# --- Integration: full fromage scenario ---


async def test_fromage_full_scenario(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Full scenario: create ingredient in g (normalized to kg), recipe with 80g, verify food cost."""
    # 1. Create ingredient — user says "g" but system normalizes to kg
    resp = await client.post(
        "/api/ingredients",
        json={"name": "Fromage belge scénario", "unit": "g", "current_price": 0.024},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    ing = resp.json()
    assert ing["unit"] == "kg"
    assert ing["current_price"] == 24.0

    # 2. Create recipe with 80g
    resp = await client.post(
        "/api/recipes",
        json={
            "name": "Portion Fromage scénario",
            "selling_price": 4.0,
            "is_homemade": True,
            "ingredients": [
                {
                    "ingredient_id": ing["id"],
                    "quantity": 80,
                    "unit": "g",
                },
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    recipe = resp.json()
    # convert_quantity(80, "g", "kg") = 0.08 → 0.08 × 24 = 1.92
    assert recipe["food_cost"] == pytest.approx(1.92, abs=0.01)
    assert recipe["food_cost_percent"] == pytest.approx(48.0, abs=0.1)
