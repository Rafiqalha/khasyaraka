from arq.connections import RedisSettings
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

async def startup(ctx):
    logger.info("🚀 Arq Worker Started")
    # Initialize DB pool here if needed for worker context
    # from app.db.session import engine
    # ctx['db_engine'] = engine

async def shutdown(ctx):
    logger.info("🛑 Arq Worker Stopped")
    # Close DB pool
    # await ctx['db_engine'].dispose()

# Import job functions
from app.services.user_service import sync_hearts_db

class WorkerSettings:
    """
    Arq Worker Configuration
    
    Commands to run:
    - arq app.core.worker.WorkerSettings
    """
    # Redis Connection
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL_COMPUTED)
    
    # Global Job Functions
    functions = [sync_hearts_db]
    
    # Startup/Shutdown
    on_startup = startup
    on_shutdown = shutdown
    
    # Error Handling
    max_jobs = 10
    job_timeout = 60 # seconds
