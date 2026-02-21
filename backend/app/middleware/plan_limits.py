"""Plan limit dependencies — enforce free plan quotas."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.restaurant import Restaurant
from app.services.billing import check_plan_limit


async def require_recipe_quota(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> Restaurant:
    """Verify that the restaurant can create a new recipe."""
    if not await check_plan_limit(db, restaurant, "recipe"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Limite atteinte. Tu as atteint le maximum de 5 recettes "
                "pour le plan gratuit. Passe au plan Pro pour un accès illimité."
            ),
        )
    return restaurant


async def require_invoice_quota(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> Restaurant:
    """Verify that the restaurant can import a new invoice this month."""
    if not await check_plan_limit(db, restaurant, "invoice"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Limite atteinte. Tu as atteint le maximum de 3 factures "
                "ce mois-ci pour le plan gratuit. Passe au plan Pro pour un accès illimité."
            ),
        )
    return restaurant
