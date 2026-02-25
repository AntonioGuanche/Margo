"""Tests for billing — plan info, limits, webhooks."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import Recipe, RecipeIngredient
from app.models.ingredient import Ingredient
from app.models.invoice import Invoice
from app.models.restaurant import Restaurant

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def xml_file_path() -> str:
    """Path to the test XML invoice fixture."""
    return str(FIXTURES / "test_invoice.xml")


async def _create_recipe(db: AsyncSession, restaurant_id: int, name: str) -> Recipe:
    """Helper to create a recipe."""
    recipe = Recipe(
        restaurant_id=restaurant_id,
        name=name,
        selling_price=15.0,
        category="Plat",
        food_cost=5.0,
        food_cost_percent=33.3,
    )
    db.add(recipe)
    await db.flush()
    return recipe


async def _create_invoice(db: AsyncSession, restaurant_id: int) -> Invoice:
    """Helper to create a confirmed invoice."""
    invoice = Invoice(
        restaurant_id=restaurant_id,
        source="upload",
        format="xml",
        status="confirmed",
    )
    db.add(invoice)
    await db.flush()
    return invoice


async def test_get_plan_free(client: AsyncClient, auth_headers: dict, restaurant: Restaurant):
    """New restaurant → plan='free', correct limits."""
    resp = await client.get("/api/billing/plan", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_plan"] == "free"
    assert data["max_recipes"] is None  # unlimited during field testing
    assert data["max_invoices_per_month"] is None  # unlimited during field testing
    assert data["current_recipes"] == 0
    assert data["current_invoices_this_month"] == 0
    assert data["can_manage_billing"] is False


@patch("app.services.billing.PLAN_LIMITS", {"free": {"max_recipes": 5, "max_invoices_per_month": 3}, "pro": {"max_recipes": None, "max_invoices_per_month": None}, "multi": {"max_recipes": None, "max_invoices_per_month": None}})
async def test_recipe_limit_free(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, restaurant: Restaurant
):
    """Create 5 recipes OK, 6th → 403 (patched limit=5 for test)."""
    # Create an ingredient first
    ing = Ingredient(restaurant_id=restaurant.id, name="Test", unit="kg")
    db_session.add(ing)
    await db_session.flush()

    # Create 5 recipes (max for free with patched limit)
    for i in range(5):
        await _create_recipe(db_session, restaurant.id, f"Recette {i+1}")
    await db_session.flush()

    # 6th recipe → 403
    resp = await client.post(
        "/api/recipes",
        json={
            "name": "Recette 6",
            "selling_price": 15.0,
            "ingredients": [{"ingredient_id": ing.id, "quantity": 0.1, "unit": "kg"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 403
    assert "Limite" in resp.json()["detail"]


@patch("app.services.billing.PLAN_LIMITS", {"free": {"max_recipes": 5, "max_invoices_per_month": 3}, "pro": {"max_recipes": None, "max_invoices_per_month": None}, "multi": {"max_recipes": None, "max_invoices_per_month": None}})
async def test_invoice_limit_free(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, restaurant: Restaurant,
    xml_file_path: str,
):
    """3 invoices this month OK, 4th → 403 (patched limit=3 for test)."""
    # Create 3 invoices (max for free with patched limit)
    for _ in range(3):
        await _create_invoice(db_session, restaurant.id)
    await db_session.flush()

    # 4th upload → 403
    with open(xml_file_path, "rb") as f:
        resp = await client.post(
            "/api/invoices/upload",
            files={"file": ("test.xml", f, "application/xml")},
            headers=auth_headers,
        )
    assert resp.status_code == 403
    assert "Limite" in resp.json()["detail"]


async def test_no_limit_pro(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, restaurant: Restaurant,
):
    """Pro plan → no recipe limit."""
    restaurant.plan = "pro"
    await db_session.flush()

    ing = Ingredient(restaurant_id=restaurant.id, name="Test", unit="kg")
    db_session.add(ing)
    await db_session.flush()

    # Create 6 recipes — should all work
    for i in range(6):
        await _create_recipe(db_session, restaurant.id, f"Recette {i+1}")
    await db_session.flush()

    # 7th should still work
    resp = await client.post(
        "/api/recipes",
        json={
            "name": "Recette 7",
            "selling_price": 15.0,
            "ingredients": [{"ingredient_id": ing.id, "quantity": 0.1, "unit": "kg"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201


@patch("app.routers.billing.create_checkout_session")
async def test_checkout_creates_session(
    mock_checkout, client: AsyncClient, auth_headers: dict, restaurant: Restaurant,
):
    """POST /billing/checkout → returns URL (mock Stripe)."""
    mock_checkout.return_value = "https://checkout.stripe.com/test_session_123"

    resp = await client.post(
        "/api/billing/checkout",
        json={
            "plan": "pro",
            "success_url": "https://heymargo.be/settings",
            "cancel_url": "https://heymargo.be/pricing",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/test_session_123"


@patch("app.services.billing.stripe")
async def test_webhook_activates_plan(
    mock_stripe,
    client: AsyncClient,
    db_session: AsyncSession,
    restaurant: Restaurant,
):
    """Simulate checkout.session.completed webhook → plan activated."""
    # Set restaurant plan to free
    restaurant.plan = "free"
    await db_session.flush()

    event_data = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "restaurant_id": str(restaurant.id),
                    "plan": "pro",
                },
                "customer": "cus_test_123",
                "subscription": "sub_test_456",
            }
        },
    }

    mock_stripe.Webhook.construct_event.return_value = event_data

    resp = await client.post(
        "/webhooks/stripe",
        content=json.dumps(event_data),
        headers={
            "stripe-signature": "test_sig",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200

    # Verify plan updated
    await db_session.refresh(restaurant)
    assert restaurant.plan == "pro"
    assert restaurant.stripe_customer_id == "cus_test_123"
    assert restaurant.stripe_subscription_id == "sub_test_456"


@patch("app.services.billing.stripe")
async def test_webhook_cancels_plan(
    mock_stripe,
    client: AsyncClient,
    db_session: AsyncSession,
    restaurant: Restaurant,
):
    """Simulate subscription.deleted webhook → plan reverts to free."""
    restaurant.plan = "pro"
    restaurant.stripe_subscription_id = "sub_test_456"
    await db_session.flush()

    event_data = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test_456",
            }
        },
    }

    mock_stripe.Webhook.construct_event.return_value = event_data

    resp = await client.post(
        "/webhooks/stripe",
        content=json.dumps(event_data),
        headers={
            "stripe-signature": "test_sig",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200

    await db_session.refresh(restaurant)
    assert restaurant.plan == "free"
    assert restaurant.stripe_subscription_id is None


async def test_plan_info_with_counts(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, restaurant: Restaurant,
):
    """GET /billing/plan → correct counters."""
    # Create 2 recipes and 1 invoice
    for i in range(2):
        await _create_recipe(db_session, restaurant.id, f"Recette {i+1}")
    await _create_invoice(db_session, restaurant.id)
    await db_session.flush()

    resp = await client.get("/api/billing/plan", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_recipes"] == 2
    assert data["current_invoices_this_month"] == 1
