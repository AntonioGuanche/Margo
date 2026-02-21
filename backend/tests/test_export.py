"""Tests for CSV export endpoints."""

import datetime as dt

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.recipe import Recipe
from app.models.restaurant import Restaurant


async def test_export_invoices_csv(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, restaurant: Restaurant,
):
    """GET /api/export/invoices with dates → CSV with correct columns."""
    # Create a confirmed invoice
    inv = Invoice(
        restaurant_id=restaurant.id,
        source="upload",
        format="xml",
        status="confirmed",
        supplier_name="Metro",
        total_amount=250.50,
        invoice_date=dt.date(2025, 2, 1),
    )
    db_session.add(inv)
    await db_session.flush()

    resp = await client.get(
        "/api/export/invoices?from_date=2025-01-01&to_date=2025-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")

    content = resp.text
    lines = content.strip().split("\n")
    assert len(lines) == 2  # header + 1 row
    assert "Fournisseur" in lines[0]
    assert "Metro" in lines[1]


async def test_export_invoices_empty(
    client: AsyncClient, auth_headers: dict, restaurant: Restaurant,
):
    """No invoices in period → CSV with just the header."""
    resp = await client.get(
        "/api/export/invoices?from_date=2030-01-01&to_date=2030-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    content = resp.text
    lines = content.strip().split("\n")
    assert len(lines) == 1  # header only


async def test_export_food_costs_csv(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, restaurant: Restaurant,
):
    """GET /api/export/food-costs → CSV with all recipes."""
    recipe = Recipe(
        restaurant_id=restaurant.id,
        name="Moules-frites",
        selling_price=18.0,
        category="Plat",
        food_cost=5.40,
        food_cost_percent=30.0,
    )
    db_session.add(recipe)
    await db_session.flush()

    resp = await client.get("/api/export/food-costs", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    content = resp.text
    lines = content.strip().split("\n")
    assert len(lines) == 2  # header + 1 row
    assert "Moules-frites" in lines[1]
    assert "30.0" in lines[1]


async def test_export_protected(client: AsyncClient):
    """Without auth token → 401."""
    resp = await client.get("/api/export/invoices")
    assert resp.status_code == 401
