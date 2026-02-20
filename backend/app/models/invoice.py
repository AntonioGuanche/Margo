"""Invoice model."""

import datetime as dt

from sqlalchemy import Date, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    extracted_lines: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    matched_ingredients: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[dt.datetime | None] = mapped_column(
        onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship(back_populates="invoices")
    price_history_entries: Mapped[list["IngredientPriceHistory"]] = relationship(
        back_populates="invoice"
    )
