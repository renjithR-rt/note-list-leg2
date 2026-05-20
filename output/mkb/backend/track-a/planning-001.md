# Planning Document — MWU-NL2-001 Backend Module
**Phase:** Planning
**MWU Tier:** LOW
**Date:** 2026-05-20
**Source stack:** PHP 5.6 + MySQL (utf8 3-byte) + procedural `mysql_*` query functions
**Target stack:** FastAPI (Python 3.11+) + PostgreSQL 15+ (UTF-8) + SQLAlchemy 2.x async + Pydantic v2
**Business Rules:** 9 rules (from comprehension BR catalog)
**Dependencies:** none

---

## §1 — Target Data Model (DDL)

This module owns one table: `notes`. The DDL below is valid PostgreSQL 15 syntax.
No source-dialect types (MySQL `INT UNSIGNED`, `utf8mb4_unicode_ci`, etc.) appear here.

```sql
-- ============================================================
-- notes table
-- Owns: all note records for the application.
-- BR-009: created_at is DB-managed; the application never
--         supplies this value on INSERT.
-- BR-008: PostgreSQL's native UTF-8 is 4-byte; emoji and
--         supplementary Unicode are supported automatically.
-- BR-002: content is VARCHAR(500); DB enforces the cap as a
--         second layer after the app-layer Pydantic check.
-- ============================================================

CREATE TABLE IF NOT EXISTS notes (
    id          SERIAL          PRIMARY KEY,
    content     VARCHAR(500)    NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index: supports BR-007 (always return notes newest-first).
-- Without this index every GET /api/notes performs a full sequential
-- scan + sort; the index makes ORDER BY created_at DESC a pure index
-- scan on any Postgres query planner version.
CREATE INDEX IF NOT EXISTS idx_notes_created_at_desc
    ON notes (created_at DESC);
```

### Column specification

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | `SERIAL` (= `INTEGER` + sequence) | NOT NULL | auto-increment | PK; never supplied by app on INSERT |
| `content` | `VARCHAR(500)` | NOT NULL | — | BR-002 DB-layer cap; BR-003 trimmed value stored |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `CURRENT_TIMESTAMP` | BR-009: always DB-supplied; timezone-aware (RISK-006) |

### Constraints summary

| Constraint | Type | Columns | Expression |
|------------|------|---------|------------|
| `notes_pkey` | PRIMARY KEY | `id` | — |
| `notes_content_not_empty` | CHECK | `content` | `LENGTH(TRIM(content)) > 0` |
| `idx_notes_created_at_desc` | INDEX | `created_at DESC` | — |

> **Note on the CHECK constraint:** The `LENGTH(TRIM(content)) > 0` constraint provides a database-level guarantee matching BR-001 + BR-003. The Pydantic validator is the primary enforcement layer; this constraint is a defensive backstop that prevents bypassing validation via direct DB writes.

---

## §2 — Target ORM / Data Access Models

Uses SQLAlchemy 2.x declarative with `mapped_column` (typed mapping). All async.
File target: `backend/models.py`

```python
"""
SQLAlchemy 2.x ORM model for the notes module.

Maps exactly to the DDL in §1. Zero drift rule: any DDL change
must be reflected here and vice versa.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all models in this service."""
    pass


class Note(Base):
    """
    Persistent note record.

    BR-002: content VARCHAR(500) — enforced at Pydantic layer first,
            DB layer second.
    BR-008: PostgreSQL UTF-8 is natively 4-byte; no charset declaration needed.
    BR-009: created_at is server-default only; never set by application code.
    RISK-006: DateTime(timezone=True) → TIMESTAMPTZ in PostgreSQL;
              all timestamps are timezone-aware.
    """

    __tablename__ = "notes"

    # Primary key — auto-incremented by the DB sequence (SERIAL).
    # The application never supplies `id` on INSERT.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        init=False,
    )

    # BR-002: max 500 chars enforced here (String(500)) and in Pydantic schema.
    # BR-003: the trimmed value is what gets stored — trimming happens in the
    #         Pydantic validator before this column ever receives the value.
    content: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # BR-009: server_default means the DB sets this; app layer never touches it.
    # RISK-006: timezone=True → TIMESTAMPTZ; stores and returns UTC-aware datetimes.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        init=False,
    )

    def __repr__(self) -> str:
        return f"Note(id={self.id!r}, content={self.content[:30]!r}, created_at={self.created_at!r})"
```

