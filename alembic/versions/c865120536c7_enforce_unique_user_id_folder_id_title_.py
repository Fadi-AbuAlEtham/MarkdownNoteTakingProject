"""enforce unique (user_id, folder_id, title) on active notes

Revision ID: c865120536c7
Revises: 0b176b7f1127
Create Date: 2025-09-26 14:29:06.769659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c865120536c7'
down_revision: Union[str, Sequence[str], None] = '0b176b7f1127'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
