from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.session import get_db_session
from app.main import app
from app.modules.notes.models import Base, Note

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://notelist:notelist@localhost:5436/notes_test",
)


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"ssl": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    async_sess = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_sess() as session:
        async with session.begin():
            yield session
            await session.rollback()  # isolate each test - no state leaks


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_notes(db_session: AsyncSession):
    notes = [Note(content=f"seed note {i}") for i in range(3)]
    db_session.add_all(notes)
    await db_session.flush()
    for n in notes:
        await db_session.refresh(n)
    return notes