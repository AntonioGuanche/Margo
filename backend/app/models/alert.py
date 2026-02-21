"""Alert model."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Alert type
    alert_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "price_increase", "margin_exceeded"
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "warning", "critical"

    # Context
    ingredient_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True
    )
    recipe_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )

    # Data
    message: Mapped[str] = mapped_column(nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # State
    is_read: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship()
    ingredient: Mapped["Ingredient | None"] = relationship()
    recipe: Mapped["Recipe | None"] = relationship()
