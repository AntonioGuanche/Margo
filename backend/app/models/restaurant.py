"""Restaurant model."""

from datetime import datetime

from sqlalchemy import String, func
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