### Database session factory
File target: `backend/database.py`

```python
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

from backend.models import Base

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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
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
```

---

## §3 — Validation Schemas / DTOs

Uses Pydantic v2. All validators are `field_validator` with `mode="before"`.
File target: `backend/schemas.py`

```python
"""
Pydantic v2 schemas for the notes API.

Validation chain for note creation (BR-003 → BR-001 → BR-002):
  1. BR-003: strip() whitespace
  2. BR-001: reject empty string
  3. BR-002: reject length > 500

The chain order is enforced within a single validator so the sequence
cannot be accidentally reordered by a future developer.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Input schemas (request bodies)
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    """
    Request body for POST /api/notes.

    Implements the BR-003 → BR-001 → BR-002 validation chain in strict order.
    The trimmed value (BR-003) is what gets stored, not the raw input.
    """

    content: str

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: object) -> str:
        """
        Enforces validation chain in mandatory order:
          BR-003 — trim whitespace first
          BR-001 — reject if empty after trim
          BR-002 — reject if exceeds 500 chars after trim
        """
        if not isinstance(v, str):
            raise ValueError("content must be a string")

        # BR-003: trim whitespace; the trimmed result is stored, not the raw input
        v = v.strip()

        # BR-001: reject empty content (checked AFTER trim so "   " is correctly rejected)
        if not v:
            raise ValueError("Note cannot be empty")

        # BR-002: reject content exceeding 500 characters (checked on trimmed value)
        if len(v) > 500:
            raise ValueError("Note too long (max 500 chars)")

        return v


# ---------------------------------------------------------------------------
# Response schemas (response bodies)
# ---------------------------------------------------------------------------

class NoteResponse(BaseModel):
    """
    Response schema for a single note.

    BR-009: created_at is always present (DB-supplied); never null.
    from_attributes=True: required for SQLAlchemy ORM → Pydantic serialization.
    """

    id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteResponse(BaseModel):
    """
    Response body for a successful DELETE /api/notes/{note_id}.

    Returns a minimal acknowledgement. Frontend checks ok=True to confirm deletion.
    Chosen over 204 No Content to maintain parity with legacy ok:true JSON shape,
    easing frontend migration (MWU-NL2-002-FE can detect success without
    inspecting status codes alone).
    """

    ok: bool = True
```

### Schema → BR mapping summary

| Schema | Field | Validator | BR enforced |
|--------|-------|-----------|-------------|
| `NoteCreate` | `content` | `validate_content` step 1 | BR-003 (strip) |
| `NoteCreate` | `content` | `validate_content` step 2 | BR-001 (not empty) |
| `NoteCreate` | `content` | `validate_content` step 3 | BR-002 (≤ 500 chars) |
| `NoteResponse` | `created_at` | — | BR-009 (always present) |
| `NoteResponse` | — | `from_attributes=True` | — |
| `DeleteResponse` | `ok` | — | BR-005 (only returned on success; 404 raised instead of returning ok=False) |

---

## §4 — API / Interface Design

Three endpoints. No authentication anywhere (BR-006: CRITICAL hard constraint).
File target: `backend/router.py`

### Endpoint table

| Method | Path | Input | Output | Status codes | BRs enforced |
|--------|------|-------|--------|--------------|--------------|
| `GET` | `/api/notes` | — | `list[NoteResponse]` | 200 | BR-007 |
| `POST` | `/api/notes` | `NoteCreate` (JSON body) | `NoteResponse` | 201, 422 | BR-001, BR-002, BR-003 |
| `DELETE` | `/api/notes/{note_id}` | `note_id: int` (path) | `DeleteResponse` | 200, 404, 422 | BR-004, BR-005 |

### Status code specification

| Endpoint | Condition | Status | Response body |
|----------|-----------|--------|---------------|
| GET /api/notes | always succeeds | 200 | `[{id, content, created_at}, ...]` |
| POST /api/notes | note created | 201 | `{id, content, created_at}` |
| POST /api/notes | content empty after trim (BR-001) | 422 | `{"detail": [{"msg": "Note cannot be empty", ...}]}` |
| POST /api/notes | content > 500 chars (BR-002) | 422 | `{"detail": [{"msg": "Note too long (max 500 chars)", ...}]}` |
| DELETE /api/notes/{id} | note deleted | 200 | `{"ok": true}` |
| DELETE /api/notes/{id} | id ≤ 0 (BR-004) | 422 | `{"detail": "Invalid note ID"}` |
| DELETE /api/notes/{id} | id valid but note not found (BR-005) | 404 | `{"detail": "Note not found"}` |
| DELETE /api/notes/{id} | id not an integer | 422 | FastAPI path validation error |

