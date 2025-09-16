from __future__ import annotations

import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# --- Load app settings & models ---------------------------------------------
# Make sure Alembic can import your app package (if needed, tweak sys.path)
# import os, sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()
from app.core.db import Base            # your declarative base

# Import ALL models so they register on Base.metadata
import app.models.user                  # noqa: F401
import app.models.folder                # noqa: F401
import app.models.tag                   # noqa: F401
import app.models.note                  # noqa: F401
import app.models.revision              # noqa: F401
import app.models.issue                 # noqa: F401
import app.models.note_tag              # noqa: F401

# ----------------------------------------------------------------------------

# Alembic Config object (access to .ini values)
config = context.config

# Ensure Alembic uses the same DB URL as your app
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL_SYNC"))

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata Alembic will compare against for --autogenerate
target_metadata = Base.metadata

print("ALEMBIC URL =", context.config.get_main_option("sqlalchemy.url"))
print("MODELS SEEN =", list(target_metadata.tables.keys()))

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # detect column type changes
        compare_server_default=True # detect server_default changes
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
