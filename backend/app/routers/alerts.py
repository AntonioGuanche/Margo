"""Alert API endpoints — list, count, mark read."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.alert import Alert
from app.models.restaurant import Restaurant
from app.schemas.alert import AlertCountResponse, AlertListResponse, AlertResponse
from app.services.alerts import get_unread_count

router = APIRouter()


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    is_read: bool | None = Query(None, description="Filter by read status"),
    severity: str | None = Query(None, description="Filter by severity"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """List alerts for the current restaurant, sorted by created_at desc."""
    query = select(Alert).where(Alert.restaurant_id == restaurant.id)

    if is_read is not None:
        query = query.where(Alert.is_read == is_read)

    if severity:
        query = query.where(Alert.severity == severity)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Unread count (always for this restaurant, regardless of filters)
    unread = await get_unread_count(db, restaurant.id)

    # Paginated results
    items_query = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(items_query)
    items = result.scalars().all()

    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in items],
        total=total,
        unread_count=unread,
    )


@router.get("/count", response_model=AlertCountResponse)
async def alert_count(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> AlertCountResponse:
    """Get unread alert count (lightweight endpoint for badge polling)."""
    unread = await get_unread_count(db, restaurant.id)
    return AlertCountResponse(unread_count=unread)


@router.put("/{alert_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_alert_read(
    alert_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark a single alert as read."""
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.restaurant_id == restaurant.id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte introuvable",
        )

    alert.is_read = True
    await db.flush()


@router.put("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark all alerts as read for the current restaurant."""
    await db.execute(
        update(Alert)
        .where(Alert.restaurant_id == restaurant.id, Alert.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.flush()