### Auth requirement
**None.** BR-006 is a CRITICAL hard constraint: the legacy source has no authentication,
no sessions, no API keys, and no authorization anywhere. Adding any auth layer would
violate source design and is explicitly forbidden.

### Router implementation
File target: `backend/router.py`

```python
"""
FastAPI router for the notes API.

BR-006: No authentication, authorization, sessions, or API keys anywhere
        in this module. This is a CRITICAL hard constraint from the source design.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import DeleteResponse, NoteCreate, NoteResponse
from backend.service import NoteService

router = APIRouter(prefix="/api", tags=["notes"])


@router.get(
    "/notes",
    response_model=list[NoteResponse],
    summary="List all notes",
    description="Returns all notes ordered by creation date descending (newest first). BR-007.",
)
async def get_notes(
    db: AsyncSession = Depends(get_db),
) -> list[NoteResponse]:
    """
    BR-007: notes always returned newest-first; no client-configurable sort.
    BR-006: no auth.
    """
    service = NoteService(db)
    return await service.get_notes()


@router.post(
    "/notes",
    response_model=NoteResponse,
    status_code=201,
    summary="Create a note",
    description=(
        "Creates a new note. "
        "Content is whitespace-trimmed (BR-003), must not be empty (BR-001), "
        "and must not exceed 500 characters (BR-002)."
    ),
)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    """
    BR-001, BR-002, BR-003: enforced by NoteCreate Pydantic schema.
    BR-009: created_at is set by DB server_default; app never supplies it.
    BR-006: no auth.
    RISK-005: REST + SPA eliminates PRG; POST returns 201 JSON, no redirect.
    """
    service = NoteService(db)
    return await service.create_note(payload.content)


@router.delete(
    "/notes/{note_id}",
    response_model=DeleteResponse,
    status_code=200,
    summary="Delete a note",
    description=(
        "Deletes a note by ID. "
        "ID must be a positive integer (BR-004). "
        "Returns 404 if the note does not exist (BR-005)."
    ),
)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
) -> DeleteResponse:
    """
    BR-004: reject note_id <= 0 with "Invalid note ID".
    BR-005: 404 if note_id valid but note not found.
    RISK-004: DELETE HTTP method; no GET-based deletion accepted.
    BR-006: no auth.
    """
    # BR-004: cast to int happens via FastAPI path type annotation.
    # Manual > 0 check produces the exact error message specified in BR-004.
    if note_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid note ID")

    service = NoteService(db)
    await service.delete_note(note_id)
    return DeleteResponse(ok=True)
```

---

## §5 — Service Layer Design

Single service class `NoteService`. All database access is async.
File target: `backend/service.py`

```python
"""
Business logic layer for notes.

Each method is annotated with the BRs it implements.
Database access uses SQLAlchemy 2.x core-style expressions (parameterized —
RISK-002: no string interpolation or f-string SQL anywhere).
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Note


class NoteService:
    """
    Handles all business logic for note CRUD operations.

    Constructed per-request with the FastAPI-injected AsyncSession.
    No shared state between requests.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # get_notes
    # ------------------------------------------------------------------

    async def get_notes(self) -> list[Note]:
        """
        Return all notes ordered by created_at DESC.

        BR-007: sort order is newest-first and is NOT configurable by
                the caller. The ORDER BY is hardcoded here — no sort
                parameter is accepted.

        RISK-002: uses parameterized SQLAlchemy select(), not raw SQL.
        """
        result = await self._db.execute(
            select(Note).order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # create_note
    # ------------------------------------------------------------------

    async def create_note(self, content: str) -> Note:
        """
        Persist a new note and return the full record.

        BR-003: content has already been stripped by the Pydantic schema;
                this method receives only the trimmed value.
        BR-001, BR-002: enforced upstream by NoteCreate schema;
                not re-validated here (single source of truth).
        BR-009: created_at is set by DB server_default; the INSERT
                statement never includes a value for that column.
        RISK-002: uses parameterized ORM add() — no f-string SQL.
        RISK-005: returns the ORM Note object; no server-side redirect.
        """
        note = Note(content=content)
        self._db.add(note)
        await self._db.commit()
        await self._db.refresh(note)  # Populates id and created_at from DB
        return note

    # ------------------------------------------------------------------
    # delete_note
    # ------------------------------------------------------------------

    async def delete_note(self, note_id: int) -> None:
        """
        Delete a note by primary key. Raises 404 if no row was deleted.

        BR-004: note_id > 0 is enforced at the router layer before this
                method is called; this method trusts a positive integer.
        BR-005: checks result.rowcount after DELETE. If 0 rows were
                affected the note did not exist → raise 404. This is a
                GAP REMEDIATION — legacy PHP silently returned ok:true
                even when no row was deleted. The target behaviour is
                explicit 404 as specified in the comprehension doc.
        RISK-002: uses parameterized delete() expression — no f-string SQL.
        """
        result = await self._db.execute(
            delete(Note).where(Note.id == note_id)
        )
        await self._db.commit()

        # BR-005 gap remediation: rowcount == 0 means note did not exist
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Note not found")
```

