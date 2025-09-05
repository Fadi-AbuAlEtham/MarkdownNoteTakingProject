"""notes: add version, CITEXT title, partial active indexes

Revision ID: 1e3a018e5304
Revises: 7def3fbf6bab
Create Date: 2025-09-05 18:39:04.817909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e3a018e5304'
down_revision: Union[str, Sequence[str], None] = '7def3fbf6bab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
