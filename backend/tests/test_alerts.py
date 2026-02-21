"""Tests for alert system."""

from pathlib import Path

import pytest

from app.models.alert import Alert
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, RecipeIngredient


FIXTURES = Path(__file__).parent / "fixtures"


async def test_alert_on_price_increase_small(
    client, db_session, restaurant, auth_headers
):
    """8% price increase → warning alert."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Boeuf haché",
        unit="kg",
        current_price=10.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Upload and confirm invoice with higher price
    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
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
                    "description": "Boeuf haché",
                    "ingredient_id": ingredient.id,
                    "unit_price": 10.80,  # 8% increase
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )

    # Check alerts
    resp = await client.get("/api/alerts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    price_alerts = [a for a in data["items"] if a["alert_type"] == "price_increase"]
    assert len(price_alerts) == 1
    assert price_alerts[0]["severity"] == "warning"
    assert "8%" in price_alerts[0]["message"]


async def test_alert_on_price_increase_large(
    client, db_session, restaurant, auth_headers
):
    """20% price increase → critical alert."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Saumon frais",
        unit="kg",
        current_price=20.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
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
                    "description": "Saumon frais",
                    "ingredient_id": ingredient.id,
                    "unit_price": 24.0,  # 20% increase
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )

    resp = await client.get("/api/alerts", headers=auth_headers)
    data = resp.json()
    price_alerts = [a for a in data["items"] if a["alert_type"] == "price_increase"]
    assert len(price_alerts) == 1
    assert price_alerts[0]["severity"] == "critical"


async def test_alert_on_margin_exceeded(
    client, db_session, restaurant, auth_headers
):
    """Recipe crosses threshold after price increase → margin alert."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Poulet",
        unit="kg",
        current_price=8.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    # Create recipe with tight margin: food cost = 8*0.5 = 4€, selling = 10€ → 40% → already red
    recipe = Recipe(
        restaurant_id=restaurant.id,
        name="Poulet grillé",
        selling_price=10.0,
        food_cost=4.0,
        food_cost_percent=40.0,
    )
    db_session.add(recipe)
    await db_session.flush()
    await db_session.refresh(recipe)

    ri = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=0.5,
        unit="kg",
    )
    db_session.add(ri)
    await db_session.flush()

    # Increase price significantly
    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
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
                    "description": "Poulet",
                    "ingredient_id": ingredient.id,
                    "unit_price": 10.0,  # 25% increase → food cost goes up
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )

    resp = await client.get("/api/alerts", headers=auth_headers)
    data = resp.json()
    margin_alerts = [a for a in data["items"] if a["alert_type"] == "margin_exceeded"]
    assert len(margin_alerts) >= 1
    assert "Poulet grillé" in margin_alerts[0]["message"]


async def test_no_alert_on_small_change(
    client, db_session, restaurant, auth_headers
):
    """3% price increase → no alert."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Oignon",
        unit="kg",
        current_price=2.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
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
                    "description": "Oignon",
                    "ingredient_id": ingredient.id,
                    "unit_price": 2.06,  # 3% increase
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )

    resp = await client.get("/api/alerts", headers=auth_headers)
    data = resp.json()
    price_alerts = [a for a in data["items"] if a["alert_type"] == "price_increase"]
    assert len(price_alerts) == 0


async def test_no_alert_on_price_decrease(
    client, db_session, restaurant, auth_headers
):
    """Price decrease → no alert."""
    ingredient = Ingredient(
        restaurant_id=restaurant.id,
        name="Carotte",
        unit="kg",
        current_price=3.0,
    )
    db_session.add(ingredient)
    await db_session.flush()
    await db_session.refresh(ingredient)

    xml_path = FIXTURES / "test_invoice.xml"
    with open(xml_path, "rb") as f:
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
                    "description": "Carotte",
                    "ingredient_id": ingredient.id,
                    "unit_price": 2.5,  # price decrease
                    "unit": "kg",
                },
            ]
        },
        headers=auth_headers,
    )

    resp = await client.get("/api/alerts", headers=auth_headers)
    data = resp.json()
    price_alerts = [a for a in data["items"] if a["alert_type"] == "price_increase"]
    assert len(price_alerts) == 0


async def test_list_alerts(client, db_session, restaurant, auth_headers):
    """Create multiple alerts → GET returns all."""
    for i, (msg, severity) in enumerate([
        ("Alert 1", "warning"),
        ("Alert 2", "critical"),
        ("Alert 3", "warning"),
    ]):
        alert = Alert(
            restaurant_id=restaurant.id,
            alert_type="price_increase",
            severity=severity,
            message=msg,
        )
        db_session.add(alert)
    await db_session.flush()

    resp = await client.get("/api/alerts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["unread_count"] == 3
    assert len(data["items"]) == 3


async def test_mark_alert_read(client, db_session, restaurant, auth_headers):
    """PUT /alerts/{id}/read → is_read=true."""
    alert = Alert(
        restaurant_id=restaurant.id,
        alert_type="price_increase",
        severity="warning",
        message="Test alert",
    )
    db_session.add(alert)
    await db_session.flush()
    await db_session.refresh(alert)

    # Mark as read
    resp = await client.put(
        f"/api/alerts/{alert.id}/read", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify
    resp = await client.get("/api/alerts", headers=auth_headers)
    data = resp.json()
    assert data["items"][0]["is_read"] is True
    assert data["unread_count"] == 0


async def test_alert_count(client, db_session, restaurant, auth_headers):
    """GET /alerts/count → correct unread_count."""
    for i in range(5):
        alert = Alert(
            restaurant_id=restaurant.id,
            alert_type="price_increase",
            severity="warning",
            message=f"Alert {i}",
            is_read=(i < 2),  # First 2 are read
        )
        db_session.add(alert)
    await db_session.flush()

    resp = await client.get("/api/alerts/count", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["unread_count"] == 3  # 5 total - 2 read = 3 unread
