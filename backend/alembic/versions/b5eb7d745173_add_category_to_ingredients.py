"""add_category_to_ingredients

Revision ID: b5eb7d745173
Revises: 967d0c82564a
Create Date: 2026-02-23 19:14:30.144919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5eb7d745173'
down_revision: Union[str, None] = '967d0c82564a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ingredients', sa.Column('category', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('ingredients', 'category')
