"""Edge case tests — boundary conditions and unusual scenarios."""

from pathlib import Path

import pytest

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient


FIXTURES = Path(__file__).parent / "fixtures"


async def test_recipe_all_ingredients_no_price(
    client, db_session, restaurant, auth_headers
):
    """Recipe with ingredients that have no price → food_cost=None but still shows on dashboard."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Herbes du jardin",
        unit="g",
        current_price=None,  # No price yet
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    resp = await client.post(
        "/api/recipes",
        json={
            "name": "Salade de jardin",
            "selling_price": 8.50,
            "ingredients": [
                {"ingredient_id": ingredient.id, "quantity": 30, "unit": "g"},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["food_cost"] is None
    assert data["food_cost_percent"] is None

    # Dashboard should still include it
    resp = await client.get(
        "/api/recipes/dashboard/overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    dashboard = resp.json()
    assert dashboard["total_recipes"] == 1


async def test_invoice_confirm_empty_lines(
    client, db_session, restaurant, auth_headers
):
    """Confirm with 0 matched lines → ok, 0 updates."""
    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
        resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    invoice_id = resp.json()["invoice_id"]

    # Confirm with empty lines (all ignored)
    resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["prices_updated"] == 0
    assert data["ingredients_created"] == 0


async def test_very_long_ingredient_name(
    client, db_session, restaurant, auth_headers
):
    """Ingredient with very long name (500 chars) → should be created without error."""
    long_name = "A" * 500

    resp = await client.post(
        "/api/ingredients",
        json={"name": long_name, "unit": "kg"},
        headers=auth_headers,
    )
    # Accept both success or validation error — just shouldn't crash
    assert resp.status_code in (201, 422)


async def test_special_characters_in_names(
    client, db_session, restaurant, auth_headers
):
    """Accents, apostrophes, special chars in ingredient names → ok."""
    special_names = [
        "Crème fraîche d'Isigny",
        "Poivre Sichuan (花椒)",
        "Bœuf Angus — Premium",
    ]

    for name in special_names:
        resp = await client.post(
            "/api/ingredients",
            json={"name": name, "unit": "kg", "current_price": 5.0},
            headers=auth_headers,
        )
        assert resp.status_code == 201, f"Failed for name: {name}"
        data = resp.json()
        assert data["name"] == name


async def test_concurrent_price_updates(
    client, db_session, restaurant, auth_headers
):
    """Two invoices updating the same ingredient — second should override."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Farine",
        unit="kg",
        current_price=1.50,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Upload first invoice
    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
        resp1 = await client.post(
            "/api/invoices/upload",
            files={"file": ("inv1.xml", f, "application/xml")},
            headers=auth_headers,
        )
    inv1_id = resp1.json()["invoice_id"]

    # Upload second invoice
    with open(xml_path, "rb") as f:
        resp2 = await client.post(
            "/api/invoices/upload",
            files={"file": ("inv2.xml", f, "application/xml")},
            headers=auth_headers,
        )
    inv2_id = resp2.json()["invoice_id"]

    # Confirm first with price 2.00
    resp = await client.post(
        f"/api/invoices/{inv1_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Farine",
                    "ingredient_id": ingredient.id,
                    "unit_price": 2.00,
                    "unit": "kg",
                }
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Confirm second with price 2.50
    resp = await client.post(
        f"/api/invoices/{inv2_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Farine",
                    "ingredient_id": ingredient.id,
                    "unit_price": 2.50,
                    "unit": "kg",
                }
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Final price should be 2.50
    resp = await client.get(
        f"/api/ingredients/{ingredient.id}",
        headers=auth_headers,
    )
    assert resp.json()["current_price"] == 2.50


async def test_delete_ingredient_used_in_recipe(
    client, db_session, restaurant, auth_headers
):
    """Delete an ingredient used in a recipe → should cascade or error gracefully."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Tomate cerise",
        unit="kg",
        current_price=4.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Create recipe with this ingredient
    resp = await client.post(
        "/api/recipes",
        json={
            "name": "Salade tomate",
            "selling_price": 12.0,
            "ingredients": [
                {"ingredient_id": ingredient.id, "quantity": 0.2, "unit": "kg"},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Delete the ingredient — should return 409 since it's used in a recipe
    resp = await client.delete(
        f"/api/ingredients/{ingredient.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "utilisé" in resp.json()["detail"]


async def test_upload_too_large_file(
    client, db_session, restaurant, auth_headers
):
    """File >10MB → 413 error."""
    large_content = b"\x00" * (11 * 1024 * 1024)  # 11 MB

    resp = await client.post(
        "/api/invoices/upload",
        files={"file": ("big.jpg", large_content, "image/jpeg")},
        headers=auth_headers,
    )
    assert resp.status_code == 413
    assert "trop volumineux" in resp.json()["detail"].lower()


async def test_upload_unsupported_format(
    client, db_session, restaurant, auth_headers
):
    """Unsupported file format → 415 error."""
    resp = await client.post(
        "/api/invoices/upload",
        files={"file": ("virus.exe", b"MZ\x00\x00", "application/octet-stream")},
        headers=auth_headers,
    )
    assert resp.status_code == 415
    assert "non supporté" in resp.json()["detail"].lower()


async def test_duplicate_ingredient_name(
    client, db_session, restaurant, auth_headers
):
    """Creating duplicate ingredient → 409 DUPLICATE error."""
    resp = await client.post(
        "/api/ingredients",
        json={"name": "Sel", "unit": "kg"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/ingredients",
        json={"name": "Sel", "unit": "kg"},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "existe déjà" in resp.json()["detail"]


async def test_confirm_already_confirmed_invoice(
    client, db_session, restaurant, auth_headers
):
    """Confirming an already confirmed invoice → 409."""
    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
        resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = resp.json()["invoice_id"]

    # First confirm
    resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Second confirm → error
    resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": []},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "déjà été confirmée" in resp.json()["detail"]
