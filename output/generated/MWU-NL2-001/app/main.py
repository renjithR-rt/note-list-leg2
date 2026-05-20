"""
FastAPI application entrypoint.

Registers the notes router and manages DB table creation during lifespan.
BR-006: no auth middleware, no session middleware, no API key middleware.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.db.session import create_tables
from app.modules.backend.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create tables on startup (idempotent — uses CREATE TABLE IF NOT EXISTS)."""
    await create_tables()
    yield


app = FastAPI(
    title="Note List API",
    version="2.0.0",
    description="Note List migration — MWU-NL2-001 backend.",
    lifespan=lifespan,
)

# BR-006: no auth router, no middleware for auth/sessions/API keys
app.include_router(router)