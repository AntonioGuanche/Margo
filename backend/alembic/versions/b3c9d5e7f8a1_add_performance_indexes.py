"""Add performance indexes for alerts and invoices.

Revision ID: b3c9d5e7f8a1
Revises: a2f8c3d4e5b6
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c9d5e7f8a1"
down_revision: Union[str, None] = "a2f8c3d4e5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index for fast unread count per restaurant
    op.create_index(
        "ix_alerts_restaurant_is_read",
        "alerts",
        ["restaurant_id", "is_read"],
    )

    # Index for filtering invoices by status
    op.create_index(
        "ix_invoices_status",
        "invoices",
        ["status"],
    )

    # Index for invoice listing sorted by created_at
    op.create_index(
        "ix_invoices_restaurant_created",
        "invoices",
        ["restaurant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_restaurant_created", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_alerts_restaurant_is_read", table_name="alerts")
