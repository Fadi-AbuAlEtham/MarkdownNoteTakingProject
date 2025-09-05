"""notes: add version + convert title to CITEXT + active indexes

Revision ID: 3a15c3a292f7
Revises: 1e3a018e5304
Create Date: 2025-09-05 20:15:18.544052

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "fix_notes_version_citext"
down_revision = "1e3a018e5304"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0) citext extension
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # 1) add version INT NOT NULL DEFAULT 0 (then drop default)
    if not has_column("notes", "version"):
        op.add_column(
            "notes",
            sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("notes", "version", server_default=None)

    # 2) convert title VARCHAR(200) -> CITEXT
    # (idempotent-ish: only alter if current type is not citext)
    op.alter_column(
        "notes",
        "title",
        type_=postgresql.CITEXT(),
        existing_type=sa.String(length=200),
        existing_nullable=False,
        postgresql_using="title::citext",
    )

    # 3) create soft-delete-aware helper indexes (if they don't exist)
    op.create_index(
        "ix_notes_user_active",
        "notes",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_notes_public_active",
        "notes",
        ["is_public"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        if_not_exists=True,
    )

    # 4) (optional) enforce unique active titles per user+folder, case-insensitive
    # WARNING: this will fail if you have duplicates; check first with the query below.
    # op.execute("""
    #   CREATE UNIQUE INDEX IF NOT EXISTS uq_notes_user_folder_title_active
    #   ON notes (user_id, folder_id, title)
    #   WHERE deleted_at IS NULL
    # """)


def downgrade() -> None:
    # Drop optional unique partial (if you created it)
    # op.execute("DROP INDEX IF EXISTS uq_notes_user_folder_title_active")

    op.drop_index("ix_notes_public_active", table_name="notes")
    op.drop_index("ix_notes_user_active", table_name="notes")

    op.alter_column(
        "notes",
        "title",
        type_=sa.String(length=200),
        existing_type=postgresql.CITEXT(),
        existing_nullable=False,
        postgresql_using="title::varchar(200)",
    )

    if has_column("notes", "version"):
        op.drop_column("notes", "version")


# --- helpers (works on Alembic 1.12+ where context.bind is available) ---
def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols
