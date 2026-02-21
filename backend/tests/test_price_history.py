"""Tests for ingredient price history."""

import datetime as dt
from pathlib import Path

import pytest

from app.models.ingredient import Ingredient
from app.models.price_history import IngredientPriceHistory

FIXTURES = Path(__file__).parent / "fixtures"


async def test_price_history_after_invoice_confirm(
    client, db_session, restaurant, auth_headers
):
    """Confirm invoice → entry in IngredientPriceHistory."""
    # Create ingredient
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf haché",
        unit="kg",
        current_price=10.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Upload invoice
    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm with price update
    await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Boeuf haché",
                    "ingredient_id": ingredient.id,
                    "unit_price": 12.00,
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )

    # Check price history via API
    resp = await client.get(
        f"/api/ingredients/{ingredient.id}/price-history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingredient_name"] == "Boeuf haché"
    assert data["current_price"] == 12.0
    assert len(data["history"]) == 1
    assert data["history"][0]["price"] == 12.0
    assert data["history"][0]["invoice_id"] == invoice_id


async def test_price_history_endpoint(client, db_session, restaurant, auth_headers):
    """GET price history with multiple entries."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Crème fraîche",
        unit="l",
        current_price=5.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Add history entries manually
    for i, price in enumerate([4.0, 4.5, 5.0]):
        entry = IngredientPriceHistory(
            ingredient_id=ingredient.id,
            price=price,
            date=dt.date(2024, 10 + i, 1),
        )
        db_session.add(entry)
    await db_session.flush()

    resp = await client.get(
        f"/api/ingredients/{ingredient.id}/price-history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["history"]) == 3
    # Sorted desc by date
    assert data["history"][0]["price"] == 5.0
    assert data["history"][2]["price"] == 4.0


async def test_price_history_empty(client, db_session, restaurant, auth_headers):
    """Ingredient with no history → empty list."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Sel",
        unit="kg",
        current_price=1.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    resp = await client.get(
        f"/api/ingredients/{ingredient.id}/price-history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingredient_name"] == "Sel"
    assert data["current_price"] == 1.0
    assert data["history"] == []
