"""
Structured Logging Configuration

Provides centralized logging setup with structured output.
"""

import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure application-wide logging.
    
    Sets up:
    - Console handler with structured format
    - File handler (if log directory exists)
    - Log level based on environment
    """
    # Determine log level based on environment
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # File handler (optional, for production)
    file_handler = None
    log_dir = Path("logs")
    if log_dir.exists() or settings.ENVIRONMENT == "production":
        if not log_dir.exists():
            log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / f"scout_os_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    if file_handler:
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    
    Example:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"user_id": 123})
    """
    return logging.getLogger(name)


class RequestLogger:
    """
    Middleware-friendly request logger.
    Provides structured logging for HTTP requests.
    """
    
    def __init__(self):
        self.logger = get_logger("http.request")
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: Optional[str] = None,
        user_id: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        Log HTTP request with structured data.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            client_ip: Client IP address
            user_id: Authenticated user ID (if any)
            **kwargs: Additional context
        """
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }
        
        if client_ip:
            log_data["client_ip"] = client_ip
        if user_id:
            log_data["user_id"] = user_id
        if kwargs:
            log_data.update(kwargs)
        
        # Log level based on status code
        if status_code >= 500:
            self.logger.error(f"{method} {path} - {status_code}", extra=log_data)
        elif status_code >= 400:
            self.logger.warning(f"{method} {path} - {status_code}", extra=log_data)
        else:
            self.logger.info(f"{method} {path} - {status_code}", extra=log_data)


# Initialize request logger singleton
request_logger = RequestLogger()
