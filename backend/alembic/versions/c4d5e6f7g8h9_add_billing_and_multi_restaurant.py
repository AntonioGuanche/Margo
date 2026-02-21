"""add billing and multi-restaurant fields

Revision ID: c4d5e6f7g8h9
Revises: b3c9d5e7f8a1
Create Date: 2025-02-21 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7g8h9"
down_revision: Union[str, None] = "b3c9d5e7f8a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Billing fields
    op.add_column("restaurants", sa.Column("plan", sa.String(20), server_default="free", nullable=False))
    op.add_column("restaurants", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("restaurants", sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
    op.add_column("restaurants", sa.Column("plan_expires_at", sa.DateTime(), nullable=True))

    # Multi-restaurant
    op.add_column("restaurants", sa.Column("parent_restaurant_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_restaurants_parent",
        "restaurants",
        "restaurants",
        ["parent_restaurant_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_restaurants_parent", "restaurants", type_="foreignkey")
    op.drop_column("restaurants", "parent_restaurant_id")
    op.drop_column("restaurants", "plan_expires_at")
    op.drop_column("restaurants", "stripe_subscription_id")
    op.drop_column("restaurants", "stripe_customer_id")
    op.drop_column("restaurants", "plan")
