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


async def test_confirm_normalizes_price_to_ingredient_unit(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Confirm with unit='g' on ingredient in 'kg' → price normalized to €/kg, unit unchanged."""
    # Ingredient stored in kg
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Beurre",
        unit="kg",
        current_price=20.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Upload invoice
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm with unit="g", unit_price=0.024 (€/g) → should normalize to 24 €/kg
    confirm_resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Beurre",
                    "ingredient_id": ingredient.id,
                    "unit_price": 0.024,
                    "unit": "g",
                },
            ]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200

    # Unit stays "kg", price normalized: 0.024 €/g × 1000 = 24 €/kg
    await db_session.refresh(ingredient)
    assert ingredient.unit == "kg"
    assert ingredient.current_price == pytest.approx(24.0, abs=0.01)


async def test_confirm_same_unit_no_normalization(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Confirm with same unit → price stored as-is."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Fromage",
        unit="kg",
        current_price=20.0,
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
                    "description": "Fromage",
                    "ingredient_id": ingredient.id,
                    "unit_price": 24.00,
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )

    await db_session.refresh(ingredient)
    assert ingredient.unit == "kg"
    assert ingredient.current_price == 24.00


async def test_confirm_price_normalization_fixes_food_cost(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Full scenario: ingredient in kg (base unit) + recipe 80g → confirm with kg price → food cost correct."""
    # Ingredient stored in "kg" (base unit — all ingredients are in base unit after Sprint 34)
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Fromage belge",
        unit="kg",
        current_price=None,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Recipe using 80g (chef's unit)
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

    # Confirm: invoice says 24 €/kg
    # normalize_to_base_unit("kg", 24.0) → ("kg", 24.0) — already base
    # Recipe: convert_quantity(80, "g", "kg") = 0.08 → 0.08 × 24 = 1.92€ ✓
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

    # Unit stays "kg", price = 24 €/kg
    await db_session.refresh(ingredient)
    assert ingredient.unit == "kg"
    assert ingredient.current_price == pytest.approx(24.0, abs=0.01)

    # Recipe: convert_quantity(80, "g", "kg") = 0.08 → 0.08 × 24 = 1.92€
    await db_session.refresh(recipe)
    assert recipe.food_cost == pytest.approx(1.92, abs=0.01)
    assert recipe.food_cost_percent == pytest.approx(48.0, abs=0.1)


async def test_confirm_ignores_unknown_unit(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Confirm with unit='casier' → no conversion, price stored as-is."""
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

    # unit stays "piece", price as-is (no conversion possible)
    await db_session.refresh(ingredient)
    assert ingredient.unit == "piece"
    assert ingredient.current_price == 1.80


async def test_delete_confirmed_with_price_history(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Delete a confirmed invoice that has price_history entries → 204, no FK crash.

    Regression test for Sprint 38: IngredientPriceHistory.invoice_id FK had no
    ondelete, causing a crash when deleting invoices that were referenced by
    price history rows. Fix: SET NULL on price_history.invoice_id before delete.
    """
    from app.models.price_history import IngredientPriceHistory
    from sqlalchemy import select

    # Create an ingredient and upload + confirm an invoice to generate price history
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Viande test",
        unit="kg",
        current_price=10.0,
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

    # Confirm the invoice — this creates a IngredientPriceHistory row with invoice_id set
    confirm_resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Boeuf haché",
                    "ingredient_id": ingredient.id,
                    "unit_price": 15.0,
                    "unit": "kg",
                }
            ]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200

    # Verify price history was created with invoice_id set
    ph_result = await db_session.execute(
        select(IngredientPriceHistory).where(
            IngredientPriceHistory.ingredient_id == ingredient.id
        )
    )
    ph_rows = ph_result.scalars().all()
    assert len(ph_rows) == 1
    assert ph_rows[0].invoice_id == invoice_id

    # Delete the confirmed invoice — must NOT crash (FK safe)
    resp = await client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Price history row still exists, but invoice_id is now NULL
    await db_session.refresh(ph_rows[0])
    assert ph_rows[0].invoice_id is None


async def test_confirm_duplicate_ingredient_name(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Confirm with create_ingredient_name that already exists (trailing space) → reuse, no crash.

    Regression test for Sprint 43b: UniqueViolationError when create_ingredient_name
    has trailing space and ingredient with same trimmed name already exists.
    """
    from sqlalchemy import select, func

    # Create existing ingredient "Poulycroc"
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Poulycroc",
        unit="piece",
        current_price=5.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Count ingredients before
    count_before = (
        await db_session.execute(
            select(func.count(Ingredient.id)).where(
                Ingredient.restaurant_id == restaurant.id
            )
        )
    ).scalar()

    # Upload
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Confirm with trailing space — should NOT crash
    confirm_resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "Poulycroc casier",
                    "create_ingredient_name": "Poulycroc ",
                    "unit_price": 6.50,
                    "unit": "piece",
                },
            ]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()
    # Should reuse existing, not create new
    assert data["ingredients_created"] == 0

    # Count ingredients after — should be same
    count_after = (
        await db_session.execute(
            select(func.count(Ingredient.id)).where(
                Ingredient.restaurant_id == restaurant.id
            )
        )
    ).scalar()
    assert count_after == count_before

    # Price of existing ingredient should be updated
    await db_session.refresh(ingredient)
    assert ingredient.current_price == 6.50


async def test_patch_invoice_saves_line_edits(client, auth_headers, db_session, restaurant, xml_file_path):
    """PATCH with lines should persist ingredient assignments in JSONB."""
    # Create an ingredient to assign
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Beurre",
        unit="kg",
        current_price=12.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Upload invoice
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]
    num_lines = len(upload_resp.json()["lines"])

    # Build line patches — assign ingredient to first line
    line_patches = [
        {"matched_ingredient_id": ingredient.id, "matched_ingredient_name": "Beurre", "ignored": False}
    ] + [
        {"matched_ingredient_id": None, "matched_ingredient_name": None, "ignored": False}
        for _ in range(num_lines - 1)
    ]

    # PATCH with lines
    resp = await client.patch(
        f"/api/invoices/{invoice_id}",
        json={"lines": line_patches},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["lines"][0]["matched_ingredient_id"] == ingredient.id
    assert resp.json()["lines"][0]["matched_ingredient_name"] == "Beurre"

    # GET the invoice back — assignments should persist
    get_resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["lines"][0]["matched_ingredient_id"] == ingredient.id
    assert get_resp.json()["lines"][0]["matched_ingredient_name"] == "Beurre"


async def test_patch_invoice_saves_ignored_lines(client, auth_headers, xml_file_path):
    """PATCH with ignored=True should persist in JSONB."""
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]
    num_lines = len(upload_resp.json()["lines"])
    assert num_lines > 0

    # Ignore the first line
    line_patches = [
        {"matched_ingredient_id": None, "matched_ingredient_name": None, "ignored": True}
    ] + [
        {"matched_ingredient_id": None, "matched_ingredient_name": None, "ignored": False}
        for _ in range(num_lines - 1)
    ]

    resp = await client.patch(
        f"/api/invoices/{invoice_id}",
        json={"lines": line_patches},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["lines"][0]["ignored"] is True

    # GET back — ignored should persist
    get_resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert get_resp.json()["lines"][0]["ignored"] is True
    # Other lines should not be ignored
    if num_lines > 1:
        assert get_resp.json()["lines"][1]["ignored"] is False


async def test_patch_invoice_preserves_other_fields(client, auth_headers, xml_file_path):
    """PATCH lines should not lose OCR data (description, quantity, price, etc.)."""
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]
    original_lines = upload_resp.json()["lines"]
    num_lines = len(original_lines)
    assert num_lines > 0

    # Note original first line data
    original_first = original_lines[0]

    # PATCH with line edits
    line_patches = [
        {"matched_ingredient_id": 999, "matched_ingredient_name": "Test", "ignored": False}
    ] + [
        {"matched_ingredient_id": None, "matched_ingredient_name": None, "ignored": False}
        for _ in range(num_lines - 1)
    ]

    resp = await client.patch(
        f"/api/invoices/{invoice_id}",
        json={"lines": line_patches},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    patched_first = resp.json()["lines"][0]

    # OCR data preserved
    assert patched_first["description"] == original_first["description"]
    assert patched_first["quantity"] == original_first["quantity"]
    assert patched_first["unit_price"] == original_first["unit_price"]
    assert patched_first["total_price"] == original_first["total_price"]
    # User edit applied
    assert patched_first["matched_ingredient_id"] == 999
    assert patched_first["matched_ingredient_name"] == "Test"


async def test_confirm_saves_assignments_to_jsonb(client, auth_headers, db_session, restaurant, xml_file_path):
    """After confirm, the JSONB should reflect final assignments, not OCR matches."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Saucisse sèche",
        unit="kg",
        current_price=15.0,
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
    num_lines = len(upload_resp.json()["lines"])

    # Confirm: assign ingredient to first line, send all lines
    confirm_lines = [
        {
            "description": upload_resp.json()["lines"][0]["description"],
            "ingredient_id": ingredient.id,
            "unit_price": 15.0,
            "unit": "kg",
            "ignored": False,
        }
    ] + [
        {
            "description": upload_resp.json()["lines"][i]["description"],
            "ingredient_id": None,
            "create_ingredient_name": None,
            "unit_price": None,
            "unit": None,
            "ignored": False,
        }
        for i in range(1, num_lines)
    ]

    resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": confirm_lines},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # GET the invoice — JSONB should reflect the confirmed assignment
    get_resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    first_line = get_resp.json()["lines"][0]
    assert first_line["matched_ingredient_id"] == ingredient.id
    assert first_line["matched_ingredient_name"] == "Saucisse sèche"
    assert first_line["match_confidence"] == "confirmed"


async def test_confirm_saves_ignored_lines_to_jsonb(client, auth_headers, xml_file_path):
    """After confirm, ignored lines should be marked in JSONB."""
    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]
    num_lines = len(upload_resp.json()["lines"])
    assert num_lines >= 2

    # Confirm: first line active (no ingredient), second line ignored
    confirm_lines = [
        {
            "description": upload_resp.json()["lines"][0]["description"],
            "ingredient_id": None,
            "create_ingredient_name": None,
            "unit_price": None,
            "unit": None,
            "ignored": False,
        },
        {
            "description": upload_resp.json()["lines"][1]["description"],
            "ingredient_id": None,
            "create_ingredient_name": None,
            "unit_price": None,
            "unit": None,
            "ignored": True,
        },
    ] + [
        {
            "description": upload_resp.json()["lines"][i]["description"],
            "ingredient_id": None,
            "create_ingredient_name": None,
            "unit_price": None,
            "unit": None,
            "ignored": False,
        }
        for i in range(2, num_lines)
    ]

    resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": confirm_lines},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # GET the invoice — second line should be ignored
    get_resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert get_resp.json()["lines"][0]["ignored"] is False
    assert get_resp.json()["lines"][1]["ignored"] is True


async def test_reopen_confirmed_invoice_shows_saved_data(client, auth_headers, db_session, restaurant, xml_file_path):
    """Opening a confirmed invoice should show the confirmed assignments."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Fromage belge",
        unit="kg",
        current_price=22.0,
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
    original_match_id = upload_resp.json()["lines"][0].get("matched_ingredient_id")
    num_lines = len(upload_resp.json()["lines"])

    # Confirm with custom assignment (different from OCR match)
    confirm_lines = [
        {
            "description": upload_resp.json()["lines"][0]["description"],
            "ingredient_id": ingredient.id,
            "unit_price": 22.0,
            "unit": "kg",
            "ignored": False,
        }
    ] + [
        {
            "description": upload_resp.json()["lines"][i]["description"],
            "ingredient_id": None,
            "create_ingredient_name": None,
            "unit_price": None,
            "unit": None,
            "ignored": False,
        }
        for i in range(1, num_lines)
    ]

    await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={"lines": confirm_lines},
        headers=auth_headers,
    )

    # GET — should show confirmed assignment, not original OCR match
    get_resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    first_line = get_resp.json()["lines"][0]
    assert first_line["matched_ingredient_id"] == ingredient.id
    assert first_line["matched_ingredient_name"] == "Fromage belge"
    # Should NOT be the original OCR match (if it was different)
    if original_match_id is not None and original_match_id != ingredient.id:
        assert first_line["matched_ingredient_id"] != original_match_id


async def test_confirm_saves_recipe_links_in_jsonb(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Confirm should save confirmed_recipe_links in extracted_lines JSONB."""
    from sqlalchemy import select
    from app.models.invoice import Invoice

    ing = Ingredient(restaurant_id=restaurant.id, name="TestIng", unit="kg", current_price=10.0)
    db_session.add(ing)
    await db_session.flush()
    await db_session.refresh(ing)

    recipe = Recipe(restaurant_id=restaurant.id, name="TestRecipe", selling_price=15.0)
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

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
            "lines": [{
                "description": "Test product",
                "ingredient_id": ing.id,
                "unit_price": 12.0,
                "unit": "kg",
                "recipe_links": [{"recipe_id": recipe.id, "quantity": 0.1, "unit": "kg"}],
            }]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200

    # Check JSONB has confirmed_recipe_links via direct DB query
    inv_result = await db_session.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = inv_result.scalar_one()
    found_line = next(
        (ln for ln in inv.extracted_lines if ln.get("matched_ingredient_id") == ing.id),
        None,
    )
    assert found_line is not None
    assert "confirmed_recipe_links" in found_line
    assert len(found_line["confirmed_recipe_links"]) == 1
    assert found_line["confirmed_recipe_links"][0]["recipe_id"] == recipe.id


async def test_confirm_casier_stores_price_per_piece(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Casier 24 bouteilles: confirm with unit=piece → price = total / (qty × 24) per piece."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Jupiler",
        unit="piece",
        current_price=None,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    recipe = Recipe(
        restaurant_id=restaurant.id,
        name="Jupiler 40cL",
        selling_price=2.50,
    )
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=1,
        unit="piece",
    )
    db_session.add(ri)
    await db_session.flush()

    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Frontend sends: unit=piece, unit_price = 26.16 / (2 × 24) = 0.545
    confirm_resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "JUPILER PILS 24/4",
                    "ingredient_id": ingredient.id,
                    "unit_price": 0.545,
                    "unit": "piece",
                },
            ]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200

    await db_session.refresh(ingredient)
    assert ingredient.unit == "piece"
    assert ingredient.current_price == pytest.approx(0.545, abs=0.01)

    # Recipe: 1 piece × 0.545 €/piece = 0.545€ → 21.8%
    await db_session.refresh(recipe)
    assert recipe.food_cost == pytest.approx(0.545, abs=0.01)
    assert recipe.food_cost_percent == pytest.approx(21.8, abs=0.5)