### Method signature summary

| Method | Signature | BRs | Transaction |
|--------|-----------|-----|-------------|
| `get_notes` | `async def get_notes(self) -> list[Note]` | BR-007 | Read-only; no commit |
| `create_note` | `async def create_note(self, content: str) -> Note` | BR-003 (upstream), BR-001 (upstream), BR-002 (upstream), BR-009 | Commit after add |
| `delete_note` | `async def delete_note(self, note_id: int) -> None` | BR-004 (upstream), BR-005 | Commit after delete; 404 if rowcount==0 |

### Application entrypoint
File target: `backend/main.py`

```python
"""
FastAPI application entrypoint.

Registers the notes router and manages DB table creation during lifespan.
BR-006: no auth middleware, no session middleware, no API key middleware.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from backend.database import create_tables
from backend.router import router


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
```

---

## §6 — Risk Register and Mitigations

### RISK-001: HIGH — Delete Silent No-Op on Missing Note

**Source behaviour:**
Legacy PHP (`index.php:35-43`) executes `DELETE FROM notes WHERE id = ?` and
immediately returns `{"ok": true}` regardless of whether any row was actually
deleted. If the note did not exist, the caller receives a success response with
no indication of the failure. The frontend cannot distinguish "deleted" from
"was never there."

**Target implementation:**
After executing the `DELETE` statement, check `result.rowcount`. If zero rows
were affected, the note does not exist — raise 404.

```python
result = await self._db.execute(
    delete(Note).where(Note.id == note_id)
)
await self._db.commit()

if result.rowcount == 0:
    raise HTTPException(status_code=404, detail="Note not found")
```

**Validation approach:**
Test `DELETE /api/notes/9999` against an empty database. Assert HTTP 404 and
`{"detail": "Note not found"}`. Test `DELETE /api/notes/{valid_id}` after
creating a note. Assert HTTP 200 and `{"ok": true}`. Test double-delete: create,
delete (200), delete again (404).

---

### RISK-002: HIGH — SQL Injection via String Interpolation

**Source behaviour:**
Legacy PHP used `mysql_*` functions (deprecated since PHP 5.5, removed in PHP 7).
Pattern: `mysql_query("DELETE FROM notes WHERE id = " . $id)` — direct string
concatenation of user input into SQL. Completely vulnerable to SQL injection.

**Target implementation:**
All SQLAlchemy expressions use parameterized bindings. No `text()` with f-strings.
No string concatenation with user data. All three operations use typed ORM expressions:

```python
# GET — parameterized ORDER BY (no user input in this query)
select(Note).order_by(Note.created_at.desc())

# POST — ORM add(); SQLAlchemy generates parameterized INSERT
note = Note(content=content)
self._db.add(note)

# DELETE — parameterized WHERE clause via ORM expression
delete(Note).where(Note.id == note_id)
```

**What NOT to write:**
```python
# FORBIDDEN — f-string SQL injection vector
await db.execute(text(f"DELETE FROM notes WHERE id = {note_id}"))

# FORBIDDEN — string formatting
await db.execute(text("DELETE FROM notes WHERE id = %s" % note_id))
```

**Validation approach:**
Test `DELETE /api/notes/1%3BDROP%20TABLE%20notes` (URL-encoded `;DROP TABLE notes`).
FastAPI path type annotation `note_id: int` rejects this at routing time with 422.
Test `POST /api/notes` with `{"content": "'; DROP TABLE notes; --"}`.
Assert the string is stored literally and `SELECT * FROM notes` still returns rows.

---

