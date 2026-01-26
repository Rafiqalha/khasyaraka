"""
SQLAlchemy Base

Centralized Base class for all SQLAlchemy models.
All models must inherit from this Base to be detected by Alembic.

NOTE: Model imports are NOT done here to avoid circular imports.
Instead, import all models in alembic/env.py for migration detection.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()