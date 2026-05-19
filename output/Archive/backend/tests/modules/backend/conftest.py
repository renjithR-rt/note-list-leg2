"""Test configuration for backend module."""

import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.base import get_db_session
from app.modules.backend.models import Base

# Test database configuration — port 5436 is the Docker-mapped host port
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5436/notelist_test",
)

# NullPool prevents connection reuse across event loop scopes.
# pytest-asyncio 0.23+ gives session-scoped and function-scoped fixtures
# different event loops; asyncpg connections can't cross event loops, so
# pooled connections from create_test_schema would cause "another operation
# is in progress" when reused in db_session. NullPool creates/discards a
# fresh connection for every checkout.
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestAsyncSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_schema():
    """Create all tables before test session starts."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup after all tests complete
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    """Provide isolated database session for each test."""
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()  # each test gets a clean slate

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Provide HTTP client with test database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()