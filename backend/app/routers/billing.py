"""Billing routes — plan info, Stripe checkout, customer portal."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.invoice import Invoice
from app.models.recipe import Recipe
from app.models.restaurant import Restaurant
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanInfoResponse,
    PortalResponse,
)
from app.services.billing import (
    PLAN_LIMITS,
    create_checkout_session,
    create_customer_portal_session,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/plan", response_model=PlanInfoResponse)
async def get_plan_info(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> PlanInfoResponse:
    """Return current plan info with usage counters."""
    plan = restaurant.plan or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    # Count recipes
    recipe_count_result = await db.execute(
        select(func.count()).select_from(
            select(Recipe).where(Recipe.restaurant_id == restaurant.id).subquery()
        )
    )
    current_recipes = recipe_count_result.scalar_one()

    # Count invoices this month
    now = datetime.now(timezone.utc)
    invoice_count_result = await db.execute(
        select(func.count()).select_from(
            select(Invoice).where(
                Invoice.restaurant_id == restaurant.id,
                extract("year", Invoice.created_at) == now.year,
                extract("month", Invoice.created_at) == now.month,
            ).subquery()
        )
    )
    current_invoices = invoice_count_result.scalar_one()

    return PlanInfoResponse(
        current_plan=plan,
        max_recipes=limits["max_recipes"],
        max_invoices_per_month=limits["max_invoices_per_month"],
        current_recipes=current_recipes,
        current_invoices_this_month=current_invoices,
        stripe_customer_id=restaurant.stripe_customer_id,
        can_manage_billing=restaurant.stripe_customer_id is not None,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    body: CheckoutRequest,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create a Stripe Checkout session and return the URL."""
    if body.plan not in ("pro", "multi"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan invalide. Choisis 'pro' ou 'multi'.",
        )

    try:
        url = await create_checkout_session(
            restaurant, body.plan, body.success_url, body.cancel_url
        )
    except Exception as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erreur lors de la création de la session de paiement.",
        )

    # Save stripe_customer_id if it was just created
    if not restaurant.stripe_customer_id:
        await db.refresh(restaurant)
    await db.flush()

    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def customer_portal(
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> PortalResponse:
    """Create a Stripe Customer Portal session."""
    if not restaurant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pas d'abonnement actif. Souscris d'abord à un plan.",
        )

    try:
        url = await create_customer_portal_session(
            restaurant, f"{restaurant.owner_email}"
        )
    except Exception as e:
        logger.error("Stripe portal error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erreur lors de la création du portail.",
        )

    return PortalResponse(portal_url=url)
