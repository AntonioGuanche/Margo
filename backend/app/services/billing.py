"""Stripe billing service — checkout, portal, webhooks, plan limits."""

import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.invoice import Invoice
from app.models.recipe import Recipe
from app.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key

PLAN_LIMITS: dict[str, dict[str, int | None]] = {
    "free": {"max_recipes": None, "max_invoices_per_month": None},  # TODO: revert to 5/3 after field testing
    "pro": {"max_recipes": None, "max_invoices_per_month": None},
    "multi": {"max_recipes": None, "max_invoices_per_month": None},
}

PRICE_MAP: dict[str, str] = {
    "pro": settings.stripe_price_pro,
    "multi": settings.stripe_price_multi,
}


async def create_checkout_session(
    restaurant: Restaurant,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session for upgrading to Pro or Multi.

    Returns the checkout URL.
    """
    price_id = PRICE_MAP.get(plan)
    if not price_id:
        raise ValueError(f"Plan invalide : {plan}")

    # Create Stripe customer if needed
    customer_id = restaurant.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=restaurant.owner_email,
            name=restaurant.name,
            metadata={"restaurant_id": str(restaurant.id)},
        )
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"restaurant_id": str(restaurant.id), "plan": plan},
    )

    return session.url


async def create_customer_portal_session(
    restaurant: Restaurant,
    return_url: str,
) -> str:
    """Create a Stripe Customer Portal session for managing the subscription."""
    if not restaurant.stripe_customer_id:
        raise ValueError("Pas de compte Stripe associé.")

    session = stripe.billing_portal.Session.create(
        customer=restaurant.stripe_customer_id,
        return_url=return_url,
    )

    return session.url


async def handle_webhook_event(
    db: AsyncSession,
    payload: bytes,
    sig_header: str,
) -> None:
    """Process Stripe webhook events.

    Handles:
    - checkout.session.completed → activate plan
    - customer.subscription.updated → update plan if changed
    - customer.subscription.deleted → revert to free
    - invoice.payment_failed → log warning
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise ValueError("Signature Stripe invalide")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        restaurant_id = int(data["metadata"].get("restaurant_id", 0))
        plan = data["metadata"].get("plan", "pro")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")

        if restaurant_id:
            restaurant = await db.get(Restaurant, restaurant_id)
            if restaurant:
                restaurant.plan = plan
                restaurant.stripe_customer_id = customer_id
                restaurant.stripe_subscription_id = subscription_id
                await db.flush()
                logger.info(
                    "Plan activated: restaurant=%d plan=%s",
                    restaurant_id, plan,
                )

    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")
        if subscription_id:
            result = await db.execute(
                select(Restaurant).where(
                    Restaurant.stripe_subscription_id == subscription_id
                )
            )
            restaurant = result.scalar_one_or_none()
            if restaurant:
                # Check if the price changed → update plan
                items = data.get("items", {}).get("data", [])
                if items:
                    price_id = items[0].get("price", {}).get("id", "")
                    if price_id == settings.stripe_price_multi:
                        restaurant.plan = "multi"
                    elif price_id == settings.stripe_price_pro:
                        restaurant.plan = "pro"
                    await db.flush()
                    logger.info(
                        "Subscription updated: restaurant=%d plan=%s",
                        restaurant.id, restaurant.plan,
                    )

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            result = await db.execute(
                select(Restaurant).where(
                    Restaurant.stripe_subscription_id == subscription_id
                )
            )
            restaurant = result.scalar_one_or_none()
            if restaurant:
                restaurant.plan = "free"
                restaurant.stripe_subscription_id = None
                await db.flush()
                logger.info(
                    "Subscription cancelled: restaurant=%d → free",
                    restaurant.id,
                )

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        logger.warning("Payment failed for customer=%s", customer_id)


async def check_plan_limit(
    db: AsyncSession,
    restaurant: Restaurant,
    resource: str,
) -> bool:
    """Check if the restaurant can still create a resource.

    resource = "recipe" or "invoice"
    Returns True if OK, False if limit reached.
    """
    plan = restaurant.plan or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    if resource == "recipe":
        max_recipes = limits["max_recipes"]
        if max_recipes is None:
            return True
        count_result = await db.execute(
            select(func.count()).select_from(
                select(Recipe).where(
                    Recipe.restaurant_id == restaurant.id
                ).subquery()
            )
        )
        current = count_result.scalar_one()
        return current < max_recipes

    elif resource == "invoice":
        max_invoices = limits["max_invoices_per_month"]
        if max_invoices is None:
            return True
        now = datetime.now(timezone.utc)
        count_result = await db.execute(
            select(func.count()).select_from(
                select(Invoice).where(
                    Invoice.restaurant_id == restaurant.id,
                    extract("year", Invoice.created_at) == now.year,
                    extract("month", Invoice.created_at) == now.month,
                ).subquery()
            )
        )
        current = count_result.scalar_one()
        return current < max_invoices

    return True
