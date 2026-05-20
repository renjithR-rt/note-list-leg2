from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# BR-010: Database credentials from environment with safe defaults
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://notelist:notelist@localhost:5432/notelist_modern",
)

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": False},  # Required for local/Docker PostgreSQL on Windows
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, 
    expire_on_commit=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency - yields one AsyncSession per request.
    
    RISK-002: replaces the global $conn anti-pattern.
    Transaction committed on clean exit; rolled back on exception.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session