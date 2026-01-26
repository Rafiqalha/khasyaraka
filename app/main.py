"""
Scout OS Backend - Main Application

Production-ready FastAPI application with:
- Centralized exception handling
- Structured logging
- Request/response middleware
- Standard API response format
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import setup_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware
from app.core.response import success, error
from app.api.router import api_router

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Scout OS Backend API - Production Ready",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle all AppException instances.
    Converts domain exceptions to standard API error responses.
    """
    logger.warning(
        f"AppException: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error(
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details
        )
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions.
    Prevents sensitive error details from leaking in production.
    """
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    # In production, don't expose internal error details
    if settings.ENVIRONMENT == "production":
        message = "An internal error occurred"
    else:
        message = f"Internal error: {str(exc)}"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error(
            message=message,
            error_code="INTERNAL_SERVER_ERROR"
        )
    )


# 5. ROUTER REGISTRATION
app.include_router(api_router, prefix=settings.API_V1_STR)

# 6. HEALTH CHECK ENDPOINT
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return success(
        data={
            "message": "Scout OS Backend is Running",
            "architecture": "Modular Architecture",
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0"
        },
        message="API is healthy"
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Detailed health check endpoint.
    
    ✅ Production Hardened:
    - Non-blocking async operations
    - Timeout protection (5s per check)
    - Does not block event loop
    - Returns structured JSON with status
    """
    import asyncio
    from app.db.session import engine
    from sqlalchemy import text
    
    # Check database connection (with timeout)
    db_status = "disconnected"
    try:
        async with asyncio.timeout(5.0):  # 5 second timeout
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.scalar()
                db_status = "connected"
    except asyncio.TimeoutError:
        logger.error("Database health check timeout")
        db_status = "timeout"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)[:50]}"  # Truncate long errors
    
    # Check Redis connection (with timeout)
    redis_status = "disconnected"
    try:
        async with asyncio.timeout(5.0):  # 5 second timeout
            from app.core.redis import get_redis
            redis_client = await get_redis()
            await redis_client.ping()
            redis_status = "connected"
    except asyncio.TimeoutError:
        logger.error("Redis health check timeout")
        redis_status = "timeout"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = f"error: {str(e)[:50]}"  # Truncate long errors
    
    # Determine overall health
    is_healthy = db_status == "connected" and redis_status == "connected"
    
    return success(
        data={
            "status": "healthy" if is_healthy else "degraded",
            "environment": settings.ENVIRONMENT,
            "database": db_status,
            "redis": redis_status,
        },
        message="Service health check completed"
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Starting {settings.PROJECT_NAME} in {settings.ENVIRONMENT} mode")
    
    # ✅ CRITICAL: Verify training data exists
    # This ensures core training data is seeded before accepting requests
    try:
        from app.db.session import SessionLocal
        from app.modules.training.verification import verify_training_data
        
        async with SessionLocal() as db:
            verification_result = await verify_training_data(db)
            
            if not verification_result.get("is_ready"):
                logger.error(
                    "⚠️ TRAINING DATA NOT READY - Core training data missing or incomplete",
                    extra=verification_result
                )
                logger.error(
                    "⚠️ Users will not be able to access training paths. "
                    "Run migration '89f3741b3905_seed_training_data_puk_section' to seed data."
                )
            else:
                logger.info(
                    "✅ Training data verification passed - System ready",
                    extra=verification_result
                )
    except Exception as e:
        logger.error(f"❌ Failed to verify training data on startup: {e}", exc_info=True)
        # Don't fail startup - log error but continue
        # In production, consider failing fast if training data is critical


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
    # Close Redis connection
    from app.core.redis import close_redis
    await close_redis()