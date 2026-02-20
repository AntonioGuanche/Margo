"""Ingredient model."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "name", name="uq_ingredient_restaurant_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    current_price: Mapped[float | None] = mapped_column(nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship(back_populates="ingredients")
    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="ingredient"
    )
    price_history: Mapped[list["IngredientPriceHistory"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
    aliases: Mapped[list["IngredientAlias"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
