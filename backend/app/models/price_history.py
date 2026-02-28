"""IngredientPriceHistory model."""

import datetime as dt

from sqlalchemy import Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngredientPriceHistory(Base):
    __tablename__ = "ingredient_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[float] = mapped_column(nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    # Relationships
    ingredient: Mapped["Ingredient"] = relationship(back_populates="price_history")
    invoice: Mapped["Invoice | None"] = relationship(back_populates="price_history_entries")
