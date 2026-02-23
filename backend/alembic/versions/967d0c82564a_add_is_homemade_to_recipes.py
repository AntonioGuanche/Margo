"""add_is_homemade_to_recipes

Revision ID: 967d0c82564a
Revises: d5e6f7g8h9i0
Create Date: 2026-02-23 17:32:46.508874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '967d0c82564a'
down_revision: Union[str, None] = 'd5e6f7g8h9i0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('recipes', sa.Column('is_homemade', sa.Boolean(), server_default='true', nullable=False))


def downgrade() -> None:
    op.drop_column('recipes', 'is_homemade')