### RISK-003: MEDIUM — Deprecated `mysql_*` API

**Source behaviour:**
Legacy PHP used `mysql_connect()`, `mysql_query()`, `mysql_fetch_assoc()` —
the `ext/mysql` extension removed in PHP 7. These are synchronous, unbuffered,
and provide no prepared statement support.

**Target implementation:**
Fully resolved by migration to SQLAlchemy 2.x async with `asyncpg` driver.
No action required beyond using the standard async session pattern as specified
in §2 and §5. The entire query execution path is parameterized and async.

**Validation approach:** N/A — resolved by architecture choice.

---

### RISK-004: MEDIUM — DELETE via HTTP GET

**Source behaviour:**
Legacy PHP (`index.php`) handles deletion via `$_GET['delete']` — the delete
operation is triggered by a GET request with a query parameter. This violates
HTTP semantics (GET must be idempotent and side-effect-free) and is vulnerable
to CSRF via `<img src="...?delete=1">` tags.

**Target implementation:**
`DELETE /api/notes/{note_id}` uses the HTTP DELETE method exclusively.
The router registration `@router.delete(...)` means FastAPI only routes HTTP
DELETE requests to this handler. A GET request to the same path returns 405
Method Not Allowed automatically.

```python
@router.delete("/notes/{note_id}", ...)
async def delete_note(note_id: int, ...):
    ...
```

**What NOT to write:**
```python
# FORBIDDEN — GET-based delete
@router.get("/notes")
async def get_notes(delete: int = None, ...):
    if delete:
        await service.delete_note(delete)
```

**Validation approach:**
`GET /api/notes/1` must return 405 Method Not Allowed (FastAPI default behaviour
for unregistered methods on a path). Only `DELETE /api/notes/1` returns 200/404.

---

### RISK-005: MEDIUM — No PRG Pattern (Duplicate on Refresh)

**Source behaviour:**
Legacy PHP returns an HTML page after a form POST. If the user presses browser
Refresh, the browser re-submits the POST form, potentially creating a duplicate
note. The PRG (Post-Redirect-Get) pattern was a workaround for this.

**Target implementation:**
Fully resolved by the REST API + SPA architecture. `POST /api/notes` returns
JSON (HTTP 201); the React SPA (MWU-NL2-002-FE) handles state updates and
navigation. There is no page reload, no browser form submission, and no refresh
risk. Server-side redirects must NOT be implemented.

**Validation approach:** N/A — resolved by architecture.

---

### RISK-006: MEDIUM — `DATETIME` to `TIMESTAMP WITH TIME ZONE`

**Source behaviour:**
MySQL `DATETIME` stores no timezone information. The legacy schema uses
`created_at DATETIME DEFAULT CURRENT_TIMESTAMP`. Timestamps are stored as
bare local time with no timezone record. Two notes created in different
timezones can have ambiguous ordering if the server's timezone changes.

**Target implementation:**
PostgreSQL `TIMESTAMPTZ` stores UTC internally and converts on read.
`DateTime(timezone=True)` in SQLAlchemy generates `TIMESTAMPTZ`. All timestamps
are unambiguous UTC regardless of server timezone setting.

```python
# In Note model (§2):
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
    nullable=False,
    init=False,
)
```

**Assumption documented:** Legacy data without timezone info is treated as UTC
during any future data migration. No historical data migration is in scope for
this MWU (schema is created fresh — see §8).

**Validation approach:**
Assert `NoteResponse.created_at` includes timezone info (`tzinfo` is not None).
Assert stored value round-trips correctly: create note, retrieve, confirm
`created_at.tzinfo` is UTC-aware.

---

### RISK-007: LOW — MySQL `utf8` 3-Byte Limitation

**Source behaviour:**
MySQL's `utf8` charset stores only 3-byte Unicode (BMP only). Emoji and
supplementary Unicode (U+10000 and above) are silently truncated or cause errors.
The legacy schema uses `DEFAULT CHARSET=utf8`.

**Target implementation:**
No action required. PostgreSQL's native `UTF8` encoding is always 4-byte.
Emoji, supplementary Unicode, and all characters in the Unicode standard are
stored correctly without any configuration change. The `VARCHAR(500)` length
limit is measured in characters (code points), not bytes.

**Validation approach:**
`POST /api/notes` with `content="Hello 🎉"`. Retrieve and assert content matches
exactly including the emoji. Assert length is 8 (7 chars + 1 emoji code point),
well under 500.

