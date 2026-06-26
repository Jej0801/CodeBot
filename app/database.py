"""
Database configuration and session management.

This module provides:
- Async SQLAlchemy engine
- Async session factory
- Database dependency for FastAPI routes
- Base class for all ORM models
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

# Create async engine
# echo=True logs all SQL statements (useful for debugging, disable in production)
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug_mode,
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Additional connections when pool is exhausted
)

# Session factory
# expire_on_commit=False prevents attributes from being expired after commit
# This is important for async contexts where we might access objects after commit
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all ORM models
# All models will inherit from this
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database dependency for FastAPI routes.

    Usage in routes:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()

    This is a dependency injection pattern. FastAPI will:
    1. Call this function
    2. Yield a database session
    3. Inject it into the route
    4. Close the session when the request completes (even if an error occurs)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.

    This creates all tables defined in models.
    In production, we'll use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.

    Used by health check endpoint.
    Returns True if connection successful, False otherwise.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception:
        return False
