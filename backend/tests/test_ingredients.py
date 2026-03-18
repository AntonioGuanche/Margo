"""Tests for ingredients CRUD endpoints."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient
from app.models.restaurant import Restaurant
from app.services.auth import create_access_token


# --- CREATE ---


async def test_create_ingredient(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """POST /api/ingredients with valid data returns 201."""
    response = await client.post(
        "/api/ingredients",
        json={"name": "Beurre", "unit": "kg"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Beurre"
    assert data["unit"] == "kg"
    assert data["current_price"] is None
    assert data["supplier_name"] is None
    assert data["last_updated"] is None
    assert "id" in data
    assert "created_at" in data


async def test_create_ingredient_with_price(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """POST with current_price sets last_updated."""
    response = await client.post(
        "/api/ingredients",
        json={"name": "Saumon", "unit": "kg", "current_price": 18.50, "supplier_name": "Metro"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["current_price"] == 18.50
    assert data["supplier_name"] == "Metro"
    assert data["last_updated"] is not None


async def test_create_ingredient_duplicate(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """POST with duplicate name for same restaurant returns 409."""
    payload = {"name": "Farine", "unit": "kg"}
    response1 = await client.post("/api/ingredients", json=payload, headers=auth_headers)
    assert response1.status_code == 201

    response2 = await client.post("/api/ingredients", json=payload, headers=auth_headers)
    assert response2.status_code == 409
    assert "existe déjà" in response2.json()["detail"].lower()


async def test_create_ingredient_invalid_unit(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """POST with invalid unit returns 422."""
    response = await client.post(
        "/api/ingredients",
        json={"name": "Sel", "unit": "xyz"},
        headers=auth_headers,
    )
    assert response.status_code == 422


# --- LIST ---


async def test_list_ingredients(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """GET returns all ingredients for the restaurant."""
    for name in ["Ail", "Basilic", "Citron"]:
        await client.post(
            "/api/ingredients",
            json={"name": name, "unit": "piece"},
            headers=auth_headers,
        )

    response = await client.get("/api/ingredients", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    # Sorted alphabetically
    names = [item["name"] for item in data["items"]]
    assert names == sorted(names)


async def test_list_ingredients_search(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """GET with search filters by name (case-insensitive)."""
    for name in ["Beurre", "Bière", "Saumon"]:
        await client.post(
            "/api/ingredients",
            json={"name": name, "unit": "kg"},
            headers=auth_headers,
        )

    response = await client.get("/api/ingredients?search=beu", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Beurre"


async def test_list_ingredients_pagination(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """GET with skip/limit paginates correctly."""
    for i in range(5):
        await client.post(
            "/api/ingredients",
            json={"name": f"Ingredient {i:02d}", "unit": "g"},
            headers=auth_headers,
        )

    response = await client.get("/api/ingredients?skip=2&limit=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


# --- GET BY ID ---


async def test_get_ingredient(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """GET /api/ingredients/{id} returns the ingredient."""
    create_resp = await client.post(
        "/api/ingredients",
        json={"name": "Poivre", "unit": "g"},
        headers=auth_headers,
    )
    ingredient_id = create_resp.json()["id"]

    response = await client.get(f"/api/ingredients/{ingredient_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Poivre"


async def test_get_ingredient_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """GET with non-existent ID returns 404."""
    response = await client.get("/api/ingredients/99999", headers=auth_headers)
    assert response.status_code == 404


# --- UPDATE ---


async def test_update_ingredient(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """PUT updates the ingredient name."""
    create_resp = await client.post(
        "/api/ingredients",
        json={"name": "Huile olive", "unit": "l"},
        headers=auth_headers,
    )
    ingredient_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/ingredients/{ingredient_id}",
        json={"name": "Huile d'olive extra vierge"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Huile d'olive extra vierge"
    assert response.json()["unit"] == "l"  # unchanged


async def test_update_ingredient_price(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """PUT with new price updates last_updated."""
    create_resp = await client.post(
        "/api/ingredients",
        json={"name": "Lait", "unit": "l"},
        headers=auth_headers,
    )
    ingredient_id = create_resp.json()["id"]
    assert create_resp.json()["last_updated"] is None

    response = await client.put(
        f"/api/ingredients/{ingredient_id}",
        json={"current_price": 1.20},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["current_price"] == 1.20
    assert response.json()["last_updated"] is not None


# --- DELETE ---


async def test_delete_ingredient(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """DELETE removes the ingredient, subsequent GET returns 404."""
    create_resp = await client.post(
        "/api/ingredients",
        json={"name": "Persil", "unit": "piece"},
        headers=auth_headers,
    )
    ingredient_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/ingredients/{ingredient_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/ingredients/{ingredient_id}", headers=auth_headers)
    assert get_resp.status_code == 404


# --- AUTH / ISOLATION ---


async def test_no_token(client: AsyncClient) -> None:
    """GET /api/ingredients without Authorization header returns 401."""
    response = await client.get("/api/ingredients")
    assert response.status_code == 401


async def test_cross_restaurant_isolation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    restaurant: Restaurant,
    db_session: AsyncSession,
) -> None:
    """Restaurant A cannot see ingredients of restaurant B."""
    # Create ingredient with restaurant A (via auth_headers)
    create_resp = await client.post(
        "/api/ingredients",
        json={"name": "Secret Sauce", "unit": "l"},
        headers=auth_headers,
    )
    ingredient_id = create_resp.json()["id"]

    # Create restaurant B
    resto_b = Restaurant(name="Autre Resto", owner_email="autre@resto.be")
    db_session.add(resto_b)
    await db_session.flush()
    await db_session.refresh(resto_b)

    # JWT for restaurant B
    token_b = create_access_token(resto_b.id, resto_b.owner_email)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Restaurant B cannot GET restaurant A's ingredient
    response = await client.get(f"/api/ingredients/{ingredient_id}", headers=headers_b)
    assert response.status_code == 404

    # Restaurant B cannot see it in list either
    list_resp = await client.get("/api/ingredients", headers=headers_b)
    assert list_resp.json()["total"] == 0


# --- INGREDIENT RECIPES ---


async def test_get_ingredient_recipes(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    restaurant: Restaurant,
) -> None:
    """GET /api/ingredients/{id}/recipes returns recipes using this ingredient."""
    # Create ingredient
    ingredient = Ingredient(
        restaurant_id=restaurant.id, name="Boeuf haché", unit="kg", current_price=12.0
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Create two recipes that use the ingredient
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

    ri1 = RecipeIngredient(
        recipe_id=recipe1.id, ingredient_id=ingredient.id, quantity=0.15, unit="kg"
    )
    ri2 = RecipeIngredient(
        recipe_id=recipe2.id, ingredient_id=ingredient.id, quantity=0.12, unit="kg"
    )
    db_session.add_all([ri1, ri2])
    await db_session.flush()

    # Query the endpoint
    resp = await client.get(
        f"/api/ingredients/{ingredient.id}/recipes", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    names = {item["recipe_name"] for item in data["items"]}
    assert names == {"Spaghetti Bolo", "Lasagne"}


async def test_get_ingredient_recipes_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    restaurant: Restaurant,
) -> None:
    """GET /api/ingredients/{id}/recipes returns empty if no recipes use it."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id, name="Sel", unit="kg", current_price=1.0
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    resp = await client.get(
        f"/api/ingredients/{ingredient.id}/recipes", headers=auth_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0


# --- BATCH RECIPES ---


async def test_recipes_batch(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    restaurant: Restaurant,
) -> None:
    """POST /api/ingredients/recipes-batch returns recipes grouped by ingredient."""
    # Create 2 ingredients
    ing1 = Ingredient(restaurant_id=restaurant.id, name="Boeuf", unit="kg", current_price=12.0)
    ing2 = Ingredient(restaurant_id=restaurant.id, name="Poulet", unit="kg", current_price=8.0)
    db_session.add_all([ing1, ing2])
    await db_session.flush()
    await db_session.refresh(ing1)
    await db_session.refresh(ing2)

    # Create recipe linked to ing1 only
    recipe = Recipe(restaurant_id=restaurant.id, name="Steak Frites", selling_price=18.0)
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    ri = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing1.id, quantity=0.2, unit="kg")
    db_session.add(ri)
    await db_session.flush()

    resp = await client.post(
        "/api/ingredients/recipes-batch",
        json={"ingredient_ids": [ing1.id, ing2.id]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # ing1 has 1 recipe, ing2 has 0
    assert len(data["results"][str(ing1.id)]) == 1
    assert data["results"][str(ing1.id)][0]["recipe_name"] == "Steak Frites"
    assert len(data["results"][str(ing2.id)]) == 0


async def test_recipes_batch_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /api/ingredients/recipes-batch with empty list returns empty."""
    resp = await client.post(
        "/api/ingredients/recipes-batch",
        json={"ingredient_ids": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["results"] == {}


async def test_delete_ingredient_with_recipes(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    restaurant: Restaurant,
) -> None:
    """DELETE /api/ingredients/{id} cascades to recipe_ingredients and recalculates food cost.

    Regression test for Sprint 40: previously returned 409 when ingredient was used
    in a recipe. Now it should silently remove the recipe_ingredient links and
    recalculate food cost for affected recipes.
    """
    from sqlalchemy import select

    # Create ingredient
    ing = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf cascade test",
        unit="kg",
        current_price=15.0,
    )
    db_session.add(ing)
    await db_session.flush()
    await db_session.refresh(ing)

    # Create recipe using that ingredient
    recipe = Recipe(
        restaurant_id=restaurant.id,
        name="Steak test cascade",
        selling_price=20.0,
        is_homemade=True,
    )
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    ri = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id, quantity=0.2, unit="kg")
    db_session.add(ri)
    await db_session.flush()

    # Delete ingredient — should succeed (no 409)
    resp = await client.delete(f"/api/ingredients/{ing.id}", headers=auth_headers)
    assert resp.status_code == 204

    # Ingredient is gone
    ing_check = await db_session.execute(
        select(Ingredient).where(Ingredient.id == ing.id)
    )
    assert ing_check.scalar_one_or_none() is None

    # recipe_ingredient link is gone
    ri_check = await db_session.execute(
        select(RecipeIngredient).where(RecipeIngredient.ingredient_id == ing.id)
    )
    assert ri_check.scalar_one_or_none() is None

    # Recipe still exists
    recipe_check = await db_session.execute(
        select(Recipe).where(Recipe.id == recipe.id)
    )
    recipe_row = recipe_check.scalar_one_or_none()
    assert recipe_row is not None
    # food_cost recalculated — no ingredients left, so 0.0 or None
    assert recipe_row.food_cost is None or recipe_row.food_cost == 0.0


# --- LAST CONFIRMED LINKS ---


async def test_last_confirmed_links_returns_saved_choices(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    restaurant: Restaurant,
) -> None:
    """After confirming with specific recipe links, last-confirmed-links returns those."""
    from pathlib import Path

    xml_file_path = str(Path(__file__).parent / "fixtures" / "test_invoice.xml")

    ing = Ingredient(restaurant_id=restaurant.id, name="IngX", unit="kg", current_price=10.0)
    db_session.add(ing)
    await db_session.flush()
    await db_session.refresh(ing)

    recipe_a = Recipe(restaurant_id=restaurant.id, name="RecipeA", selling_price=15.0)
    recipe_b = Recipe(restaurant_id=restaurant.id, name="RecipeB", selling_price=18.0)
    db_session.add_all([recipe_a, recipe_b])
    await db_session.flush()
    await db_session.refresh(recipe_a)
    await db_session.refresh(recipe_b)

    # Link both recipes to ingredient
    db_session.add(RecipeIngredient(recipe_id=recipe_a.id, ingredient_id=ing.id, quantity=0.1, unit="kg"))
    db_session.add(RecipeIngredient(recipe_id=recipe_b.id, ingredient_id=ing.id, quantity=0.2, unit="kg"))
    await db_session.flush()

    # Upload + confirm with ONLY recipe_a (not recipe_b)
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
            "lines": [{
                "description": "Test",
                "ingredient_id": ing.id,
                "unit_price": 12.0,
                "unit": "kg",
                "recipe_links": [{"recipe_id": recipe_a.id, "quantity": 0.1, "unit": "kg"}],
            }]
        },
        headers=auth_headers,
    )

    # Call last-confirmed-links
    resp = await client.post(
        "/api/ingredients/last-confirmed-links",
        json={"ingredient_ids": [ing.id]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    links = data["results"][str(ing.id)]
    assert len(links) == 1
    assert links[0]["recipe_id"] == recipe_a.id
    assert links[0]["recipe_name"] == "RecipeA"


async def test_last_confirmed_links_no_history(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    restaurant: Restaurant,
) -> None:
    """Ingredient with no confirmed invoice returns empty list."""
    ing = Ingredient(restaurant_id=restaurant.id, name="NewIng", unit="kg")
    db_session.add(ing)
    await db_session.flush()
    await db_session.refresh(ing)

    resp = await client.post(
        "/api/ingredients/last-confirmed-links",
        json={"ingredient_ids": [ing.id]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][str(ing.id)] == []


async def test_last_confirmed_links_deleted_recipe(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    restaurant: Restaurant,
) -> None:
    """If a saved recipe was deleted, it should be silently skipped."""
    from pathlib import Path

    xml_file_path = str(Path(__file__).parent / "fixtures" / "test_invoice.xml")

    ing = Ingredient(restaurant_id=restaurant.id, name="IngDel", unit="kg", current_price=10.0)
    db_session.add(ing)
    await db_session.flush()
    await db_session.refresh(ing)

    recipe = Recipe(restaurant_id=restaurant.id, name="WillDelete", selling_price=15.0)
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)
    recipe_id = recipe.id

    # Confirm invoice with this recipe
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
            "lines": [{
                "description": "Test",
                "ingredient_id": ing.id,
                "unit_price": 12.0,
                "unit": "kg",
                "recipe_links": [{"recipe_id": recipe_id, "quantity": 0.1, "unit": "kg"}],
            }]
        },
        headers=auth_headers,
    )

    # Delete the recipe
    await client.delete(f"/api/recipes/{recipe_id}", headers=auth_headers)

    # Call last-confirmed-links — deleted recipe should be skipped
    resp = await client.post(
        "/api/ingredients/last-confirmed-links",
        json={"ingredient_ids": [ing.id]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][str(ing.id)] == []
