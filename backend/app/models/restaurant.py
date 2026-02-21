"""Restaurant model."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    default_target_margin: Mapped[float] = mapped_column(default=30.0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        onupdate=func.now(), server_default=func.now()
    )

    # Billing (Sprint 8)
    plan: Mapped[str] = mapped_column(String(20), default="free")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Multi-restaurant (Sprint 8)
    parent_restaurant_id: Mapped[int | None] = mapped_column(
        ForeignKey("restaurants.id"), nullable=True
    )

    # Relationships
    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    recipes: Mapped[list["Recipe"]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    aliases: Mapped[list["IngredientAlias"]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )
    sub_restaurants: Mapped[list["Restaurant"]] = relationship(
        "Restaurant", back_populates="parent", foreign_keys="[Restaurant.parent_restaurant_id]"
    )
    parent: Mapped["Restaurant | None"] = relationship(
        "Restaurant", back_populates="sub_restaurants", remote_side=[id],
        foreign_keys="[Restaurant.parent_restaurant_id]"
    )
