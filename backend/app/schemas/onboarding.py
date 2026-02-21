"""Onboarding request/response schemas."""

from pydantic import BaseModel, Field


# --- Menu extraction ---

class ExtractedDish(BaseModel):
    name: str
    price: float | None = None
    category: str | None = None


class MenuExtractionResponse(BaseModel):
    dishes: list[ExtractedDish]
    image_path: str


# --- Ingredient suggestions ---

class SuggestIngredientsRequest(BaseModel):
    dishes: list[ExtractedDish]


class SuggestedIngredient(BaseModel):
    name: str
    quantity: float
    unit: str


class DishWithSuggestions(BaseModel):
    name: str
    price: float | None = None
    category: str | None = None
    ingredients: list[SuggestedIngredient]


class SuggestIngredientsResponse(BaseModel):
    dishes: list[DishWithSuggestions]


# --- Confirmation ---

class OnboardingConfirmDish(BaseModel):
    name: str
    selling_price: float = Field(gt=0)
    category: str | None = None
    ingredients: list[SuggestedIngredient]


class OnboardingConfirmRequest(BaseModel):
    dishes: list[OnboardingConfirmDish]


class OnboardingConfirmResponse(BaseModel):
    recipes_created: int
    ingredients_created: int
