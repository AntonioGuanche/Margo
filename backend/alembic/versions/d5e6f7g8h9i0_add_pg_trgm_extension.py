"""add pg_trgm extension (optional)

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2025-02-22 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d5e6f7g8h9i0"
down_revision: Union[str, None] = "c4d5e6f7g8h9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pg_trgm for fuzzy invoice matching. Non-fatal if unavailable."""
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    except Exception:
        # pg_trgm may not be available on some hosts — matching service
        # gracefully falls back to exact/alias matching at runtime.
        pass


def downgrade() -> None:
    try:
        op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
    except Exception:
        pass
