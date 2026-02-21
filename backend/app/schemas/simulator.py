"""Simulator request/response schemas."""

from pydantic import BaseModel


class IngredientAdjustment(BaseModel):
    ingredient_id: int
    new_quantity: float | None = None
    new_unit_price: float | None = None


class SimulateRequest(BaseModel):
    new_selling_price: float | None = None
    ingredient_adjustments: list[IngredientAdjustment] | None = None
    estimated_weekly_sales: int | None = None


class SimulatedIngredient(BaseModel):
    ingredient_id: int
    ingredient_name: str
    quantity: float
    unit: str
    unit_price: float | None
    line_cost: float | None
    changed: bool


class SimulationState(BaseModel):
    selling_price: float
    food_cost: float
    food_cost_percent: float
    margin_status: str  # green/orange/red
    gross_margin: float
    ingredients: list[SimulatedIngredient]


class SimulateResponse(BaseModel):
    recipe_name: str
    current: SimulationState
    simulated: SimulationState
    monthly_impact: float | None = None
