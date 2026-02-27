"""One-time migration: normalize all ingredient units to base (kg, l, piece).

Usage: cd backend && python -m scripts.normalize_units
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.database import async_session, engine
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.services.costing import normalize_to_base_unit, recalculate_recipe


async def migrate():
    async with async_session() as db:
        result = await db.execute(select(Ingredient))
        ingredients = result.scalars().all()

        fixed = 0
        for ing in ingredients:
            base_unit, base_price = normalize_to_base_unit(ing.unit, ing.current_price)

            if base_unit != ing.unit or base_price != ing.current_price:
                print(f"  FIX: {ing.name}")
                print(f"    unit: {ing.unit} → {base_unit}")
                print(f"    price: {ing.current_price} → {base_price}")
                ing.unit = base_unit
                ing.current_price = base_price
                fixed += 1

        await db.commit()
        print(f"\nFixed {fixed}/{len(ingredients)} ingredients.")

        # Recalculate ALL recipes after normalization
        result = await db.execute(select(Recipe.id))
        recipe_ids = result.scalars().all()

        for rid in recipe_ids:
            await recalculate_recipe(db, rid)

        await db.commit()
        print(f"Recalculated {len(recipe_ids)} recipes.")


if __name__ == "__main__":
    asyncio.run(migrate())
