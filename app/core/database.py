"""
Database Connection (SQLAlchemy + AsyncPG + Supabase Pooler)

✅ SERVERLESS OPTIMIZED for Google Cloud Run + Supabase Transaction Pooler

Architecture:
- Uses NullPool (no app-side pooling) because Supabase Supavisor handles pooling
- Async engine with asyncpg driver for high performance
- Session-per-request pattern with dependency injection
- Connection timeout optimized for serverless cold starts

Key Design Decisions:
1. NullPool: Prevents "connection closed unexpectedly" errors during Cloud Run scale up/down
2. Supabase Pooler (port 6543): Requires NullPool because pooler manages connections
3. Prepared Statement Caching disabled: Required for transaction pooler mode
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# =====================================================
# BASE MODEL
# =====================================================
Base = declarative_base()

# =====================================================
# ENGINE CONFIGURATION
# =====================================================

# ✅ CRITICAL: NullPool for Supabase Transaction Pooler (Supavisor)
# Supabase's pooler (port 6543) manages connections - app should NOT pool
_engine_options = {
    "poolclass": NullPool,  # No app-side pooling (Supabase pooler handles it)
    "echo": settings.ENVIRONMENT == "development",  # SQL logging in dev only
    # ✅ Connection arguments for asyncpg driver
    "connect_args": {
        # Disable prepared statement caching (required for transaction pooler)
        "prepared_statement_cache_size": 0,
        # Timeout for connection attempts (serverless cold start tolerance)
        "timeout": 30,
        # Command timeout for queries
        "command_timeout": 60,
    },
}

# Create async engine (singleton)
engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    **_engine_options
)

# Session factory (async)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy load after commit in async
    autocommit=False,
    autoflush=False,
)

logger.info(f"✅ Database engine configured with NullPool for Supabase Pooler")


# =====================================================
# SESSION DEPENDENCY (FastAPI)
# =====================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency: Get database session per-request.
    
    Usage:
        @router.get("/users/{id}")
        async def get_user(id: str, db: AsyncSession = Depends(get_db)):
            ...
    
    ✅ CRITICAL: Session is closed after request (NullPool returns connection to Supabase)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database session error: {e}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions (for use outside FastAPI routes).
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(...)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database context error: {e}")
            raise
        finally:
            await session.close()


# =====================================================
# LIFECYCLE HOOKS (for FastAPI lifespan)
# =====================================================

async def init_db():
    """Initialize database (create tables if needed)"""
    # Tables should be created via migrations (Alembic)
    # This is just for connection verification
    try:
        async with engine.begin() as conn:
            # Simple query to verify connection
            await conn.execute("SELECT 1")
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


async def close_db():
    """Close database engine (called on shutdown)"""
    try:
        await engine.dispose()
        logger.info("✅ Database engine disposed")
    except Exception as e:
        logger.error(f"⚠️ Error disposing database engine: {e}")
