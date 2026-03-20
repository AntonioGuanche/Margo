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
    units_per_package: int | None = None
    # Volume-based portion calculation
    volume_liters: float | None = None
    serving_type: str | None = None  # 'beer', 'wine', 'spirit'
    suggested_serving_cl: float | None = None  # 25, 12.5, 4
    suggested_portions: int | None = None
    price_per_portion: float | None = None
    matched_ingredient_id: int | None = None
    matched_ingredient_name: str | None = None
    match_confidence: str = "none"
    suggestions: list[IngredientSuggestion] = []
    ignored: bool = False
    draft_recipe_links: list[dict] | None = None  # User draft of recipe links (pre-confirm)


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
    image_url: str | None = None


# --- Confirmation ---

class RecipeLink(BaseModel):
    """A single recipe association for an invoice line."""
    recipe_id: int | None = None
    create_recipe_name: str | None = None
    create_recipe_price: float | None = None
    create_recipe_category: str | None = None
    create_recipe_is_homemade: bool = False
    quantity: float = 1
    unit: str = "piece"


class InvoiceConfirmLine(BaseModel):
    description: str
    ingredient_id: int | None = None  # null = ignore this line
    create_ingredient_name: str | None = None  # if new, create with this name
    unit_price: float | None = None
    unit: str | None = None
    ignored: bool = False
    recipe_links: list[RecipeLink] = []


class InvoiceConfirmRequest(BaseModel):
    lines: list[InvoiceConfirmLine]


class InvoiceConfirmResponse(BaseModel):
    prices_updated: int
    ingredients_created: int
    aliases_saved: int
    recipes_recalculated: int
    recipes_created: int = 0


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

class InvoiceLinePatchItem(BaseModel):
    """User edit for a single invoice line, identified by index."""
    matched_ingredient_id: int | None = None
    matched_ingredient_name: str | None = None
    ignored: bool = False
    draft_recipe_links: list[dict] | None = None  # User draft of recipe links (pre-confirm)
    # Editable line fields
    description: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None


class InvoicePatchRequest(BaseModel):
    supplier_name: str | None = None
    invoice_date: str | None = None  # YYYY-MM-DD
    lines: list[InvoiceLinePatchItem] | None = None  # user line edits, indexed by position


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
    image_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
