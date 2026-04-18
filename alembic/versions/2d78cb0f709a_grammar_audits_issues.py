"""grammar audits + issues

Revision ID: 2d78cb0f709a
Revises: de6b6049d7ca
Create Date: 2025-09-14 00:41:15.888095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d78cb0f709a'
down_revision: Union[str, Sequence[str], None] = 'de6b6049d7ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
