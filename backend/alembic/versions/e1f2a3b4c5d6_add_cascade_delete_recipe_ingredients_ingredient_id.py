"""add_cascade_delete_recipe_ingredients_ingredient_id

Revision ID: e1f2a3b4c5d6
Revises: af16fbd67992
Create Date: 2026-02-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'af16fbd67992'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ondelete=CASCADE to recipe_ingredients.ingredient_id FK
    # so that deleting an ingredient automatically removes its recipe_ingredient rows
    op.drop_constraint(
        'recipe_ingredients_ingredient_id_fkey',
        'recipe_ingredients',
        type_='foreignkey',
    )
    op.create_foreign_key(
        None,
        'recipe_ingredients',
        'ingredients',
        ['ingredient_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(None, 'recipe_ingredients', type_='foreignkey')
    op.create_foreign_key(
        'recipe_ingredients_ingredient_id_fkey',
        'recipe_ingredients',
        'ingredients',
        ['ingredient_id'],
        ['id'],
    )