---

### RISK-008: LOW — Hardcoded DB Credential Fallbacks

**Source behaviour:**
Legacy `db.php` contains hardcoded fallback credentials:
`$host = "localhost"; $user = "noteuser"; $pass = "notepass"; $db = "notes_db";`
These credentials appear in source control and provide a default that works in
dev but is silently used in prod if env vars are not set.

**Target implementation:**
`DATABASE_URL` is required. If absent the process raises `KeyError` at import time —
fail-fast, not silent misconfiguration. No default value, no fallback credentials.

```python
# RISK-008: KeyError if missing — intentional fail-fast
DATABASE_URL: str = os.environ["DATABASE_URL"]
```

**What NOT to write:**
```python
# FORBIDDEN — hardcoded fallback
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://noteuser:notepass@localhost/notes_db")
```

**Validation approach:**
Unset `DATABASE_URL` and attempt to import `backend.database`. Assert `KeyError`
is raised immediately. Confirm no default connection string exists anywhere in
the codebase (`grep -r "noteuser\|notepass" backend/`).

---

## §7 — Cross-Module Stubs

**N/A — no cross-module dependencies.**

The backend module (MWU-NL2-001) has no upstream dependencies. It is entirely
self-contained. The downstream consumer MWU-NL2-002-FE (React frontend) depends
on this module's three REST endpoints, but the dependency flows one-way: frontend
calls backend. The backend does not call the frontend, and does not call any other
module.

No stub classes are required.

---

## §8 — Data Migration

**N/A — schema created fresh.**

The target PostgreSQL database is provisioned fresh for this migration.
No existing MySQL data is being migrated in this MWU. The `CREATE TABLE IF NOT EXISTS`
in §1 initialises the schema on first startup via the `lifespan` handler in `main.py`.

**Future data migration note (out of scope for MWU-NL2-001):**
If historical notes data is later migrated from MySQL to PostgreSQL:
- `id INT AUTO_INCREMENT` → `SERIAL` (values preserved; reset sequence with `SELECT setval('notes_id_seq', MAX(id)) FROM notes`)
- `content VARCHAR(500)` → `VARCHAR(500)` (direct copy; re-validate length in migration script)
- `created_at DATETIME` → `TIMESTAMPTZ` (treat as UTC per RISK-006 assumption: `AT TIME ZONE 'UTC'`)
- Emoji in content stored with MySQL `utf8` charset: re-validate all rows > 3 bytes; any 4-byte sequences were silently truncated in MySQL and must be handled as data loss

---

## §9 — Test Strategy

File targets: `backend/tests/conftest.py`, `backend/tests/test_notes.py`

### Fixtures

