"""Tests for restaurant management — list, create sub, switch."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant
from app.services.auth import create_access_token


async def test_list_restaurants_single(
    client: AsyncClient, auth_headers: dict, restaurant: Restaurant,
):
    """Plan free → just 1 restaurant, no subs."""
    resp = await client.get("/api/restaurants", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["main"]["id"] == restaurant.id
    assert data["sub_restaurants"] == []


async def test_create_sub_restaurant_multi(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, restaurant: Restaurant,
):
    """Plan multi → create sub-restaurant OK."""
    restaurant.plan = "multi"
    await db_session.flush()

    resp = await client.post(
        "/api/restaurants",
        json={"name": "Deuxième établissement"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Deuxième établissement"
    assert data["parent_restaurant_id"] == restaurant.id


async def test_create_sub_restaurant_free(
    client: AsyncClient, auth_headers: dict, restaurant: Restaurant,
):
    """Plan free → 403."""
    resp = await client.post(
        "/api/restaurants",
        json={"name": "Impossible"},
        headers=auth_headers,
    )
    assert resp.status_code == 403
    assert "Multi" in resp.json()["detail"]


async def test_switch_restaurant(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, restaurant: Restaurant,
):
    """Switch → new JWT with correct restaurant_id."""
    restaurant.plan = "multi"
    await db_session.flush()

    # Create sub-restaurant via the API (handles unique email)
    create_resp = await client.post(
        "/api/restaurants",
        json={"name": "Sub resto"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    sub_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/restaurants/{sub_id}/switch",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["restaurant_id"] == sub_id
    assert data["restaurant_name"] == "Sub resto"
    assert "access_token" in data
