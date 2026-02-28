"""Invoice API endpoints — upload, list, detail, confirm, delete."""

import datetime as dt
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.plan_limits import require_invoice_quota
from app.middleware.rate_limit import check_upload_rate_limit
from app.models.ingredient import Ingredient
from app.models.ingredient_alias import IngredientAlias
from app.models.invoice import Invoice
from app.models.price_history import IngredientPriceHistory
from app.models.recipe import Recipe, RecipeIngredient
from app.models.restaurant import Restaurant
from app.dependencies import get_current_restaurant
from app.schemas.invoice import (
    IngredientSuggestion,
    InvoiceConfirmRequest,
    InvoiceConfirmResponse,
    InvoiceDetailResponse,
    InvoiceLineResponse,
    InvoiceListItem,
    InvoiceListResponse,
    InvoicePatchRequest,
    InvoiceUploadResponse,
)
from app.services.alerts import check_and_create_alerts
from app.services.costing import UNIT_TO_BASE, normalize_to_base_unit, recalculate_recipes_for_ingredient
from app.services.invoice_router import parse_invoice_file
from app.services.matching import match_invoice_lines, save_alias
from app.services.unit_parser import (
    SERVING_SIZES,
    guess_serving_type,
    parse_units_per_package,
    parse_volume_liters,
)
from app.services.utils import guess_ingredient_category
from app.services.storage import save_upload

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Upload validation ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/xml",
    "text/xml",
}


def _compute_portion_fields(
    description: str,
    total_price: float | None,
    units_per_package: int | None,
) -> dict:
    """Compute volume-based portion fields for a line (only if no units_per_package)."""
    if units_per_package:
        return {}
    volume = parse_volume_liters(description)
    serving_type = guess_serving_type(description)
    if volume and serving_type:
        serving_cl = SERVING_SIZES[serving_type]
        portions = int(volume * 100 / serving_cl)
        price_per_portion = (
            total_price / portions if portions > 0 and total_price else None
        )
        return {
            "volume_liters": volume,
            "serving_type": serving_type,
            "suggested_serving_cl": serving_cl,
            "suggested_portions": portions,
            "price_per_portion": round(price_per_portion, 4) if price_per_portion else None,
        }
    return {}


def _build_line_responses(match_results: list) -> list[dict]:
    """Convert MatchResult list to serializable dicts for JSONB storage."""
    lines = []
    for mr in match_results:
        # Use OCR value if available, otherwise apply deterministic fallback
        upp = mr.invoice_line.units_per_package
        if upp is None:
            upp = parse_units_per_package(mr.invoice_line.description)
        lines.append({
            "description": mr.invoice_line.description,
            "quantity": mr.invoice_line.quantity,
            "unit": mr.invoice_line.unit,
            "unit_price": mr.invoice_line.unit_price,
            "total_price": mr.invoice_line.total_price,
            "matched_ingredient_id": mr.matched_ingredient_id,
            "matched_ingredient_name": mr.matched_ingredient_name,
            "units_per_package": upp,
            "match_confidence": mr.confidence,
            "suggestions": mr.suggestions,
        })
    return lines


def _line_dict_to_response(ld: dict) -> InvoiceLineResponse:
    """Convert a JSONB line dict to InvoiceLineResponse, with portion computation."""
    upp = ld.get("units_per_package")
    if upp is None:
        upp = parse_units_per_package(ld.get("description", ""))
    portion = _compute_portion_fields(ld.get("description", ""), ld.get("total_price"), upp)
    return InvoiceLineResponse(
        description=ld["description"],
        quantity=ld.get("quantity"),
        unit=ld.get("unit"),
        unit_price=ld.get("unit_price"),
        total_price=ld.get("total_price"),
        units_per_package=upp,
        volume_liters=portion.get("volume_liters"),
        serving_type=portion.get("serving_type"),
        suggested_serving_cl=portion.get("suggested_serving_cl"),
        suggested_portions=portion.get("suggested_portions"),
        price_per_portion=portion.get("price_per_portion"),
        matched_ingredient_id=ld.get("matched_ingredient_id"),
        matched_ingredient_name=ld.get("matched_ingredient_name"),
        match_confidence=ld.get("match_confidence", "none"),
        suggestions=[
            IngredientSuggestion(**s) for s in ld.get("suggestions", [])
        ],
    )


