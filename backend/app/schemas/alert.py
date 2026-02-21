"""Alert request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: str
    severity: str
    message: str
    details: dict | None = None
    is_read: bool
    ingredient_id: int | None = None
    recipe_id: int | None = None
    created_at: datetime


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    unread_count: int


class AlertCountResponse(BaseModel):
    unread_count: int
