# Re-export the main Base class from db.py for recommendation models
# This ensures all models share the same metadata for Alembic migrations
from db import Base

__all__ = ["Base"]