@router.post("/upload", response_model=InvoiceUploadResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    restaurant: Restaurant = Depends(require_invoice_quota),
) -> InvoiceUploadResponse:
    """Upload an invoice file (XML, PDF, or image).

    Parses the file, matches lines to ingredients, and saves to DB.
    """
    # Rate limit
    check_upload_rate_limit(restaurant.id)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le fichier doit avoir un nom.",
        )

    # Validate MIME type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        valid_extensions = {"jpg", "jpeg", "png", "webp", "pdf", "xml"}
        if ext not in valid_extensions:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Format non supporté : {content_type or ext}. Formats acceptés : JPEG, PNG, WebP, PDF, XML.",
            )

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        size_mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux ({size_mb:.1f} MB). Maximum : 10 MB.",
        )
    await file.seek(0)

    logger.info(
        "Invoice upload: %s (%s, %.1f KB)",
        file.filename,
        content_type,
        len(content) / 1024,
        extra={"restaurant_id": restaurant.id},
    )

    # Save file
    file_path = await save_upload(file, subfolder="invoices")

    # Parse
    parsed = await parse_invoice_file(file_path, file.filename)

    # Match lines to ingredients
    match_results = await match_invoice_lines(db, restaurant.id, parsed.lines)

    # Build serializable line data
    line_dicts = _build_line_responses(match_results)

    # Create Invoice in DB
    invoice = Invoice(
        restaurant_id=restaurant.id,
        image_url=file_path,
        supplier_name=parsed.supplier_name,
        invoice_date=dt.date.fromisoformat(parsed.invoice_date) if parsed.invoice_date else None,
        source="upload",
        format=parsed.format,
        status="pending_review",
        extracted_lines=line_dicts,
        total_amount=parsed.total_incl_vat or parsed.total_excl_vat,
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)

    # Build response
    response_lines = [_line_dict_to_response(ld) for ld in line_dicts]

    return InvoiceUploadResponse(
        invoice_id=invoice.id,
        supplier_name=parsed.supplier_name,
        invoice_number=parsed.invoice_number,
        invoice_date=parsed.invoice_date,
        total_excl_vat=parsed.total_excl_vat,
        total_incl_vat=parsed.total_incl_vat,
        lines=response_lines,
        format=parsed.format,
        status="pending_review",
        raw_text=parsed.raw_text,
    )


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by supplier name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> InvoiceListResponse:
    """List invoices for the current restaurant."""
    query = select(Invoice).where(Invoice.restaurant_id == restaurant.id)

    if status:
        query = query.where(Invoice.status == status)
    if search:
        query = query.where(Invoice.supplier_name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch page — sort by invoice_date (nulls last), then created_at
    query = query.order_by(
        Invoice.invoice_date.desc().nulls_last(),
        Invoice.created_at.desc(),
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    invoices = result.scalars().all()

    items = []
    for inv in invoices:
        lines_count = len(inv.extracted_lines) if inv.extracted_lines else 0
        items.append(InvoiceListItem(
            id=inv.id,
            supplier_name=inv.supplier_name,
            invoice_date=str(inv.invoice_date) if inv.invoice_date else None,
            source=inv.source,
            format=inv.format,
            status=inv.status,
            total_amount=inv.total_amount,
            lines_count=lines_count,
            created_at=inv.created_at,
        ))

    return InvoiceListResponse(items=items, total=total)


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> InvoiceDetailResponse:
    """Get invoice detail with lines and match results."""
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.restaurant_id == restaurant.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture introuvable.",
        )

    # Rebuild line responses from JSONB
    lines = [_line_dict_to_response(ld) for ld in (invoice.extracted_lines or [])]

    return InvoiceDetailResponse(
        id=invoice.id,
        supplier_name=invoice.supplier_name,
        invoice_date=str(invoice.invoice_date) if invoice.invoice_date else None,
        source=invoice.source,
        format=invoice.format,
        status=invoice.status,
        total_amount=invoice.total_amount,
        lines=lines,
        raw_text=None,  # Could store in JSONB if needed
        created_at=invoice.created_at,
    )


@router.post("/{invoice_id}/confirm", response_model=InvoiceConfirmResponse)
async def confirm_invoice(
    invoice_id: int,
    body: InvoiceConfirmRequest,
    db: AsyncSession = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> InvoiceConfirmResponse:
    """Confirm invoice lines: update prices, create ingredients, save aliases, recalculate recipes."""
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.restaurant_id == restaurant.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture introuvable.",
        )

    prices_updated = 0
    ingredients_created = 0
    aliases_saved = 0
    recipes_created = 0
    affected_ingredient_ids: set[int] = set()
    # Track old→new prices for alert generation
    price_changes: list[tuple[int, float | None, float]] = []  # (ingredient_id, old_price, new_price)

    for line in body.lines:
        # Skip ignored lines
        if line.ingredient_id is None and line.create_ingredient_name is None:
            continue

        ingredient_id = line.ingredient_id

        # Create new ingredient if requested
        if line.create_ingredient_name:
            raw_unit = line.unit or "kg"
            base_unit, base_price = normalize_to_base_unit(raw_unit, line.unit_price)
            new_ingredient = Ingredient(
                restaurant_id=restaurant.id,
                name=line.create_ingredient_name,
                unit=base_unit,
                current_price=base_price,
                supplier_name=invoice.supplier_name,
                category=guess_ingredient_category(line.create_ingredient_name),
                last_updated=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),
            )
            db.add(new_ingredient)
            await db.flush()
            await db.refresh(new_ingredient)
            ingredient_id = new_ingredient.id
            ingredients_created += 1

            # Save alias for the new ingredient
            await save_alias(db, restaurant.id, line.description, ingredient_id)
            aliases_saved += 1

        if ingredient_id and line.unit_price is not None:
            # Update ingredient price
            ing_result = await db.execute(
                select(Ingredient).where(
                    Ingredient.id == ingredient_id,
                    Ingredient.restaurant_id == restaurant.id,
                )
            )
            ingredient = ing_result.scalar_one_or_none()
            if ingredient:
                old_price = ingredient.current_price
                # Normalize line price to base unit using normalize_to_base_unit
                new_price = line.unit_price
                if new_price is not None and line.unit:
                    _, new_price = normalize_to_base_unit(line.unit, new_price)
                ingredient.current_price = new_price
                ingredient.last_updated = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
                if invoice.supplier_name:
                    ingredient.supplier_name = invoice.supplier_name
                prices_updated += 1
                affected_ingredient_ids.add(ingredient_id)
                price_changes.append((ingredient_id, old_price, new_price))

                # Record price history (normalized price)
                history = IngredientPriceHistory(
                    ingredient_id=ingredient_id,
                    price=new_price,
                    date=invoice.invoice_date or dt.date.today(),
                    invoice_id=invoice.id,
                )
                db.add(history)

                # Save alias if description differs from ingredient name
                if line.description.lower() != ingredient.name.lower():
                    await save_alias(db, restaurant.id, line.description, ingredient_id)
                    aliases_saved += 1

        # Multi-recipe support: loop through recipe_links
        for rl in line.recipe_links:
            recipe_id_for_link = rl.recipe_id

            # Create a new recipe/product if requested
            if rl.create_recipe_name and not rl.recipe_id:
                new_recipe = Recipe(
                    restaurant_id=restaurant.id,
                    name=rl.create_recipe_name,
                    selling_price=rl.create_recipe_price or 0,
                    category=rl.create_recipe_category,
                    is_homemade=rl.create_recipe_is_homemade,
                )
                db.add(new_recipe)
                await db.flush()
                recipe_id_for_link = new_recipe.id
                recipes_created += 1

            if recipe_id_for_link and ingredient_id:
                # Verify recipe belongs to restaurant
                recipe_result = await db.execute(
                    select(Recipe).where(
                        Recipe.id == recipe_id_for_link,
                        Recipe.restaurant_id == restaurant.id,
                    )
                )
                if recipe_result.scalar_one_or_none():
                    # Check if link already exists
                    existing_ri = await db.execute(
                        select(RecipeIngredient).where(
                            RecipeIngredient.recipe_id == recipe_id_for_link,
                            RecipeIngredient.ingredient_id == ingredient_id,
                        )
                    )
                    if not existing_ri.scalar_one_or_none():
                        ri = RecipeIngredient(
                            recipe_id=recipe_id_for_link,
                            ingredient_id=ingredient_id,
                            quantity=rl.quantity,
                            unit=rl.unit,
                        )
                        db.add(ri)
                        affected_ingredient_ids.add(ingredient_id)

    # Cascade recalculate all affected recipes
    recipes_recalculated = 0
    for ing_id in affected_ingredient_ids:
        await recalculate_recipes_for_ingredient(db, ing_id)
        recipes_recalculated += 1  # Count unique ingredients that triggered recalc

    # Generate alerts for price changes (after recalculation so food_cost_percent is up to date)
    for ing_id, old_price, new_price in price_changes:
        await check_and_create_alerts(
            db, restaurant.id, ing_id, old_price, new_price, invoice.id
        )

    # Update invoice status
    invoice.status = "confirmed"
    await db.flush()

    logger.info(
        "Invoice %d confirmed: %d prices updated, %d ingredients created, %d recipes recalculated",
        invoice_id,
        prices_updated,
        ingredients_created,
        recipes_recalculated,
        extra={"restaurant_id": restaurant.id},
    )

    return InvoiceConfirmResponse(
        prices_updated=prices_updated,
        ingredients_created=ingredients_created,
        aliases_saved=aliases_saved,
        recipes_recalculated=recipes_recalculated,
        recipes_created=recipes_created,
    )


