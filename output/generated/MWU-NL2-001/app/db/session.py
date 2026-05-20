"""
Async database engine and session factory.

RISK-008: DATABASE_URL is required. No hardcoded fallback credentials.
          If the env var is absent the process raises KeyError at import
          time — fail-fast, not silent misconfiguration.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.modules.backend.models import Base

# RISK-008: KeyError if DATABASE_URL is missing — intentional fail-fast.
# Acceptable values: postgresql+asyncpg://user:pass@host/db
DATABASE_URL: str = os.environ["DATABASE_URL"]

engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # Set True only in local dev via env var if desired
    pool_pre_ping=True,  # Recycles stale connections after DB restart
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Allows reading attributes after commit without re-query
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async SQLAlchemy session.
    Session is committed/rolled-back by the caller (service layer).
    Connection is always returned to the pool on exit.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables() -> None:
    """Create all tables defined in Base.metadata. Called during app lifespan startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)