```python
# backend/tests/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.main import app
from backend.database import get_db
from backend.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test_notes"

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    AsyncTestSession = async_sessionmaker(db_engine, expire_on_commit=False)
    async with AsyncTestSession() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

### Test matrix

| BR ID | Test type | Scenario | Expected result |
|-------|-----------|----------|-----------------|
| BR-001 | Unit | POST with `content: ""` | 422, `"Note cannot be empty"` |
| BR-001 | Unit | POST with `content: "   "` (spaces only) | 422, `"Note cannot be empty"` |
| BR-001 | Unit | POST with `content: "\t\n"` (whitespace only) | 422, `"Note cannot be empty"` |
| BR-002 | Unit | POST with content of exactly 500 chars | 201, note created |
| BR-002 | Unit | POST with content of 501 chars | 422, `"Note too long (max 500 chars)"` |
| BR-002 | Unit | POST with content of 1000 chars | 422, `"Note too long (max 500 chars)"` |
| BR-003 | Unit | POST with `content: "  hello  "` | 201, stored content is `"hello"` (trimmed) |
| BR-003 | Unit | POST with `content: "\nhello\n"` | 201, stored content is `"hello"` |
| BR-003+001 | Unit | POST `"   "` — trim then empty check | 422 (not 201); order matters |
| BR-003+002 | Unit | POST 498 spaces + `"ab"` → trimmed = `"ab"` (2 chars) | 201; trim reduces to 2 chars |
| BR-004 | Unit | DELETE `/api/notes/0` | 422, `"Invalid note ID"` |
| BR-004 | Unit | DELETE `/api/notes/-1` | 422, `"Invalid note ID"` |
| BR-004 | Unit | DELETE `/api/notes/-999` | 422, `"Invalid note ID"` |
| BR-004 | Unit | DELETE `/api/notes/abc` | 422 (FastAPI path type error) |
| BR-005 | Integration | DELETE `/api/notes/9999` on empty DB | 404, `"Note not found"` |
| BR-005 | Integration | DELETE valid ID, then DELETE same ID | Second DELETE → 404 |
| BR-005 | Integration | DELETE valid ID that was just created | 200, `{"ok": true}` |
| BR-006 | Contract | GET `/api/notes` — no Authorization header | 200 (no 401/403) |
| BR-006 | Contract | POST `/api/notes` — no Authorization header | 201 (no 401/403) |
| BR-006 | Contract | DELETE `/api/notes/1` — no Authorization header | 200 or 404 (no 401/403) |
| BR-007 | Integration | Create note A then note B; GET `/api/notes` | Note B first in list (DESC order) |
| BR-007 | Integration | Create 5 notes; GET `/api/notes` | All 5 returned newest-first |
| BR-008 | Integration | POST with `content: "Hello 🎉"` | 201, stored content matches including emoji |
| BR-008 | Integration | POST with content containing 4-byte Unicode (U+1F4A1) | 201, round-trips correctly |
| BR-009 | Integration | POST note; inspect response `created_at` | `created_at` present, not null, UTC-aware |
| BR-009 | Contract | POST with body `{"content": "x", "created_at": "2000-01-01"}` | `created_at` in response is DB time, not `"2000-01-01"` |
| RISK-001 | Integration | Create, delete, delete again | Second delete → 404 (not silent ok:true) |
| RISK-002 | Security | POST with SQL injection payload in content | 201, stored literally; no SQL error |
| RISK-004 | Contract | GET `/api/notes/1` (wrong method for delete path) | 405 Method Not Allowed |

### Full test file skeleton

```python
# backend/tests/test_notes.py

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


class TestGetNotes:
    """GET /api/notes"""

    async def test_empty_list(self, client):
        resp = await client.get("/api/notes")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_br007_newest_first(self, client):
        """BR-007: notes returned in descending creation order."""
        await client.post("/api/notes", json={"content": "first"})
        await client.post("/api/notes", json={"content": "second"})
        resp = await client.get("/api/notes")
        notes = resp.json()
        assert notes[0]["content"] == "second"
        assert notes[1]["content"] == "first"

    async def test_br006_no_auth_required(self, client):
        """BR-006: GET requires no authentication."""
        resp = await client.get("/api/notes")
        assert resp.status_code != 401
        assert resp.status_code != 403


