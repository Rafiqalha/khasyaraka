from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import ssl

# Membuat Engine Async (menggunakan driver asyncpg)
# ✅ CRITICAL: SSL Configuration for Supabase
# Supabase requires SSL connections. For asyncpg, SSL is handled via connect_args
# 
# For asyncpg driver:
# - SSL can be enabled via URL parameter: ?sslmode=require
# - Or via connect_args with ssl context
# - Supabase uses valid SSL certificates, so we can use default context

# Check if URL already contains SSL parameters
database_url = str(settings.SQLALCHEMY_DATABASE_URI)
has_ssl_param = "sslmode=" in database_url or "ssl=" in database_url
is_supabase = "supabase" in database_url.lower()

# Prepare connect_args for SSL and PgBouncer compatibility
# ✅ CRITICAL: Disable prepared statements for PgBouncer transaction pooling mode
# PgBouncer in transaction pooling mode doesn't support prepared statements
connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
}
if (is_supabase or settings.ENVIRONMENT == "production") and not has_ssl_param:
    # ✅ CRITICAL: For asyncpg, create SSL context for Supabase
    # Supabase uses valid SSL certificates, but we disable hostname verification
    # for compatibility with Supabase's pooler endpoint
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False  # Supabase pooler uses different hostname
    ssl_context.verify_mode = ssl.CERT_NONE  # Disable cert verification for compatibility
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.ENVIRONMENT == "development", # ✅ Only echo SQL in development
    future=True,
    pool_pre_ping=True, # ✅ Reconnect if connection is lost (important for Cloud Run)
    # ✅ Cloud Run pool settings: Optimized for stateless, concurrent requests
    # Aligned with Cloud Run concurrency (80 requests/instance)
    pool_size=10,  # Base pool size (allows 10 concurrent DB operations)
    max_overflow=20,  # Allow temporary overflow for traffic spikes (total: 30 connections)
    pool_recycle=3600,  # Recycle connections after 1 hour (prevent stale connections)
    pool_timeout=30,  # Timeout for getting connection from pool
    connect_args=connect_args,  # ✅ SSL configuration for Supabase + PgBouncer compatibility
)

# Membuat Session Factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency Injection untuk FastAPI
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()