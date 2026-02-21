"""Shared FastAPI dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.restaurant import Restaurant
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_restaurant(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Restaurant:
    """FastAPI dependency that extracts and validates the JWT from the Authorization header.

    Returns the Restaurant object for the authenticated user.
    Raises 401 if the token is invalid or the restaurant is not found.
    """
    payload = decode_access_token(token)

    restaurant_id: int | None = payload.get("restaurant_id")
    if restaurant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide : restaurant_id manquant",
        )

    restaurant = await db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Restaurant introuvable",
        )

    return restaurant
