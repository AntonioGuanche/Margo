"""Restaurant management routes — list, create sub-restaurant, switch."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_restaurant
from app.models.restaurant import Restaurant
from app.services.auth import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


class RestaurantResponse(BaseModel):
    id: int
    name: str
    owner_email: str
    plan: str
    default_target_margin: float
    parent_restaurant_id: int | None = None


class RestaurantListResponse(BaseModel):
    main: RestaurantResponse
    sub_restaurants: list[RestaurantResponse]


class CreateSubRestaurantRequest(BaseModel):
    name: str


class SwitchResponse(BaseModel):
    access_token: str
    restaurant_id: int
    restaurant_name: str


class UpdateRestaurantRequest(BaseModel):
    name: str | None = None
    default_target_margin: float | None = None


@router.get("", response_model=RestaurantListResponse)
async def list_restaurants(
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> RestaurantListResponse:
    """Return the main restaurant + sub-restaurants (if multi plan)."""
    # Find the main restaurant (the one without parent)
    main_restaurant = restaurant
    if restaurant.parent_restaurant_id is not None:
        main_result = await db.get(Restaurant, restaurant.parent_restaurant_id)
        if main_result:
            main_restaurant = main_result

    main_resp = RestaurantResponse(
        id=main_restaurant.id,
        name=main_restaurant.name,
        owner_email=main_restaurant.owner_email,
        plan=main_restaurant.plan or "free",
        default_target_margin=main_restaurant.default_target_margin,
        parent_restaurant_id=main_restaurant.parent_restaurant_id,
    )

    subs: list[RestaurantResponse] = []
    if (main_restaurant.plan or "free") == "multi":
        result = await db.execute(
            select(Restaurant).where(
                Restaurant.parent_restaurant_id == main_restaurant.id
            )
        )
        for sub in result.scalars().all():
            subs.append(RestaurantResponse(
                id=sub.id,
                name=sub.name,
                owner_email=sub.owner_email,
                plan=sub.plan or "free",
                default_target_margin=sub.default_target_margin,
                parent_restaurant_id=sub.parent_restaurant_id,
            ))

    return RestaurantListResponse(main=main_resp, sub_restaurants=subs)


@router.post("", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
async def create_sub_restaurant(
    body: CreateSubRestaurantRequest,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> RestaurantResponse:
    """Create a sub-restaurant (multi plan only, max 5)."""
    # Find the main restaurant
    main_restaurant = restaurant
    if restaurant.parent_restaurant_id is not None:
        main_result = await db.get(Restaurant, restaurant.parent_restaurant_id)
        if main_result:
            main_restaurant = main_result

    if (main_restaurant.plan or "free") != "multi":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le plan Multi est requis pour ajouter des établissements.",
        )

    # Count existing sub-restaurants
    count_result = await db.execute(
        select(func.count()).select_from(
            select(Restaurant).where(
                Restaurant.parent_restaurant_id == main_restaurant.id
            ).subquery()
        )
    )
    count = count_result.scalar_one()
    if count >= 5:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maximum 5 sous-établissements.",
        )

    # Generate a unique email for the sub-restaurant (owner_email has unique constraint)
    base_email = main_restaurant.owner_email
    sub_email = f"sub_{count + 1}+{base_email}"

    sub = Restaurant(
        name=body.name,
        owner_email=sub_email,
        plan=main_restaurant.plan,
        parent_restaurant_id=main_restaurant.id,
        default_target_margin=main_restaurant.default_target_margin,
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)

    logger.info(
        "Sub-restaurant created: %s (id=%d) under main=%d",
        sub.name, sub.id, main_restaurant.id,
    )

    return RestaurantResponse(
        id=sub.id,
        name=sub.name,
        owner_email=sub.owner_email,
        plan=sub.plan or "free",
        default_target_margin=sub.default_target_margin,
        parent_restaurant_id=sub.parent_restaurant_id,
    )


@router.put("/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant(
    restaurant_id: int,
    body: UpdateRestaurantRequest,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> RestaurantResponse:
    """Update restaurant name or target margin."""
    # Verify ownership
    target = await db.get(Restaurant, restaurant_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant introuvable."
        )

    # Must be the same restaurant or a sub of it
    if target.id != restaurant.id and target.parent_restaurant_id != restaurant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu ne peux modifier que tes propres établissements.",
        )

    if body.name is not None:
        target.name = body.name
    if body.default_target_margin is not None:
        target.default_target_margin = body.default_target_margin

    await db.flush()
    await db.refresh(target)

    return RestaurantResponse(
        id=target.id,
        name=target.name,
        owner_email=target.owner_email,
        plan=target.plan or "free",
        default_target_margin=target.default_target_margin,
        parent_restaurant_id=target.parent_restaurant_id,
    )


@router.get("/{restaurant_id}/switch", response_model=SwitchResponse)
async def switch_restaurant(
    restaurant_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: AsyncSession = Depends(get_db),
) -> SwitchResponse:
    """Switch context to another restaurant. Returns a new JWT."""
    target = await db.get(Restaurant, restaurant_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant introuvable."
        )

    # Must be the same owner (main or sub)
    main_id = restaurant.parent_restaurant_id or restaurant.id
    target_main_id = target.parent_restaurant_id or target.id
    if main_id != target_main_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu ne peux switcher que vers tes propres établissements.",
        )

    new_token = create_access_token(target.id, target.owner_email)

    return SwitchResponse(
        access_token=new_token,
        restaurant_id=target.id,
        restaurant_name=target.name,
    )
