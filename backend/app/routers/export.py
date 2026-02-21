"""Export routes — CSV export for invoices and food costs."""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.invoice import Invoice
from app.models.recipe import Recipe
from app.models.restaurant import Restaurant
from app.services.costing import get_margin_status

router = APIRouter()


@router.get("/invoices")
async def export_invoices_csv(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export invoices as CSV with date filtering."""
    query = select(Invoice).where(
        Invoice.restaurant_id == restaurant.id,
        Invoice.status == "confirmed",
    )

    if from_date:
        query = query.where(Invoice.invoice_date >= from_date)
    if to_date:
        query = query.where(Invoice.invoice_date <= to_date)

    query = query.order_by(Invoice.invoice_date.asc())
    result = await db.execute(query)
    invoices = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Header
    writer.writerow([
        "Date facture",
        "Fournisseur",
        "Source",
        "Format",
        "Montant total",
        "Statut",
    ])

    for inv in invoices:
        writer.writerow([
            str(inv.invoice_date) if inv.invoice_date else "",
            inv.supplier_name or "",
            inv.source or "",
            inv.format or "",
            f"{inv.total_amount:.2f}" if inv.total_amount else "",
            inv.status,
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=factures_export.csv"
        },
    )


@router.get("/food-costs")
async def export_food_costs_csv(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export food costs for all recipes as CSV."""
    result = await db.execute(
        select(Recipe)
        .where(Recipe.restaurant_id == restaurant.id)
        .order_by(Recipe.name)
    )
    recipes = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Header
    writer.writerow([
        "Recette",
        "Catégorie",
        "Prix de vente",
        "Coût matière",
        "Food cost %",
        "Marge brute",
        "Statut",
    ])

    for r in recipes:
        target = r.target_margin if r.target_margin is not None else 30.0
        margin_status = get_margin_status(r.food_cost_percent, target)
        status_label = {"green": "🟢 OK", "orange": "🟠 Attention", "red": "🔴 Critique"}.get(
            margin_status, ""
        )
        gross_margin = (
            round(r.selling_price - r.food_cost, 2)
            if r.food_cost is not None
            else None
        )

        writer.writerow([
            r.name,
            r.category or "",
            f"{r.selling_price:.2f}",
            f"{r.food_cost:.2f}" if r.food_cost is not None else "",
            f"{r.food_cost_percent:.1f}" if r.food_cost_percent is not None else "",
            f"{gross_margin:.2f}" if gross_margin is not None else "",
            status_label,
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=food_costs_export.csv"
        },
    )