@router.patch("/{invoice_id}", response_model=InvoiceDetailResponse)
async def patch_invoice(
    invoice_id: int,
    body: InvoicePatchRequest,
    db: AsyncSession = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> InvoiceDetailResponse:
    """Update supplier name and/or date on a pending invoice."""
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.restaurant_id == restaurant.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture introuvable.",
        )

    if body.supplier_name is not None:
        invoice.supplier_name = body.supplier_name
    if body.invoice_date is not None:
        invoice.invoice_date = dt.date.fromisoformat(body.invoice_date)

    await db.flush()
    await db.refresh(invoice)

    # Build response
    lines = [_line_dict_to_response(ld) for ld in (invoice.extracted_lines or [])]

    return InvoiceDetailResponse(
        id=invoice.id,
        supplier_name=invoice.supplier_name,
        invoice_date=str(invoice.invoice_date) if invoice.invoice_date else None,
        source=invoice.source,
        format=invoice.format,
        status=invoice.status,
        total_amount=invoice.total_amount,
        lines=lines,
        raw_text=None,
        created_at=invoice.created_at,
    )


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> None:
    """Delete a pending invoice. Cannot delete confirmed invoices."""
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.restaurant_id == restaurant.id,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture introuvable.",
        )

    # Detach price history entries before deleting invoice (invoice_id FK has no ondelete)
    await db.execute(
        update(IngredientPriceHistory)
        .where(IngredientPriceHistory.invoice_id == invoice_id)
        .values(invoice_id=None)
    )

    await db.delete(invoice)
    await db.flush()
