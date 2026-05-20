# Planning Document — MWU-NL2-001 Backend
**Phase:** Planning
**MWU Tier:** LOW
**Date:** 2026-05-20
**Source stack:** PHP 5.6 + MySQL (mysql_* extension)
**Target stack:** FastAPI 0.111+ + SQLAlchemy 2.x async + PostgreSQL 15+
**Business Rules:** 10 rules (from comprehension BR catalog)
**Dependencies:** none (MWU-NL2-002-FE is a downstream consumer, not a prerequisite)

---

## §1 — Target Data Model (DDL)

```sql
-- PostgreSQL 15+ DDL for notes table
-- Owned by: MWU-NL2-001 Backend

CREATE TABLE IF NOT EXISTS notes (
    id          SERIAL                      PRIMARY KEY,
    content     VARCHAR(500)                NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- BR-007: all list queries order by created_at DESC; index supports this hot path
CREATE INDEX IF NOT EXISTS idx_notes_created_at_desc
    ON notes (created_at DESC);
```

**Design decisions:**

- `SERIAL` (auto-increment integer) maps cleanly from MySQL `AUTO_INCREMENT INT`. PostgreSQL 15 also supports `GENERATED ALWAYS AS IDENTITY` but `SERIAL` is simpler for SQLAlchemy 2.x compatibility.
- `VARCHAR(500)` character-count limit enforces BR-002 at the DB layer as a defense-in-depth backstop. Pydantic performs the primary enforcement; the DB constraint catches any code path that bypasses validation.
- `TIMESTAMP WITH TIME ZONE` (BR-008): MySQL `DATETIME` had no timezone; PostgreSQL `TIMESTAMPTZ` stores UTC internally and presents in the session timezone. Legacy timestamps are treated as UTC on migration.
- `NOT NULL` on `created_at` with `DEFAULT CURRENT_TIMESTAMP` — value always server-generated, never supplied by the application layer (BR-009).
- No soft-delete column — the legacy schema has none; adding one exceeds scope.
- No user/session FK — system is fully public per BR-006.

---

## §2 — Target ORM / Data Access Models

```python
# app/models.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Note(Base):
    """ORM model for the notes table — owned by MWU-NL2-001."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    # BR-009: DB sets this via server_default; omit init=False (BR-010 / pipeline lesson R-010)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

**Design decisions:**

- `DeclarativeBase` (SQLAlchemy 2.x) — NOT `MappedAsDataclass`. Therefore `init=False` **must not** appear anywhere in `mapped_column()`. This is a hard constraint from pipeline lesson R-010 / BR-BACKEND-010. `server_default=func.now()` is the correct way to express a DB-generated default without `init=False`.
- `Mapped[datetime]` with `DateTime(timezone=True)` — matches `TIMESTAMP WITH TIME ZONE` in §1 exactly. Zero DDL/ORM drift.
- `String(500)` length matches `VARCHAR(500)` in §1 — zero DDL/ORM drift.
- No `__init__` override needed — SQLAlchemy 2.x `DeclarativeBase` generates a clean `__init__(id=..., content=..., created_at=...)`. Because `created_at` has `server_default`, it does not need to be supplied at object construction time; SQLAlchemy populates it after flush/refresh.
- No `relationship()` declarations — no FK associations in this module.

---

## §3 — Validation Schemas / DTOs

```python
# app/schemas.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteCreate(BaseModel):
    """Input schema for POST /api/notes.

    Enforces the BR-003 → BR-001 → BR-002 validation chain in strict order.
    """

    content: str = Field(
        ...,
        description="Note text — trimmed before validation, max 500 characters",
    )

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("content must be a string")

        # BR-003: strip leading/trailing whitespace FIRST; stripped value is stored
        v = v.strip()

        # BR-001: after strip, value must not be empty
        if not v:
            raise ValueError("Note cannot be empty")

        # BR-002: character-count (not byte-count) must not exceed 500
        if len(v) > 500:
            raise ValueError("Note too long (max 500 chars)")

        # Return trimmed value — this is what gets persisted (BR-003 confirmed)
        return v


