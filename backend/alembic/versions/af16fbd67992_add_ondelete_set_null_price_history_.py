"""add_ondelete_set_null_price_history_invoice_id

Revision ID: af16fbd67992
Revises: b5eb7d745173
Create Date: 2026-02-28 11:19:41.770396

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'af16fbd67992'
down_revision: Union[str, None] = 'b5eb7d745173'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ondelete=SET NULL to ingredient_price_history.invoice_id FK
    # so that deleting an invoice automatically NULLs the reference
    op.drop_constraint(
        'ingredient_price_history_invoice_id_fkey',
        'ingredient_price_history',
        type_='foreignkey',
    )
    op.create_foreign_key(
        None,
        'ingredient_price_history',
        'invoices',
        ['invoice_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(None, 'ingredient_price_history', type_='foreignkey')
    op.create_foreign_key(
        'ingredient_price_history_invoice_id_fkey',
        'ingredient_price_history',
        'invoices',
        ['invoice_id'],
        ['id'],
    )
