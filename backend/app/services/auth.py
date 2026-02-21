"""Authentication service — magic link tokens and JWT access tokens."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from app.config import settings


def create_magic_token(email: str) -> str:
    """Generate a short-lived JWT for magic link authentication."""
    payload = {
        "email": email,
        "type": "magic_link",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_expiry_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_magic_token(token: str) -> str:
    """Decode a magic link token and return the email.

    Raises HTTPException 401 if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Lien de connexion expiré",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Lien de connexion invalide",
        )

    if payload.get("type") != "magic_link":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Type de token invalide",
        )

    email: str | None = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide : email manquant",
        )

    return email


def create_access_token(restaurant_id: int, email: str) -> str:
    """Generate a long-lived JWT for API access."""
    payload = {
        "restaurant_id": restaurant_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode an access token and return its payload.

    Raises HTTPException 401 if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée, veuillez vous reconnecter",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'accès invalide",
        )

    return payload
