"""Recipe request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecipeIngredientCreate(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)
    unit: str


class RecipeIngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: int
    ingredient_name: str
    quantity: float
    unit: str
    unit_cost: float | None
    unit_cost_unit: str | None = None
    line_cost: float | None


class RecipeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    selling_price: float = Field(gt=0)
    category: str | None = None
    target_margin: float | None = None
    is_homemade: bool = True
    ingredients: list[RecipeIngredientCreate] = Field(default_factory=list)


class RecipeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    selling_price: float | None = Field(default=None, gt=0)
    category: str | None = None
    target_margin: float | None = None
    is_homemade: bool | None = None
    ingredients: list[RecipeIngredientCreate] | None = None


class RecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    selling_price: float
    category: str | None
    target_margin: float | None
    food_cost: float | None
    food_cost_percent: float | None
    is_homemade: bool
    margin_status: str
    ingredients: list[RecipeIngredientResponse] = []
    created_at: datetime


class RecipeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    selling_price: float
    category: str | None
    target_margin: float | None
    food_cost: float | None
    food_cost_percent: float | None
    is_homemade: bool
    margin_status: str
    created_at: datetime


class RecipeListResponse(BaseModel):
    items: list[RecipeListItem]
    total: int


class DashboardResponse(BaseModel):
    average_food_cost_percent: float | None
    total_recipes: int
    recipes_green: int
    recipes_orange: int
    recipes_red: int
    recipes: list[RecipeListItem]
