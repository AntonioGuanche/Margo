"""Tests for authentication endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.restaurant import Restaurant
from app.services.auth import create_magic_token


async def test_login_success(client: AsyncClient) -> None:
    """POST /auth/login with valid email returns 200 and message."""
    response = await client.post("/auth/login", json={"email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Lien de connexion envoyé par email"


async def test_login_invalid_email(client: AsyncClient) -> None:
    """POST /auth/login with invalid email returns 422."""
    response = await client.post("/auth/login", json={"email": "pas-un-email"})
    assert response.status_code == 422


async def test_verify_success(client: AsyncClient) -> None:
    """POST /auth/verify with valid magic token returns access_token."""
    token = create_magic_token("chef@restaurant.be")
    response = await client.post("/auth/verify", json={"token": token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Decode the access token to verify payload
    payload = jwt.decode(
        data["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert payload["email"] == "chef@restaurant.be"
    assert "restaurant_id" in payload


async def test_verify_creates_restaurant(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """POST /auth/verify with new email creates a restaurant."""
    email = "nouveau@resto.be"
    token = create_magic_token(email)

    response = await client.post("/auth/verify", json={"token": token})
    assert response.status_code == 200

    # Check restaurant was created in DB
    result = await db_session.execute(
        select(Restaurant).where(Restaurant.owner_email == email)
    )
    restaurant = result.scalar_one_or_none()
    assert restaurant is not None
    assert restaurant.name == "Mon restaurant"
    assert restaurant.owner_email == email


async def test_verify_existing_restaurant(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """POST /auth/verify with existing email reuses the restaurant."""
    email = "existant@resto.be"

    # Create restaurant first
    restaurant = Restaurant(name="Le Moulin", owner_email=email)
    db_session.add(restaurant)
    await db_session.flush()
    original_id = restaurant.id

    # Verify with the same email
    token = create_magic_token(email)
    response = await client.post("/auth/verify", json={"token": token})
    assert response.status_code == 200

    payload = jwt.decode(
        response.json()["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert payload["restaurant_id"] == original_id


async def test_verify_expired_token(client: AsyncClient) -> None:
    """POST /auth/verify with expired token returns 401."""
    payload = {
        "email": "expired@test.com",
        "type": "magic_link",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    response = await client.post("/auth/verify", json={"token": expired_token})
    assert response.status_code == 401
    assert "expiré" in response.json()["detail"].lower()


async def test_verify_invalid_token(client: AsyncClient) -> None:
    """POST /auth/verify with garbage token returns 401."""
    response = await client.post("/auth/verify", json={"token": "not.a.valid.token"})
    assert response.status_code == 401


async def test_verify_wrong_type_token(client: AsyncClient) -> None:
    """POST /auth/verify with access token (wrong type) returns 401."""
    payload = {
        "email": "wrong@type.com",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    wrong_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    response = await client.post("/auth/verify", json={"token": wrong_token})
    assert response.status_code == 401


async def test_login_sends_magic_link_email(client: AsyncClient) -> None:
    """Login endpoint should attempt to send email via Resend."""
    with patch("app.services.email.send_magic_link_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        response = await client.post("/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 200
        assert response.json()["message"] == "Lien de connexion envoyé par email"
        mock_send.assert_called_once()
        # Verify the email and magic link were passed
        call_args = mock_send.call_args
        assert call_args[0][0] == "test@example.com"
        assert "/auth/callback?token=" in call_args[0][1]


async def test_login_succeeds_even_if_email_fails(client: AsyncClient) -> None:
    """Login should still return 200 even if email sending fails."""
    with patch("app.services.email.send_magic_link_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = False
        response = await client.post("/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 200  # Don't expose email failures to user


async def test_send_magic_link_no_api_key(monkeypatch) -> None:
    """Without API key, should fallback to console logging."""
    monkeypatch.setattr("app.services.email.settings.resend_api_key", "")
    from app.services.email import send_magic_link_email
    result = await send_magic_link_email("test@test.com", "https://heymargo.be/auth/callback?token=abc")
    assert result is True  # Returns True (fallback to console)


async def test_health_still_public(client: AsyncClient) -> None:
    """GET /health remains accessible without authentication."""
    response = await client.get("/health")
    assert response.status_code == 200
