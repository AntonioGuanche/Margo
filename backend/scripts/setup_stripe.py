"""Create Stripe products and prices for Margó plans.

Usage:
    python -m scripts.setup_stripe

Creates:
    - Margó Pro: 14.90€/month recurring
    - Margó Multi: 24.90€/month recurring

Prints the price IDs to copy into .env.
"""

import stripe

from app.config import settings

stripe.api_key = settings.stripe_secret_key


def setup() -> None:
    """Create Stripe products and prices."""
    if not stripe.api_key:
        print("❌ STRIPE_SECRET_KEY not set in .env")
        return

    print("🔧 Creating Stripe products and prices...\n")

    # --- Margó Pro ---
    pro_product = stripe.Product.create(
        name="Margó Pro",
        description="Recettes et factures illimitées, alertes email, export CSV.",
        metadata={"plan": "pro"},
    )
    pro_price = stripe.Price.create(
        product=pro_product.id,
        unit_amount=1490,  # 14.90€ in cents
        currency="eur",
        recurring={"interval": "month"},
        metadata={"plan": "pro"},
    )
    print(f"✅ Margó Pro")
    print(f"   Product ID: {pro_product.id}")
    print(f"   Price ID:   {pro_price.id}")
    print()

    # --- Margó Multi ---
    multi_product = stripe.Product.create(
        name="Margó Multi",
        description="Tout Pro + jusqu'à 5 établissements, dashboard consolidé.",
        metadata={"plan": "multi"},
    )
    multi_price = stripe.Price.create(
        product=multi_product.id,
        unit_amount=2490,  # 24.90€ in cents
        currency="eur",
        recurring={"interval": "month"},
        metadata={"plan": "multi"},
    )
    print(f"✅ Margó Multi")
    print(f"   Product ID: {multi_product.id}")
    print(f"   Price ID:   {multi_price.id}")
    print()

    print("=" * 60)
    print("📋 Copie ces lignes dans ton .env :")
    print()
    print(f"STRIPE_PRICE_PRO={pro_price.id}")
    print(f"STRIPE_PRICE_MULTI={multi_price.id}")
    print("=" * 60)


if __name__ == "__main__":
    setup()