class NoteResponse(BaseModel):
    """Output schema for all note endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime


class NoteListResponse(BaseModel):
    """Envelope for GET /api/notes."""

    notes: list[NoteResponse]


class ErrorResponse(BaseModel):
    """Standard error payload for 4xx/5xx responses."""

    detail: str
```

**Validator chain rationale:**

- `mode="before"` ensures the validator runs before Pydantic's own type coercion, giving full control over the strip → empty-check → length-check sequence (BR-003 → BR-001 → BR-002).
- The validator returns the trimmed value, not the original, matching confirmed legacy behaviour (Ambiguity #3 resolved: PHP stores the trimmed value).
- `len(v) > 500` counts Unicode characters (code points), not bytes. This is the correct semantic per RISK-BACKEND-006 resolution — character-count is the intended semantic; byte-count was a PHP implementation incidental.
- No auth fields anywhere — BR-006 mandates zero authentication across all schemas.

---

## §4 — API / Interface Design

### Route Overview

| Method | Path | Input | Output | HTTP Status | BRs Enforced |
|--------|------|-------|--------|-------------|--------------|
| GET | /api/notes | none | NoteListResponse | 200 | BR-007 |
| POST | /api/notes | NoteCreate (JSON body) | NoteResponse | 201 | BR-001, BR-002, BR-003 |
| DELETE | /api/notes/{note_id} | note_id: int (path param) | empty body | 204 | BR-004, BR-005 |

All endpoints: no authentication, no authorization headers (BR-006).

---

### GET /api/notes

- **Purpose:** Retrieve all notes, newest first.
- **Auth:** None (BR-006).
- **Query params:** None — no pagination, no filtering, no sort parameter exposed.
- **Response (200):**
  ```json
  {
    "notes": [
      {"id": 3, "content": "third note", "created_at": "2026-05-20T10:00:00+00:00"},
      {"id": 2, "content": "second note", "created_at": "2026-05-19T09:00:00+00:00"}
    ]
  }
  ```
- **BR-007:** `ORDER BY created_at DESC` enforced in service layer — the API never exposes a sort parameter.
- **Empty table:** returns `{"notes": []}` with status 200 — not a 404.

---

### POST /api/notes

- **Purpose:** Create a new note.
- **Auth:** None (BR-006).
- **Request body:**
  ```json
  {"content": "  my new note  "}
  ```
- **Validation chain:** Pydantic `NoteCreate.validate_content` runs BR-003 → BR-001 → BR-002 before the service layer is called.
- **Response (201):**
  ```json
  {"id": 4, "content": "my new note", "created_at": "2026-05-20T10:01:00+00:00"}
  ```
  Note: `content` is the *trimmed* value (BR-003).
- **Error responses:**
  - `422 Unprocessable Entity` — `{"detail": [{"msg": "Note cannot be empty", ...}]}` (BR-001)
  - `422 Unprocessable Entity` — `{"detail": [{"msg": "Note too long (max 500 chars)", ...}]}` (BR-002)
  - FastAPI generates a structured 422 body from `ValidationError` automatically.

---

### DELETE /api/notes/{note_id}

- **Purpose:** Delete a note by ID.
- **Auth:** None (BR-006).
- **Path param:** `note_id: int` — FastAPI coerces and type-validates automatically; non-integer path values return 422 before reaching the service layer.
- **Response (204):** empty body on success.
- **Error responses:**
  - `422 Unprocessable Entity` — FastAPI rejects non-integer `note_id` at path-param coercion.
  - `422 Unprocessable Entity` — Service raises `HTTPException(422)` when `note_id <= 0` (BR-004).
  - `404 Not Found` — `{"detail": "Note not found"}` when delete affects zero rows (BR-005, GAP REMEDIATION).
- **BR-004:** Application layer explicitly checks `note_id <= 0` and raises 422 before issuing SQL.
- **BR-005:** `result.rowcount == 0` check post-DELETE raises 404. This is a confirmed behaviour change from legacy (approved GAP REMEDIATION per comprehension doc).

---

### Router Declaration

```python
# app/router.py — top-level declaration
from fastapi import APIRouter

router = APIRouter(prefix="/api")
# Mounted in main.py: app.include_router(router)
# No dependencies=[Depends(some_auth)] — BR-006 mandates zero auth
```

---

## §5 — Service Layer Design

### NoteService

```python
# app/service.py
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models import Note
from app.schemas import NoteCreate


class NoteService:
    """All business logic for the notes module — stateless, async."""

    @staticmethod
    async def list_notes(db: AsyncSession) -> list[Note]:
        """Return all notes ordered newest-first.

        BR-007: ORDER BY created_at DESC, no user-configurable sort.
        """
        result = await db.execute(
            select(Note).order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_note(db: AsyncSession, data: NoteCreate) -> Note:
        """Persist a new note.

        BR-003/001/002: already enforced by Pydantic before this method is called.
        BR-009: created_at not passed — DB server_default applies.
        RISK-005: flush + refresh to populate auto-generated id and created_at.
        """
        note = Note(content=data.content)
        db.add(note)
        await db.flush()
        await db.refresh(note)  # populates id and server-generated created_at
        return note

    @staticmethod
    async def delete_note(db: AsyncSession, note_id: int) -> None:
        """Delete a note by ID.

        BR-004: note_id must be a positive integer (> 0).
        BR-005: raise 404 when note does not exist (GAP REMEDIATION).
        """
        # BR-004: guard against zero or negative ID before issuing SQL
        if note_id <= 0:
            raise HTTPException(status_code=422, detail="Invalid note ID")

        result = await db.execute(
            delete(Note).where(Note.id == note_id)
        )
        # BR-005: legacy silently returned ok:true — target returns 404
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Note not found")
```

---

### Database Session Dependency

```python
# app/database.py
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
)

async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields one AsyncSession per request.

    RISK-002: replaces the global $conn anti-pattern.
    Transaction committed on clean exit; rolled back on exception.
    """
    async with async_session() as session:
        async with session.begin():
            yield session
