"""initial tables

Revision ID: 4b1bcb01510d
Revises:
Create Date: 2026-02-20 15:48:12.762690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4b1bcb01510d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- restaurants ---
    op.create_table(
        "restaurants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_email", sa.String(255), nullable=False),
        sa.Column("default_target_margin", sa.Float(), server_default="30.0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_restaurants_owner_email", "restaurants", ["owner_email"], unique=True)

    # --- ingredients ---
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_ingredients_restaurant_id", "ingredients", ["restaurant_id"])
    op.create_unique_constraint("uq_ingredient_restaurant_name", "ingredients", ["restaurant_id", "name"])

    # --- recipes ---
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("selling_price", sa.Float(), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("target_margin", sa.Float(), nullable=True),
        sa.Column("food_cost", sa.Float(), nullable=True),
        sa.Column("food_cost_percent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_recipes_restaurant_id", "recipes", ["restaurant_id"])

    # --- recipe_ingredients ---
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
    )
    op.create_index("ix_recipe_ingredients_recipe_id", "recipe_ingredients", ["recipe_id"])
    op.create_index("ix_recipe_ingredients_ingredient_id", "recipe_ingredients", ["ingredient_id"])
    op.create_unique_constraint("uq_recipe_ingredient", "recipe_ingredients", ["recipe_id", "ingredient_id"])

    # --- invoices ---
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
        sa.Column("extracted_lines", postgresql.JSONB(), nullable=True),
        sa.Column("matched_ingredients", postgresql.JSONB(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_invoices_restaurant_id", "invoices", ["restaurant_id"])

    # --- ingredient_price_history ---
    op.create_table(
        "ingredient_price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_ingredient_price_history_ingredient_id", "ingredient_price_history", ["ingredient_id"])

    # --- ingredient_aliases ---
    op.create_table(
        "ingredient_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_text", sa.String(500), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), sa.ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_ingredient_aliases_restaurant_id", "ingredient_aliases", ["restaurant_id"])
    op.create_index("ix_ingredient_aliases_ingredient_id", "ingredient_aliases", ["ingredient_id"])
    op.create_unique_constraint("uq_alias_restaurant_text", "ingredient_aliases", ["restaurant_id", "alias_text"])


def downgrade() -> None:
    op.drop_table("ingredient_aliases")
    op.drop_table("ingredient_price_history")
    op.drop_table("invoices")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
    op.drop_table("ingredients")
    op.drop_table("restaurants")
