import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine

from alembic import context

# ---------------------------------------------------------
# IMPORT KONFIGURASI APP KAMU DI SINI
# ---------------------------------------------------------
import sys
import os

# Tambahkan path root biar bisa import 'app'
sys.path.append(os.getcwd())

from app.core.config import settings # <-- Baca config dari sini
from app.db.base import Base # <-- Baca Base dari sini

# ==================== IMPORT ALL MODELS ====================
# Import all models here so Alembic can detect them for migrations
# This ensures all tables are included in autogenerate
# NOTE: Models are imported here (not in base.py) to avoid circular imports

# Users
from app.modules.users.models import User  # noqa: F401

# Auth (if any models exist)
# from app.modules.auth.models import ...  # noqa: F401

# Training
from app.modules.training.models import (  # noqa: F401
    TrainingSection,
    TrainingUnit,
    TrainingLevel,
    TrainingQuestion,
    TrainingPath
)

# SKU
from app.modules.sku.models import (  # noqa: F401
    SkuPoint,
    SkuProgress,
    SpecialMission,
    MissionTask
)

# Cyber
from app.modules.cyber.models import (  # noqa: F401
    CyberChallenge,
    UserSolvedChallenge,
    CyberModule,
    CyberLevelProgress,
    SandiType,
    SandiQuestion,
    EncryptionLog
)

# Survival
from app.modules.survival.models import SurvivalMastery  # noqa: F401

# Add other module models as they are created:
# from app.modules.hiking.models import HikingSpot  # noqa: F401
# from app.modules.events.models import Event  # noqa: F401
# etc...
# ---------------------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# OVERRIDE URL DENGAN CONFIG DARI .ENV
# Ini biar password docker terbaca otomatis
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    
    ✅ Production Hardened:
    - Disables prepared statements for PgBouncer compatibility
    - Matches runtime engine configuration exactly
    - SSL support for Supabase
    - No global engine reuse (creates new engine per migration run)
    """
    # ✅ CRITICAL: Disable prepared statements for PgBouncer compatibility
    # PgBouncer in transaction pooling mode doesn't support prepared statements
    # This MUST match app/db/session.py configuration exactly
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
    
    # Get database URL from config
    database_url = config.get_main_option("sqlalchemy.url")
    
    # ✅ CRITICAL: SSL Configuration for Supabase (matches runtime)
    # Check if URL already contains SSL parameters
    has_ssl_param = "sslmode=" in database_url or "ssl=" in database_url
    is_supabase = "supabase" in database_url.lower()
    
    # Apply SSL context if needed (same logic as app/db/session.py)
    if (is_supabase or os.getenv("ENVIRONMENT", "development") == "production") and not has_ssl_param:
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False  # Supabase pooler uses different hostname
        ssl_context.verify_mode = ssl.CERT_NONE  # Disable cert verification for compatibility
        connect_args["ssl"] = ssl_context
    
    # Create engine with PgBouncer-compatible settings
    # ✅ CRITICAL: Use NullPool for migrations (no connection pooling needed)
    # Each migration run creates a fresh engine (no global reuse)
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,  # Alembic uses NullPool for migrations
        connect_args=connect_args,  # ✅ Disable prepared statements + SSL
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # ✅ CRITICAL: Dispose engine after migration (no lingering connections)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())