```

---

### Application Settings

```python
# app/config.py
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """BR-010: DB credentials read from environment variables with fallbacks."""

    db_host: str = "localhost"
    db_user: str = "postgres"
    db_pass: str = ""
    db_name: str = "notelist"
    db_port: int = 5432
    db_echo: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {"env_prefix": "DB_", "env_file": ".env"}


settings = Settings()
```

---

### Router Implementation

```python
# app/router.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import NoteCreate, NoteListResponse, NoteResponse
from app.service import NoteService

router = APIRouter(prefix="/api")


@router.get("/notes", response_model=NoteListResponse)
async def list_notes(db: AsyncSession = Depends(get_db)) -> NoteListResponse:
    """BR-007: newest-first; BR-006: no auth."""
    notes = await NoteService.list_notes(db)
    return NoteListResponse(notes=notes)


@router.post("/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    """BR-001/002/003 enforced by Pydantic; BR-006: no auth."""
    note = await NoteService.create_note(db, data)
    return NoteResponse.model_validate(note)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """BR-004/005 enforced in service layer; BR-006: no auth."""
    await NoteService.delete_note(db, note_id)
    return Response(status_code=204)
```

---

### Main Application

```python
# app/main.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router import router

app = FastAPI(title="Note List API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(router)
```

---

### Service Layer Method Summary

| Method | BR(s) | Transaction scope | Raises |
|--------|-------|-------------------|--------|
| `list_notes(db)` | BR-007 | read-only SELECT | SQLAlchemyError → 500 (unhandled, FastAPI default) |
| `create_note(db, data)` | BR-003/001/002 (Pydantic), BR-009 (server default) | write + flush + refresh | SQLAlchemyError → 500 |
| `delete_note(db, note_id)` | BR-004, BR-005 | write | HTTPException 422 (bad ID), HTTPException 404 (not found), SQLAlchemyError → 500 |

---

## §6 — Risk Register and Mitigations

### RISK-BACKEND-001: HIGH — mysql_* Extension Removal

**Source behaviour:** All data access used `mysql_connect`, `mysql_query`, `mysql_fetch_assoc`, `mysql_real_escape_string`. These functions do not exist in Python. String concatenation was the parameterisation mechanism.

```php
// Legacy pattern
$content = mysql_real_escape_string($content);
$query = "INSERT INTO notes (content) VALUES ('$content')";
mysql_query($query, $conn);
```

**Target implementation:**
```python
# CORRECT — ORM insert, no string concatenation, no injection surface
note = Note(content=data.content)
db.add(note)
await db.flush()
await db.refresh(note)

# CORRECT — parameterized SELECT
result = await db.execute(select(Note).order_by(Note.created_at.desc()))

# CORRECT — parameterized DELETE
result = await db.execute(delete(Note).where(Note.id == note_id))
```

**Do NOT use:** `text()` with f-string interpolation, any `mysql_real_escape_string` equivalent, or manual SQL string construction.

**Validation approach:** SQL injection test vectors (e.g., `content = "'; DROP TABLE notes; --"`) must be stored as literal text, never executed as SQL. Verified in §9 injection test cases.

---

### RISK-BACKEND-002: MEDIUM — Global Connection State

**Source behaviour:**
```php
// db.php
global $conn;
$conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
```
Module-level connection shared across all function calls within a PHP request.

**Target implementation:**
```python
# CORRECT — per-request session via FastAPI dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        async with session.begin():
            yield session

# In router — session scoped to the HTTP request lifetime
@router.get("/notes")
async def list_notes(db: AsyncSession = Depends(get_db)):
    ...
```

**Do NOT use:** Module-level `AsyncSession` instance, `app.state.db`, or any pattern that shares a session across concurrent requests.

**Validation approach:** Concurrent request integration tests must show independent transactions with no cross-request state contamination.

---

### RISK-BACKEND-003: HIGH — Raw SQL Concatenation (SQL Injection)

**Source behaviour:** Even with `mysql_real_escape_string`, the pattern is architecturally unsafe — any missed escape call creates an injection vector. Legacy code had this gap.

**Target implementation:**
```python
# All three data operations use ORM — zero manual SQL construction
# list: select(Note).order_by(Note.created_at.desc())
# insert: Note(content=data.content) + db.add(note)
# delete: delete(Note).where(Note.id == note_id)
```

**Do NOT use:** `text(f"INSERT INTO notes (content) VALUES ('{data.content}')")` or any f-string in a SQL expression.

**Validation approach:** Injection payloads in §9 must return 201 with the payload stored as literal text, verifiable by fetching the created note and asserting `content == payload_string`.

---

### RISK-BACKEND-004: MEDIUM — DELETE via HTTP GET

**Source behaviour:** `GET /?delete=3` triggered a deletion — violates HTTP idempotency/safety semantics.

**Target implementation:**
```python
@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    await NoteService.delete_note(db, note_id)
    return Response(status_code=204)
```

**Coordination point:** MWU-NL2-002-FE must send `DELETE /api/notes/{id}`. Comprehension doc records this as FULLY_VALIDATED.

**Validation approach:** `GET /api/notes/3` must return 405 Method Not Allowed, not perform a deletion.

---

### RISK-BACKEND-005: LOW — mysql_insert_id Replacement

**Source behaviour:** PHP used `mysql_insert_id()` to retrieve the auto-generated PK after insert.

**Target implementation:**
```python
note = Note(content=data.content)
db.add(note)
await db.flush()    # issues INSERT; SQLAlchemy reads back RETURNING id
await db.refresh(note)  # re-reads all server-generated columns
return note  # note.id and note.created_at are now populated
```

**Do NOT use:** `text("SELECT lastval()")`, raw `RETURNING` clause in a `text()` call.

**Validation approach:** POST /api/notes must return a response with a valid positive integer `id` and a non-null `created_at`.

---

### RISK-BACKEND-006: LOW — strlen Byte vs Character Count

**Source behaviour:** PHP `strlen("café")` returns 5 (counts bytes, not characters — "é" is 2 bytes in UTF-8). A 500-byte string may be fewer than 500 characters.

**Target implementation:**
```python
# CORRECT — character count (Unicode code points)
if len(v) > 500:
    raise ValueError("Note too long (max 500 chars)")
```
`VARCHAR(500)` in PostgreSQL also counts characters. For ASCII-only content (dominant use case), behaviour is identical. For multi-byte Unicode, Python/PG behaviour is more permissive than legacy PHP.

**Resolution:** Character-count is the correct semantic per RISK-BACKEND-006. Do NOT implement byte-length checking to match PHP behaviour.

**Validation approach:** Test with a 500-character string containing multi-byte Unicode (e.g., 250 two-byte characters) — must be accepted. Test with 501 characters — must be rejected.

---

### RISK-BACKEND-007: MEDIUM — No Row-Not-Found Check on Delete

**Source behaviour:** Legacy `delete_note()` executed a DELETE query and returned `{"ok": true}` regardless of whether any row was affected.

**Target implementation:**
```python
result = await db.execute(delete(Note).where(Note.id == note_id))
if result.rowcount == 0:
    raise HTTPException(status_code=404, detail="Note not found")
```

This is a deliberate behaviour change (GAP REMEDIATION, Ambiguity #2 approved per comprehension doc).

**Validation approach:** `DELETE /api/notes/99999` against an empty or non-matching table must return 404.

---

### RISK-BACKEND-008: LOW — DATETIME to TIMESTAMPTZ

**Source behaviour:** MySQL `DATETIME` stores local time with no timezone metadata. Legacy deployment treated all times as UTC implicitly.

**Target implementation:**
```python
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),  # maps to TIMESTAMP WITH TIME ZONE
    server_default=func.now(),
    nullable=False,
)
```
All legacy seed data timestamps treated as UTC on migration (see §8).

**Validation approach:** `created_at` in API responses must include timezone offset (e.g., `"2026-05-20T10:00:00+00:00"`, not `"2026-05-20T10:00:00"`).

---

### RISK-BACKEND-009: MEDIUM — No Error Handling on mysql_query Failures

**Source behaviour:** `mysql_query()` returned `false` on failure; legacy code did not check this return value, silently ignoring DB errors.

**Target implementation:** SQLAlchemy raises `SQLAlchemyError` on failure. FastAPI's default exception handler converts unhandled exceptions to 500. No explicit try/except needed for general DB failures — FastAPI handles them correctly.

For constraint violations (e.g., content exceeding `VARCHAR(500)` at DB level), Pydantic prevents the condition from reaching the DB. No specific handler is needed.

**Validation approach:** Integration test with DB unavailable must return 500, not hang or return 200 with partial data.

---

### RISK-BACKEND-010: HIGH — init=False in mapped_column() (PIPELINE LESSON R-010)

**Source behaviour:** N/A — this is a target-stack trap, not a legacy pattern.

**Target implementation:**
```python
# CORRECT — server_default only, init=False omitted entirely
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
    nullable=False,
)

# WRONG — raises InvalidRequestError at mapper configuration time on DeclarativeBase
# created_at: Mapped[datetime] = mapped_column(..., init=False)
```

`init=False` is only valid on `MappedAsDataclass`. On `DeclarativeBase` it raises `sqlalchemy.orm.exc.InvalidRequestError` at application startup before any request is served.

**Validation approach:** `python -c "from app.models import Note"` must exit 0 without any SQLAlchemy mapper errors.

---

## §7 — Cross-Module Stubs

N/A — no cross-module dependencies require Python stub classes.

The three cross-module touchpoints with MWU-NL2-002-FE (BR-004, BR-005, BR-007) are REST API contracts. The backend publishes HTTP endpoints; the frontend consumes them over HTTP. The backend does not import or call any frontend Python module. No stub classes are needed.

MWU-NL2-002-FE is already FULLY_VALIDATED and will integrate via the REST API contract defined in §4.

---

## §8 — Data Migration

### Column Type Conversion Map

| Column | MySQL Source Type | PostgreSQL Target Type | Conversion Notes |
|--------|-------------------|----------------------|------------------|
| `id` | `INT AUTO_INCREMENT` | `SERIAL` (INTEGER) | Auto-increment semantics identical; sequence reset required post-import |
| `content` | `VARCHAR(500) CHARACTER SET utf8` | `VARCHAR(500)` | MySQL 3-byte utf8 → PostgreSQL 4-byte UTF-8; all existing content is valid |
| `created_at` | `DATETIME` (no TZ) | `TIMESTAMP WITH TIME ZONE` | Legacy values treated as UTC; stored as UTC in TIMESTAMPTZ |

### Sentinel / Magic Value Conversions

None. The notes table has no sentinel values, no soft-delete flags, no boolean integers, no NULL-as-sentinel patterns.

### Encoding and Collation

MySQL `CHARACTER SET utf8` is MySQL's 3-byte UTF-8 variant — it cannot store 4-byte characters (emoji, supplementary CJK). PostgreSQL uses true 4-byte UTF-8 by default. The migration is safe: all content valid in MySQL `utf8` is valid in PostgreSQL `utf8`. After migration, new content can include 4-byte characters.

```sql
-- Database creation with explicit UTF-8 collation
CREATE DATABASE notelist
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;
```

### Migration Script (MySQL → PostgreSQL)

```sql
-- Step 1: Create schema (run §1 DDL)
-- (CREATE TABLE notes ...; CREATE INDEX ...)

-- Step 2: Bulk-import from MySQL
-- Recommended tool: pgloader
--
--   pgloader mysql://legacy_user:pass@legacy_host/notelist_mysql \
--             postgresql://pg_user:pass@pg_host/notelist
--
-- pgloader handles automatically:
--   - DATETIME → TIMESTAMPTZ (treats source as UTC)
--   - 3-byte utf8 charset upgrade to PostgreSQL UTF-8
--   - AUTO_INCREMENT → SERIAL sequence value carry-over

-- Step 3: After bulk import, reset the SERIAL sequence to prevent PK collisions
SELECT setval('notes_id_seq', COALESCE((SELECT MAX(id) FROM notes), 0));

-- Step 4: Verify row counts match
-- Run on PostgreSQL:  SELECT COUNT(*) FROM notes;
-- Run on MySQL:       SELECT COUNT(*) FROM notes;
-- Counts must be equal before cutting over.

-- Step 5: Verify sample content round-trip
-- SELECT id, content, created_at FROM notes ORDER BY id LIMIT 10;
-- Compare against MySQL source.
```

If deploying fresh with no legacy data migration, only the §1 DDL is required.

---

## §9 — Test Strategy

### Test Infrastructure

```python
# tests/conftest.py
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/notelist_test"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
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
            await session.rollback()  # isolate each test — no state leaks


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_notes(db_session: AsyncSession):
    from app.models import Note

    notes = [Note(content=f"seed note {i}") for i in range(3)]
    db_session.add_all(notes)
    await db_session.flush()
    for n in notes:
        await db_session.refresh(n)
    return notes
```

---

### Test Case Table

| BR ID | Test Type | Scenario | Expected Result |
|-------|-----------|----------|-----------------|
| BR-001 | Unit | `NoteCreate(content="")` | `ValidationError`, message "Note cannot be empty" |
| BR-001 | Unit | `NoteCreate(content="   ")` | `ValidationError` — spaces strip to empty |
| BR-001 | Integration | `POST /api/notes` `{"content": ""}` | 422, detail contains "Note cannot be empty" |
| BR-002 | Unit | `NoteCreate(content="x" * 501)` | `ValidationError`, message "Note too long (max 500 chars)" |
| BR-002 | Unit | `NoteCreate(content="x" * 500)` | Valid — boundary accepted |
| BR-002 | Integration | `POST /api/notes` with 501-char content | 422, detail contains "Note too long" |
| BR-002 | Integration | `POST /api/notes` with 500-char content | 201 |
| BR-003 | Unit | `NoteCreate(content="  hello  ")` | Returns with `content == "hello"` |
| BR-003 | Integration | `POST /api/notes` `{"content": "  hello world  "}` | 201, response `content == "hello world"` |
| BR-003 | Unit | Chain: `"   "` → strip → empty → reject | `ValidationError` "Note cannot be empty" |
| BR-004 | Integration | `DELETE /api/notes/0` | 422, "Invalid note ID" |
| BR-004 | Integration | `DELETE /api/notes/-5` | 422, "Invalid note ID" |
| BR-004 | Integration | `DELETE /api/notes/abc` | 422 (FastAPI path-param type coercion) |
| BR-005 | Integration | `DELETE /api/notes/99999` (non-existent) | 404, "Note not found" |
| BR-005 | Integration | `DELETE /api/notes/{valid_id}` (existing) | 204 |
| BR-006 | Integration | All three endpoints called without Authorization header | 200 / 201 / 204 — no auth error |
| BR-006 | Static | Router has no auth dependencies | `router.dependencies == []` |
| BR-007 | Integration | Create notes A, B, C in order; GET /api/notes | Returns [C, B, A] (newest first) |
| BR-007 | Integration | Single note; GET /api/notes | Returns list with one item |
| BR-007 | Integration | Empty table; GET /api/notes | Returns `{"notes": []}` with 200 |
| BR-008 | Integration | POST note with emoji content; GET it back | Round-trips correctly |
| BR-008 | Integration | POST note with 500 2-byte Unicode chars; GET | 201 accepted (character count, not byte count) |
| BR-009 | Integration | POST /api/notes; inspect response | `created_at` populated, is timezone-aware |
| BR-009 | Unit | `Note(content="x")` — do not pass `created_at` | Instantiates without error |
| BR-010 (R-010) | Unit | `from app.models import Note` | No `InvalidRequestError` at import |

---

### Happy Path Tests

```python
# tests/test_notes_api.py

async def test_list_notes_empty(client):
    response = await client.get("/api/notes")
    assert response.status_code == 200
    assert response.json() == {"notes": []}


async def test_create_note(client):
    r = await client.post("/api/notes", json={"content": "hello"})
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "hello"
    assert isinstance(data["id"], int)
    assert data["id"] > 0
    assert "created_at" in data


async def test_list_notes_after_create(client):
    await client.post("/api/notes", json={"content": "first"})
    r = await client.get("/api/notes")
    assert r.status_code == 200
    assert len(r.json()["notes"]) == 1


async def test_delete_note(client, seed_notes):
    note_id = seed_notes[0].id
    r = await client.delete(f"/api/notes/{note_id}")
    assert r.status_code == 204
    r2 = await client.get("/api/notes")
    ids = [n["id"] for n in r2.json()["notes"]]
    assert note_id not in ids
```

---

### BR Violation Tests

```python
async def test_empty_content_rejected(client):
    r = await client.post("/api/notes", json={"content": ""})
    assert r.status_code == 422


async def test_whitespace_only_rejected(client):
    r = await client.post("/api/notes", json={"content": "   "})
    assert r.status_code == 422


async def test_too_long_content_rejected(client):
    r = await client.post("/api/notes", json={"content": "a" * 501})
    assert r.status_code == 422


async def test_exactly_500_chars_accepted(client):
    r = await client.post("/api/notes", json={"content": "x" * 500})
    assert r.status_code == 201


async def test_delete_zero_id(client):
    r = await client.delete("/api/notes/0")
    assert r.status_code == 422


async def test_delete_negative_id(client):
    r = await client.delete("/api/notes/-1")
    assert r.status_code == 422


async def test_delete_nonexistent_note(client):
    r = await client.delete("/api/notes/999999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Note not found"
```

---

### Edge Cases from Risk Register

```python
async def test_note_ordering_newest_first(client):
    """BR-007: ORDER BY created_at DESC is non-negotiable."""
    for content in ["first", "second", "third"]:
        await client.post("/api/notes", json={"content": content})
    r = await client.get("/api/notes")
    notes = r.json()["notes"]
    assert notes[0]["content"] == "third"
    assert notes[1]["content"] == "second"
    assert notes[2]["content"] == "first"


async def test_trim_is_stored_not_display_only(client):
    """BR-003: trimmed value persisted, confirmed by round-trip."""
    r = await client.post("/api/notes", json={"content": "  padded  "})
    assert r.status_code == 201
    assert r.json()["content"] == "padded"
    note_id = r.json()["id"]
    r2 = await client.get("/api/notes")
    note = next(n for n in r2.json()["notes"] if n["id"] == note_id)
    assert note["content"] == "padded"


async def test_unicode_4byte_content(client):
    """BR-008: 4-byte UTF-8 (emoji) must round-trip correctly."""
    r = await client.post("/api/notes", json={"content": "Hello 🌍"})
    assert r.status_code == 201
    assert r.json()["content"] == "Hello 🌍"


async def test_multibyte_character_count_not_byte_count(client):
    """BR-002/RISK-006: 500 two-byte characters must be accepted (character semantics)."""
    content = "é" * 500  # each 'é' is 2 bytes in UTF-8 — 1000 bytes total
    r = await client.post("/api/notes", json={"content": content})
    assert r.status_code == 201


async def test_created_at_timezone_aware(client):
    """BR-009/RISK-008: created_at must include timezone offset."""
    r = await client.post("/api/notes", json={"content": "tz check"})
    created_at = r.json()["created_at"]
    assert "+" in created_at or created_at.endswith("Z")


async def test_no_auth_required_on_all_endpoints(client):
    """BR-006: CRITICAL — no auth on any endpoint."""
    r = await client.get("/api/notes")
    assert r.status_code == 200
    r = await client.post("/api/notes", json={"content": "auth test"})
    assert r.status_code == 201
    note_id = r.json()["id"]
    r = await client.delete(f"/api/notes/{note_id}")
    assert r.status_code == 204


async def test_sql_injection_payload_stored_as_literal(client):
    """RISK-003: injection payload must be stored as text, not executed."""
    payload = "'; DROP TABLE notes; --"
    r = await client.post("/api/notes", json={"content": payload})
    assert r.status_code == 201
    assert r.json()["content"] == payload
    # Verify table still exists
    r2 = await client.get("/api/notes")
    assert r2.status_code == 200


async def test_mapper_init_no_error():
    """RISK-010/BR-010: DeclarativeBase ORM model must not raise InvalidRequestError."""
    from app.models import Note  # import triggers mapper configuration
    note = Note(content="mapper check")
    assert note.content == "mapper check"
```
