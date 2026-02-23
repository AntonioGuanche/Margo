"""Invoice Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel


# --- Shared ---

class IngredientSuggestion(BaseModel):
    id: int
    name: str
    score: float


# --- Upload response ---

class InvoiceLineResponse(BaseModel):
    description: str
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    matched_ingredient_id: int | None = None
    matched_ingredient_name: str | None = None
    match_confidence: str = "none"
    suggestions: list[IngredientSuggestion] = []


class InvoiceUploadResponse(BaseModel):
    invoice_id: int
    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    total_excl_vat: float | None = None
    total_incl_vat: float | None = None
    lines: list[InvoiceLineResponse] = []
    format: str
    status: str = "pending_review"
    raw_text: str | None = None


# --- Confirmation ---

class InvoiceConfirmLine(BaseModel):
    description: str
    ingredient_id: int | None = None  # null = ignore this line
    create_ingredient_name: str | None = None  # if new, create with this name
    unit_price: float | None = None
    unit: str | None = None
    # Optional: associate this ingredient with an existing recipe
    add_to_recipe_id: int | None = None
    recipe_quantity: float | None = None
    recipe_unit: str | None = None


class InvoiceConfirmRequest(BaseModel):
    lines: list[InvoiceConfirmLine]


class InvoiceConfirmResponse(BaseModel):
    prices_updated: int
    ingredients_created: int
    aliases_saved: int
    recipes_recalculated: int


# --- List ---

class InvoiceListItem(BaseModel):
    id: int
    supplier_name: str | None = None
    invoice_date: str | None = None
    source: str
    format: str
    status: str
    total_amount: float | None = None
    lines_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    items: list[InvoiceListItem]
    total: int


# --- Patch ---

class InvoicePatchRequest(BaseModel):
    supplier_name: str | None = None
    invoice_date: str | None = None  # YYYY-MM-DD


# --- Detail ---

class InvoiceDetailResponse(BaseModel):
    id: int
    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    source: str
    format: str
    status: str
    total_amount: float | None = None
    lines: list[InvoiceLineResponse] = []
    raw_text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
