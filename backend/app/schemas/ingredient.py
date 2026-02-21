"""Ingredient request/response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UnitType = Literal["g", "kg", "cl", "l", "piece"]


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    unit: UnitType
    current_price: float | None = None
    supplier_name: str | None = None


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    unit: UnitType | None = None
    current_price: float | None = None
    supplier_name: str | None = None


class IngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    unit: str
    current_price: float | None
    supplier_name: str | None
    last_updated: datetime | None
    created_at: datetime


class IngredientListResponse(BaseModel):
    items: list[IngredientResponse]
    total: int
