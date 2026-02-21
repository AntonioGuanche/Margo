"""SQLAlchemy ORM models — import all models here for Alembic discovery."""

from .alert import Alert
from .ingredient import Ingredient
from .ingredient_alias import IngredientAlias
from .invoice import Invoice
from .price_history import IngredientPriceHistory
from .recipe import Recipe, RecipeIngredient
from .restaurant import Restaurant

__all__ = [
    "Alert",
    "Ingredient",
    "IngredientAlias",
    "IngredientPriceHistory",
    "Invoice",
    "Recipe",
    "RecipeIngredient",
    "Restaurant",
]