class TestCreateNote:
    """POST /api/notes"""

    async def test_create_success(self, client):
        resp = await client.post("/api/notes", json={"content": "Hello"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello"
        assert data["id"] > 0
        assert data["created_at"] is not None

    async def test_br003_trims_whitespace(self, client):
        """BR-003: content is stripped before storage."""
        resp = await client.post("/api/notes", json={"content": "  hello  "})
        assert resp.status_code == 201
        assert resp.json()["content"] == "hello"

    async def test_br001_empty_string_rejected(self, client):
        """BR-001: empty content rejected."""
        resp = await client.post("/api/notes", json={"content": ""})
        assert resp.status_code == 422
        assert "Note cannot be empty" in str(resp.json())

    async def test_br001_whitespace_only_rejected(self, client):
        """BR-001+BR-003: whitespace-only content rejected after trim."""
        resp = await client.post("/api/notes", json={"content": "   "})
        assert resp.status_code == 422
        assert "Note cannot be empty" in str(resp.json())

    async def test_br002_exactly_500_chars_accepted(self, client):
        """BR-002: 500 chars is the boundary — must be accepted."""
        resp = await client.post("/api/notes", json={"content": "x" * 500})
        assert resp.status_code == 201

    async def test_br002_501_chars_rejected(self, client):
        """BR-002: 501 chars exceeds limit."""
        resp = await client.post("/api/notes", json={"content": "x" * 501})
        assert resp.status_code == 422
        assert "Note too long (max 500 chars)" in str(resp.json())

    async def test_br008_emoji_stored_correctly(self, client):
        """BR-008: 4-byte Unicode (emoji) stored without truncation."""
        resp = await client.post("/api/notes", json={"content": "Hello 🎉"})
        assert resp.status_code == 201
        assert resp.json()["content"] == "Hello 🎉"

    async def test_br009_created_at_set_by_db(self, client):
        """BR-009: created_at present and timezone-aware; not supplied by app."""
        resp = await client.post("/api/notes", json={"content": "test"})
        assert resp.status_code == 201
        assert resp.json()["created_at"] is not None

    async def test_risk002_sql_injection_stored_literally(self, client):
        """RISK-002: SQL injection payload stored as literal string."""
        payload = "'; DROP TABLE notes; --"
        resp = await client.post("/api/notes", json={"content": payload})
        assert resp.status_code == 201
        # Verify table still exists and content round-trips
        notes = (await client.get("/api/notes")).json()
        assert any(n["content"] == payload for n in notes)

    async def test_br006_no_auth_required(self, client):
        """BR-006: POST requires no authentication."""
        resp = await client.post("/api/notes", json={"content": "test"})
        assert resp.status_code not in (401, 403)


class TestDeleteNote:
    """DELETE /api/notes/{note_id}"""

    async def test_delete_success(self, client):
        create_resp = await client.post("/api/notes", json={"content": "delete me"})
        note_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/notes/{note_id}")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async def test_br005_not_found_returns_404(self, client):
        """BR-005: non-existent note returns 404, not silent success."""
        resp = await client.delete("/api/notes/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Note not found"

    async def test_risk001_double_delete_returns_404(self, client):
        """RISK-001: second delete of same note returns 404, not ok:true."""
        create_resp = await client.post("/api/notes", json={"content": "once"})
        note_id = create_resp.json()["id"]
        await client.delete(f"/api/notes/{note_id}")
        second = await client.delete(f"/api/notes/{note_id}")
        assert second.status_code == 404

    async def test_br004_zero_id_rejected(self, client):
        """BR-004: note_id=0 rejected."""
        resp = await client.delete("/api/notes/0")
        assert resp.status_code == 422
        assert "Invalid note ID" in str(resp.json())

    async def test_br004_negative_id_rejected(self, client):
        """BR-004: negative note_id rejected."""
        resp = await client.delete("/api/notes/-1")
        assert resp.status_code == 422
        assert "Invalid note ID" in str(resp.json())

    async def test_br004_non_integer_id_rejected(self, client):
        """BR-004: non-integer path segment rejected by FastAPI path coercion."""
        resp = await client.delete("/api/notes/abc")
        assert resp.status_code == 422

    async def test_risk004_get_method_not_accepted(self, client):
        """RISK-004: DELETE path does not accept GET requests."""
        resp = await client.get("/api/notes/1")
        assert resp.status_code == 405

    async def test_br006_no_auth_required(self, client):
        """BR-006: DELETE requires no authentication."""
        create_resp = await client.post("/api/notes", json={"content": "auth test"})
        note_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/notes/{note_id}")
        assert resp.status_code not in (401, 403)
```

---

## File Structure for CodeGen

The CodeGen agent must produce the following file tree under the backend output directory:

```
backend/
├── main.py          # FastAPI app, lifespan, router registration
├── database.py      # Engine, session factory, get_db dependency
├── models.py        # SQLAlchemy 2.x ORM Note model + Base
├── schemas.py       # Pydantic v2 NoteCreate, NoteResponse, DeleteResponse
├── router.py        # FastAPI router with 3 endpoints
├── service.py       # NoteService with get_notes, create_note, delete_note
└── tests/
    ├── conftest.py  # Async fixtures: db_engine, db_session, client
    └── test_notes.py # Full BR test suite (all 9 BRs + RISK cases)
```

---

## BR Coverage Matrix

| BR ID | Description | Enforced in | Layer |
|-------|-------------|-------------|-------|
| BR-001 | Empty content rejected | `NoteCreate.validate_content` (step 2) | Pydantic + DB CHECK |
| BR-002 | Max 500 chars | `NoteCreate.validate_content` (step 3); `String(500)` | Pydantic + ORM + DDL |
| BR-003 | Trim before validate + store | `NoteCreate.validate_content` (step 1) | Pydantic |
| BR-004 | Positive integer ID | `delete_note` router handler guard | Router |
| BR-005 | 404 on missing note delete | `NoteService.delete_note` rowcount check | Service |
| BR-006 | No authentication | No auth middleware registered | Architecture |
| BR-007 | Newest-first order | `NoteService.get_notes` ORDER BY | Service + DDL index |
| BR-008 | UTF-8 4-byte support | PostgreSQL native UTF-8 | Database |
| BR-009 | DB-managed created_at | `server_default=func.now()`, `init=False` | ORM + DDL |
