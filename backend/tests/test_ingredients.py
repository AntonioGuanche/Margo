"""Tests for ingredients CRUD endpoints."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingredient import Ingredient
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
