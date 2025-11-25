"""
Database module for authentication.
Currently using in-memory storage, can be extended to use SQLAlchemy.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator


@asynccontextmanager
async def get_test_database() -> AsyncGenerator[None, None]:
    """
    Get test database session (currently a no-op with in-memory storage).
    
    Yields:
        None (placeholder for actual database session)
    """
    # Since we're using in-memory UserRepository, no database setup needed
    yield None


__all__ = ["get_test_database"]