async def test_confirm_fut_stores_price_per_liter(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """Fût 50L: confirm with unit=l → price = total / (qty × volume) per liter."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Stella Artois",
        unit="l",
        current_price=None,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    recipe = Recipe(
        restaurant_id=restaurant.id,
        name="Stella Artois 25cL",
        selling_price=3.00,
    )
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=25,
        unit="cl",
    )
    db_session.add(ri)
    await db_session.flush()

    with open(xml_file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    invoice_id = upload_resp.json()["invoice_id"]

    # Frontend sends: unit=l, unit_price = 914.94 / (6 × 50) = 3.049 €/l
    confirm_resp = await client.post(
        f"/api/invoices/{invoice_id}/confirm",
        json={
            "lines": [
                {
                    "description": "STELLA ARTOIS 50 L",
                    "ingredient_id": ingredient.id,
                    "unit_price": 3.049,
                    "unit": "l",
                },
            ]
        },
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200

    await db_session.refresh(ingredient)
    assert ingredient.unit == "l"
    assert ingredient.current_price == pytest.approx(3.049, abs=0.01)

    # Recipe: convert_quantity(25, "cl", "l") = 0.25 → 0.25 × 3.049 = 0.762€ → 25.4%
    await db_session.refresh(recipe)
    assert recipe.food_cost == pytest.approx(0.762, abs=0.01)
    assert recipe.food_cost_percent == pytest.approx(25.4, abs=0.5)


async def test_patch_saves_draft_recipe_links(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """PATCH saves draft_recipe_links in JSONB and returns them."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id, name="Saucisson", unit="kg", current_price=16.0
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

    # PATCH with draft_recipe_links
    patch_resp = await client.patch(
        f"/api/invoices/{invoice_id}",
        json={
            "lines": [
                {
                    "matched_ingredient_id": ingredient.id,
                    "matched_ingredient_name": "Saucisson",
                    "ignored": False,
                    "draft_recipe_links": [
                        {"recipe_id": 999, "recipe_name": "Portion Saucisson", "quantity": 120, "unit": "g"}
                    ],
                },
            ]
        },
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200

    # Verify draft_recipe_links returned and persisted
    data = patch_resp.json()
    line = data["lines"][0]
    assert line.get("draft_recipe_links") is not None
    assert len(line["draft_recipe_links"]) == 1
    assert line["draft_recipe_links"][0]["recipe_name"] == "Portion Saucisson"

    # GET should also return them
    get_resp = await client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    get_line = get_resp.json()["lines"][0]
    assert get_line.get("draft_recipe_links") is not None
    assert len(get_line["draft_recipe_links"]) == 1


async def test_patch_empty_draft_links_persists(
    client, auth_headers, db_session, restaurant, xml_file_path
):
    """PATCH with empty draft_recipe_links = user removed all links. Must persist as empty list."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id, name="Beurre test", unit="kg", current_price=10.0
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

    # PATCH with EMPTY draft_recipe_links (user removed all links)
    patch_resp = await client.patch(
        f"/api/invoices/{invoice_id}",
        json={
            "lines": [
                {
                    "matched_ingredient_id": ingredient.id,
                    "matched_ingredient_name": "Beurre test",
                    "ignored": False,
                    "draft_recipe_links": [],
                },
            ]
        },
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200

    # Empty list should be persisted (not null)
    data = patch_resp.json()
    assert data["lines"][0].get("draft_recipe_links") == []


async def test_invoices_protected(client):
    """Without auth token → 401."""
    resp = await client.get("/api/invoices")
    assert resp.status_code == 401
