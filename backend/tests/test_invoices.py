"""Tests for invoice API endpoints — upload, list, confirm, delete."""

from pathlib import Path

import pytest

from app.models.ingredient import Ingredient
from app.models.ingredient_alias import IngredientAlias
from app.models.invoice import Invoice
from app.models.recipe import Recipe, RecipeIngredient

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def xml_file_path() -> str:
    """Path to the test XML invoice fixture."""
    return str(FIXTURES / "test_invoice.xml")


async def test_upload_xml(client, auth_headers, xml_file_path):
    """Upload a valid XML invoice → 200, 2 lines extracted."""
    with open(xml_file_path, "rb") as f:
        resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test_invoice.xml", f, "application/xml")},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "xml"
    assert data["status"] == "pending_review"
    assert data["supplier_name"] == "Boucherie Dupont"
    assert data["invoice_date"] == "2024-12-15"
    assert data["total_excl_vat"] == 75.00
    assert data["total_incl_vat"] == 90.75
    assert len(data["lines"]) == 2

    line1 = data["lines"][0]
    assert line1["description"] == "Boeuf haché"
    assert line1["quantity"] == 5.0
    assert line1["unit_price"] == 12.00


async def test_upload_invalid_file(client, auth_headers, tmp_path):
    """Upload a plain text file → should not crash, returns appropriate response."""
    test_file = tmp_path / "not_an_invoice.txt"
    test_file.write_text("This is just a text file, not an invoice.")

    with open(test_file, "rb") as f:
        resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("not_an_invoice.txt", f, "text/plain")},
            headers=auth_headers,
        )

    # MIME type validation rejects text/plain
    assert resp.status_code == 415


