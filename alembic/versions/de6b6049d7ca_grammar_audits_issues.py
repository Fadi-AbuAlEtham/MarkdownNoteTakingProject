"""grammar audits + issues

Revision ID: de6b6049d7ca
Revises: c98ea2bca9d5
Create Date: 2025-09-14 00:40:48.082085

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de6b6049d7ca'
down_revision: Union[str, Sequence[str], None] = 'c98ea2bca9d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
