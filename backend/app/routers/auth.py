"""Authentication routes — magic link login and token verification."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.restaurant import Restaurant
from app.schemas.auth import LoginRequest, LoginResponse, VerifyRequest, VerifyResponse
from app.services.auth import create_access_token, create_magic_token, verify_magic_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Send a magic link to the user's email.

    For now, the link is logged to the console (Resend integration later).
    """
    token = create_magic_token(request.email)
    magic_link = f"{settings.frontend_url}/auth/callback?token={token}"

    # TODO: Replace with Resend email sending (Sprint 5)
    logger.info(f"Magic link for {request.email}: {magic_link}")
    print(f"\n{'='*60}\n  MAGIC LINK: {magic_link}\n{'='*60}\n")

    return LoginResponse(message="Lien de connexion envoyé par email")


@router.post("/verify", response_model=VerifyResponse)
async def verify(request: VerifyRequest, db: AsyncSession = Depends(get_db)) -> VerifyResponse:
    """Verify a magic link token and return an access token.

    If the restaurant does not exist for this email, create one.
    """
    email = verify_magic_token(request.token)

    # Find or create restaurant for this email
    result = await db.execute(select(Restaurant).where(Restaurant.owner_email == email))
    restaurant = result.scalar_one_or_none()

    if restaurant is None:
        restaurant = Restaurant(name="Mon restaurant", owner_email=email)
        db.add(restaurant)
        await db.flush()

    access_token = create_access_token(restaurant.id, email)

    return VerifyResponse(access_token=access_token)
