"""Alert generation service — creates alerts on price changes and margin breaches."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.recipe import Recipe, RecipeIngredient
from app.services.costing import get_margin_status

logger = logging.getLogger(__name__)

# Alert thresholds
PRICE_INCREASE_THRESHOLD = 5.0  # minimum % increase to trigger alert
PRICE_INCREASE_CRITICAL = 15.0  # % increase for critical severity


async def check_and_create_alerts(
    db: AsyncSession,
    restaurant_id: int,
    ingredient_id: int,
    old_price: float | None,
    new_price: float,
    invoice_id: int | None = None,
) -> list[Alert]:
    """Generate alerts after an ingredient price update.

    Called after invoice confirmation. Creates alerts if:
    1. Price increase > 5% → warning (5-15%) or critical (>15%)
    2. Any recipe crosses its margin threshold → warning/critical
    """
    alerts: list[Alert] = []

    # No alert if ingredient had no previous price (first price)
    if old_price is None or old_price <= 0:
        return alerts

    # No alert on price decrease
    if new_price <= old_price:
        return alerts

    percent_change = ((new_price - old_price) / old_price) * 100

    # 1. Price increase alert
    if percent_change > PRICE_INCREASE_THRESHOLD:
        # Get ingredient name
        from app.models.ingredient import Ingredient

        ing_result = await db.execute(
            select(Ingredient).where(Ingredient.id == ingredient_id)
        )
        ingredient = ing_result.scalar_one_or_none()
        ingredient_name = ingredient.name if ingredient else f"Ingrédient #{ingredient_id}"

        severity = "critical" if percent_change > PRICE_INCREASE_CRITICAL else "warning"
        message = (
            f"{ingredient_name} a augmenté de {percent_change:.0f}% "
            f"({old_price:.2f}€ → {new_price:.2f}€)"
        )

        alert = Alert(
            restaurant_id=restaurant_id,
            alert_type="price_increase",
            severity=severity,
            ingredient_id=ingredient_id,
            invoice_id=invoice_id,
            message=message,
            details={
                "ingredient_name": ingredient_name,
                "old_price": old_price,
                "new_price": new_price,
                "percent_change": round(percent_change, 1),
            },
        )
        db.add(alert)
        alerts.append(alert)

    # 2. Check affected recipes for margin threshold breaches
    recipe_result = await db.execute(
        select(Recipe)
        .join(RecipeIngredient)
        .where(
            RecipeIngredient.ingredient_id == ingredient_id,
            Recipe.restaurant_id == restaurant_id,
        )
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(
                RecipeIngredient.ingredient
            )
        )
    )
    affected_recipes = recipe_result.scalars().unique().all()

    for recipe in affected_recipes:
        if recipe.food_cost_percent is None:
            continue

        target = recipe.target_margin if recipe.target_margin is not None else 30.0
        status = get_margin_status(recipe.food_cost_percent, target)

        if status in ("orange", "red"):
            severity = "critical" if status == "red" else "warning"
            message = (
                f"{recipe.name} dépasse le seuil : "
                f"food cost {recipe.food_cost_percent:.1f}% (objectif < {target:.0f}%)"
            )

            alert = Alert(
                restaurant_id=restaurant_id,
                alert_type="margin_exceeded",
                severity=severity,
                recipe_id=recipe.id,
                ingredient_id=ingredient_id,
                invoice_id=invoice_id,
                message=message,
                details={
                    "recipe_name": recipe.name,
                    "food_cost_percent": recipe.food_cost_percent,
                    "target_margin": target,
                    "selling_price": recipe.selling_price,
                },
            )
            db.add(alert)
            alerts.append(alert)

    if alerts:
        await db.flush()
        logger.info(f"Created {len(alerts)} alert(s) for restaurant {restaurant_id}")

    return alerts


async def get_unread_count(db: AsyncSession, restaurant_id: int) -> int:
    """Count unread alerts for a restaurant."""
    result = await db.execute(
        select(func.count())
        .select_from(Alert)
        .where(Alert.restaurant_id == restaurant_id, Alert.is_read == False)  # noqa: E712
    )
    return result.scalar_one()


def generate_alert_email_html(alerts: list[Alert]) -> str:
    """Generate HTML email summarizing alerts.

    For now, just generates the HTML — sending via Resend comes later.
    """
    if not alerts:
        return ""

    rows = ""
    for alert in alerts:
        icon = "🔴" if alert.severity == "critical" else "🟠"
        rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e7e5e4;">
                {icon} {alert.message}
            </td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #fafaf9; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; border: 1px solid #e7e5e4; overflow: hidden;">
            <div style="background: #c2410c; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 20px;">⚠️ Margó — Alertes sur tes marges</h1>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                {rows}
            </table>
            <div style="padding: 20px; text-align: center; color: #78716c; font-size: 14px;">
                <p>Connecte-toi sur <a href="https://heymargo.be" style="color: #c2410c;">heymargo.be</a> pour corriger tes marges</p>
            </div>
        </div>
    </body>
    </html>
    """