async def test_list_invoices(client, auth_headers, xml_file_path):
    """Upload 3 invoices → GET list → 3 items."""
    for i in range(3):
        with open(xml_file_path, "rb") as f:
            await client.post(
                "/api/invoices/upload",
                files={"file": (f"invoice_{i}.xml", f, "application/xml")},
                headers=auth_headers,
            )

    resp = await client.get("/api/invoices", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    # Sorted by created_at desc
    assert data["items"][0]["supplier_name"] == "Boucherie Dupont"


async def test_list_invoices_filter_status(client, auth_headers, xml_file_path):
    """Filter invoices by status."""
    with open(xml_file_path, "rb") as f:
        await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )

    # Filter pending
    resp = await client.get("/api/invoices?status=pending_review", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # Filter confirmed → 0
    resp = await client.get("/api/invoices?status=confirmed", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_get_invoice_detail(client, auth_headers, xml_file_path):
    """GET /api/invoices/{id} returns detail with lines."""
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == invoice_id
    assert data["supplier_name"] == "Boucherie Dupont"
    assert len(data["lines"]) == 2


async def test_confirm_updates_prices(client, auth_headers, db_session, restaurant, xml_file_path):
    """Upload + confirm with ingredient_id → price updated in DB."""
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

    # Upload
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm
    confirm_resp = await client.post(
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
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()
    assert data["prices_updated"] == 1

    # Verify price updated
    await db_session.refresh(ingredient)
    assert ingredient.current_price == 12.00


async def test_confirm_creates_ingredient(client, auth_headers, db_session, restaurant, xml_file_path):
    """Confirm with create_ingredient_name → new ingredient created."""
    # Upload
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm with new ingredient
    confirm_resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Lard fumé",
                    "create_ingredient_name": "Lard fumé",
                    "unit_price": 7.50,
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()
    assert data["ingredients_created"] == 1
    assert data["aliases_saved"] >= 1


async def test_confirm_saves_alias(client, auth_headers, db_session, restaurant, xml_file_path):
    """Confirm → alias saved, next upload auto-matches."""
    # Create ingredient with different name
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf haché premium",
        unit="kg",
        current_price=10.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Upload
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm — "Boeuf haché" maps to ingredient "Boeuf haché premium"
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

    # Upload again — should now match via alias
    with open(xml_file_path, "rb") as f:
        upload2_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test2.xml", f, "application/xml")},
            headers=auth_headers,
        )

    lines = upload2_resp.json()["lines"]
    boeuf_line = next(l for l in lines if l["description"] == "Boeuf haché")
    assert boeuf_line["matched_ingredient_id"] == ingredient.id
    assert boeuf_line["match_confidence"] == "alias"


async def test_confirm_cascades_recalculate(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Confirm → recipes recalculated when ingredient price changes."""
    # Create ingredient + recipe
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf haché",
        unit="kg",
        current_price=10.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

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

    # Upload + confirm with new price
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    confirm_resp = await client.post(
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
    data = confirm_resp.json()
    assert data["recipes_recalculated"] >= 1

    # Verify recipe recalculated: 0.2 * 12.00 = 2.40, 2.40/15.0*100 = 16.0%
    await db_session.refresh(recipe)
    assert recipe.food_cost == pytest.approx(2.4, abs=0.01)
    assert recipe.food_cost_percent == pytest.approx(16.0, abs=0.1)


async def test_delete_pending(client, auth_headers, xml_file_path):
    """Delete a pending invoice → 204."""
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    resp = await client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_confirmed_allowed(client, auth_headers, db_session, restaurant, xml_file_path):
    """Delete a confirmed invoice → 204 (allowed since Sprint 24)."""
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm it first
    await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": []},
        headers=auth_headers,
    )

    # Delete confirmed invoice — now allowed
    resp = await client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_confirm_multi_recipe(client, auth_headers, db_session, restaurant, xml_file_path):
    """Confirm with recipe_links → multiple RecipeIngredient rows created."""
    # Create ingredient
    ingredient = Ingredient(
        restaurant_id=restaurant.id, name="Viande hachée", unit="kg", current_price=10.0
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Create two existing recipes
    recipe1 = Recipe(
        restaurant_id=restaurant.id, name="Spaghetti Bolo", selling_price=14.0
    )
    recipe2 = Recipe(
        restaurant_id=restaurant.id, name="Lasagne", selling_price=16.0
    )
    db_session.add_all([recipe1, recipe2])
    await db_session.flush()
    await db_session.refresh(recipe1)
    await db_session.refresh(recipe2)

    # Upload invoice
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm with multi-recipe links
    confirm_resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Viande hachée",
                    "ingredient_id": ingredient.id,
                    "unit_price": 12.00,
                    "unit": "kg",
                    "recipe_links": [
                        {"recipe_id": recipe1.id, "quantity": 0.15, "unit": "kg"},
                        {"recipe_id": recipe2.id, "quantity": 0.12, "unit": "kg"},
                    ],
                },
            ]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()
    assert data["prices_updated"] == 1

    # Verify 2 RecipeIngredient rows were created
    from sqlalchemy import select, func
    count_result = await db_session.execute(
        select(func.count()).select_from(
            select(RecipeIngredient).where(
                RecipeIngredient.ingredient_id == ingredient.id
            ).subquery()
        )
    )
    assert count_result.scalar_one() == 2


async def test_reconfirm_allowed(client, auth_headers, db_session, restaurant, xml_file_path):
    """Re-confirming a confirmed invoice → 200 (allowed since Sprint 27)."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id, name="Poulet", unit="kg", current_price=8.0
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # First confirm
    resp1 = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": [{"description": "Poulet", "ingredient_id": ingredient.id, "unit_price": 9.0, "unit": "kg"}]},
        headers=auth_headers,
    )
    assert resp1.status_code == 200

    # Re-confirm with corrected price
    resp2 = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": [{"description": "Poulet", "ingredient_id": ingredient.id, "unit_price": 9.50, "unit": "kg"}]},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["prices_updated"] == 1

    await db_session.refresh(ingredient)
    assert ingredient.current_price == 9.50


async def test_patch_confirmed_allowed(client, auth_headers, xml_file_path):
    """Patching supplier/date on a confirmed invoice → 200 (allowed since Sprint 27)."""
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm
    await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": []},
        headers=auth_headers,
    )

    # Patch confirmed invoice — now allowed
    resp = await client.patch(
        f"/api/invoices/{invoice_id}",
        json={"supplier_name": "Nouveau Fournisseur"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["supplier_name"] == "Nouveau Fournisseur"


async def test_confirm_syncs_ingredient_unit(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Confirm with unit='kg' on ingredient with unit='g' → ingredient.unit becomes 'kg'."""
    # Ingredient created by onboarding with "g" unit (recipe-level unit)
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Fromage râpé",
        unit="g",
        current_price=None,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)
    assert ingredient.unit == "g"

    # Upload invoice
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm with unit="kg" (supplier unit) — should sync ingredient.unit
    confirm_resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Fromage râpé",
                    "ingredient_id": ingredient.id,
                    "unit_price": 24.00,
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200

    # Verify ingredient.unit synced to "kg"
    await db_session.refresh(ingredient)
    assert ingredient.unit == "kg"
    assert ingredient.current_price == 24.00


async def test_confirm_unit_sync_fixes_food_cost(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Full scenario: ingredient unit='g' + recipe 80g → confirm with kg → food cost correct."""
    # Ingredient created with "g" unit (from onboarding)
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Fromage belge",
        unit="g",
        current_price=None,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Recipe using 80g of this ingredient
    recipe = Recipe(
        restaurant_id=restaurant.id,
        name="Portion de Fromage",
        selling_price=4.0,
        is_homemade=True,
    )
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=80,
        unit="g",
    )
    db_session.add(ri)
    await db_session.flush()

    # Upload + confirm invoice with kg unit
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Fromage belge",
                    "ingredient_id": ingredient.id,
                    "unit_price": 24.00,
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )

    # After confirm: ingredient.unit = "kg", price = 24€/kg
    # Recipe: 80g → convert_quantity(80, "g", "kg") = 0.08kg × 24€/kg = 1.92€
    await db_session.refresh(ingredient)
    assert ingredient.unit == "kg"

    await db_session.refresh(recipe)
    assert recipe.food_cost == pytest.approx(1.92, abs=0.01)
    assert recipe.food_cost_percent == pytest.approx(48.0, abs=0.1)


async def test_confirm_ignores_unknown_unit(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Confirm with unit='casier' → ingredient.unit unchanged (not a recognized unit)."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Bière Blonde",
        unit="piece",
        current_price=1.50,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Bière Blonde casier",
                    "ingredient_id": ingredient.id,
                    "unit_price": 1.80,
                    "unit": "casier",
                },
            ]
        },
        headers=auth_headers,
    )

    # unit stays "piece" — "casier" is not a recognized unit
    await db_session.refresh(ingredient)
    assert ingredient.unit == "piece"
    assert ingredient.current_price == 1.80


async def test_invoices_protected(client):
    """Without auth token → 401."""
    resp = await client.get("/api/invoices")
    assert resp.status_code == 401
