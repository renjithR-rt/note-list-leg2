Writing the complete planning document to disk and loading the MKB tool in parallel.Now writing the complete planning document to disk and returning it as response text simultaneously.File written. Now storing to MKB.MKB stored (UUID: `21301749-a4e9-42b6-920b-b5050dbcf7d4`). Planning document complete.

---

# Planning Document — MWU-NL2-001 Backend
**Phase:** Planning
**MWU Tier:** LOW
**Date:** 2026-05-19
**Source stack:** PHP 5.6 + MySQL (`mysql_*` functions)
**Target stack:** FastAPI + SQLAlchemy 2.x (async) + PostgreSQL + asyncpg
**Business Rules:** 8 rules (from comprehension BR catalog)
**Dependencies:** none

---

## §1 — Target Data Model (DDL)

```sql
-- ============================================================
-- notes table — sole table owned by this module
-- ============================================================

CREATE TABLE notes (
    id          BIGSERIAL       PRIMARY KEY,
    content     VARCHAR(500)    NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_notes_content_nonempty CHECK (TRIM(content) <> '')
);

-- Supports BR-BACKEND-005: ORDER BY created_at DESC is the only list query.
-- A DESC index lets PostgreSQL satisfy that order without a sort step.
CREATE INDEX idx_notes_created_at_desc
    ON notes (created_at DESC);
```

### DDL design decisions

| Column | Type | Rationale |
|--------|------|-----------|
| `id` | `BIGSERIAL` | Auto-incrementing surrogate PK; `BIGINT` range future-proofs against row-count growth |
| `content` | `VARCHAR(500) NOT NULL` | Character-length limit (BR-BACKEND-002, resolved as character count); `NOT NULL` per BR-BACKEND-001 |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Timezone-aware timestamp; `NOW()` DB default avoids application clock drift |
| `chk_notes_content_nonempty` | CHECK constraint | Belt-and-suspenders for BR-BACKEND-001; primary enforcement is application-layer but DB must never hold empty strings |

No nullable columns. No foreign keys (self-contained module, no cross-module dependencies). No `updated_at` column — legacy source does not support updates.

---

## §2 — Target ORM / Data Access Models

```python
# models/note.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Note(Base):
    """ORM model for the notes table.

    Matches §1 DDL exactly:
      BIGSERIAL          → BigInteger + autoincrement=True
      VARCHAR(500)       → String(500)
      TIMESTAMPTZ        → DateTime(timezone=True)
      NOT NULL           → nullable=False on every column
      CHECK TRIM != ''   → CheckConstraint in __table_args__
    """

    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("TRIM(content) <> ''", name="chk_notes_content_nonempty"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
```

### ORM notes

- Uses SQLAlchemy 2.x `Mapped[]` + `mapped_column()` throughout — not the legacy 1.x `Column()` API.
- `DateTime(timezone=True)` maps to PostgreSQL `TIMESTAMPTZ` — timezone-aware in both Python and DB.
- `server_default=text("NOW()")` lets the database assign `created_at`; the application never sets this field directly.
- `nullable=False` is explicit on every column, matching `NOT NULL` in the DDL.
- No `__repr__`, no helper methods — the ORM model is a pure data access layer.
- `expire_on_commit=False` is set at the session factory level (see §5) so that after `commit()` the ORM instance can still be serialised to Pydantic without a lazy re-load.

---

## §3 — Validation Schemas / DTOs

```python
# schemas/note_schemas.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_config

class NoteCreate(BaseModel):
    """Input schema for POST /notes.

    Validator execution order (Pydantic v2):
      1. strip_whitespace  (mode='before') — BR-BACKEND-006: strip before any check
      2. content_not_empty (mode='after')  — BR-BACKEND-001: reject empty after strip
      3. Pydantic built-in max_length=500  — BR-BACKEND-002: 500-character limit
    """

    content: str = Field(
        ...,
        max_length=500,          # BR-BACKEND-002: character-length limit (Python len())
        description="Note content — 1 to 500 characters after stripping whitespace.",
    )

    # BR-BACKEND-006: strip leading/trailing whitespace before any validation
    @field_validator("content", mode="before")
    @classmethod
    def strip_whitespace(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    # BR-BACKEND-001: reject content that is empty after stripping
    @field_validator("content", mode="after")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Note cannot be empty")
        return v

    model_config = model_config(populate_by_name=True)

class NoteRead(BaseModel):
    """Response schema for a single note (used in list and create responses).

    created_at is returned as a timezone-aware datetime.
    Pydantic serialises datetime to ISO 8601 automatically.
    Frontend is responsible for display formatting — BR-RISK-004.
    """

    id: int
    content: str
    created_at: datetime  # ISO 8601 in JSON output — e.g. "2026-05-19T14:30:00+00:00"

    model_config = model_config(from_attributes=True)
```

### Schema design notes

- `max_length=500` in `Field(...)` uses Pydantic's built-in validator which calls `len()` — character count, not byte count. This is the BR-BACKEND-002 ambiguity resolution (character semantics).
- `mode='before'` on `strip_whitespace` guarantees stripping happens before the built-in `max_length` validator and before `content_not_empty`.
- No `NoteUpdate` schema — the legacy source has no update operation.
- No delete input schema — the delete path parameter (`note_id: int`) is validated directly on the router via `Path(..., gt=0)`.

---

## §4 — API / Interface Design

### Endpoint table

| Method | Path | Input | Output | Status codes | BRs enforced |
|--------|------|-------|--------|--------------|--------------|
| `GET` | `/notes` | — | `list[NoteRead]` | 200 | BR-005, BR-008 |
| `POST` | `/notes` | `NoteCreate` (JSON body) | `NoteRead` | 201, 422 | BR-001, BR-002, BR-004, BR-006 |
| `DELETE` | `/notes/{note_id}` | `note_id: int` path param | `204 No Content` | 204, 404, 422 | BR-003, BR-004, BR-007 |

No auth on any endpoint — BR-BACKEND-004 (confirmed deliberate design).

**GET `/notes`** — returns all notes newest-first (`[]` when empty, no pagination, no sort param).\
**POST `/notes`** — 422 on empty/whitespace/oversized content; 201 with full `NoteRead` on success.\
**DELETE `/notes/{note_id}`** — 422 for non-integer or ≤ 0; 404 for missing; 204 on success.

```python
# routers/notes.py
from fastapi import APIRouter, Depends, Path, status
from app.schemas.note_schemas import NoteCreate, NoteRead
from app.services.note_service import NoteService, get_note_service

router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("", response_model=list[NoteRead], status_code=status.HTTP_200_OK)
async def list_notes(service: NoteService = Depends(get_note_service)) -> list[NoteRead]:
    notes = await service.list_notes()
    return [NoteRead.model_validate(n) for n in notes]

@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(body: NoteCreate, service: NoteService = Depends(get_note_service)) -> NoteRead:
    note = await service.create_note(content=body.content)
    return NoteRead.model_validate(note)

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int = Path(..., gt=0, description="ID of the note to delete"),
    service: NoteService = Depends(get_note_service),
) -> None:
    await service.delete_note(note_id=note_id)
```

---

## §5 — Service Layer Design

```python
# db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://user:pass@host/db
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

```python
# services/note_service.py
from fastapi import Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.note import Note

class NoteService:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_notes(self) -> list[Note]:
        # BR-BACKEND-005: ORDER BY created_at DESC
        # BR-BACKEND-008: no LIMIT/OFFSET
        result = await self._db.execute(
            select(Note).order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_note(self, content: str) -> Note:
        # BR-001, BR-002, BR-006 enforced upstream by NoteCreate schema
        note = Note(content=content)
        self._db.add(note)
        await self._db.flush()
        await self._db.refresh(note)
        await self._db.commit()
        return note

    async def delete_note(self, note_id: int) -> None:
        # BR-BACKEND-003: gt=0 enforced at router layer
        # BR-BACKEND-007: 404 when rowcount == 0
        result = await self._db.execute(
            delete(Note).where(Note.id == note_id)
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found",
            )
        await self._db.commit()

async def get_note_service(db: AsyncSession = Depends(get_db)) -> NoteService:
    return NoteService(db)
```

### Method summary

| Method | BRs | Transaction | Raises |
|--------|-----|-------------|--------|
| `list_notes()` | BR-005, BR-008 | Read-only — no commit | — |
| `create_note(content)` | BR-001, BR-002, BR-006 (via schema) | INSERT + flush + refresh + commit | — |
| `delete_note(note_id)` | BR-003 (router), BR-007 | DELETE + commit if found | `HTTPException(404)` when `rowcount == 0` |

---

## §6 — Risk Register and Mitigations

### RISK-BACKEND-001: GLOBAL-VAR — Global database connection coupling

**Source behaviour:**
PHP uses `global $conn` — a module-level variable holding a single `mysql_connect()` result. All functions mutate shared state. No connection pooling, no per-request lifecycle.

**Target implementation:**
FastAPI `get_db()` dependency yields a new `AsyncSession` scoped to each request via `async with async_session_factory()`. No module-level session objects. No singleton patterns.

```python
# Correct — one session per request:
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

**Validation approach:** Integration test: two concurrent `GET /notes` requests; assert no `InvalidRequestError`; log `id(session)` per request — values must differ.

---

### RISK-BACKEND-002: RAW-SQL-CONCAT — SQL injection via string interpolation

**Source behaviour:**
`mysql_query("INSERT INTO notes (content) VALUES ('" . $content . "')")` — direct string interpolation of user content into SQL. SQL metacharacters in content execute as SQL.

**Target implementation:**
All queries use SQLAlchemy ORM or statement objects. User-supplied values are automatically parameterised — never interpolated.

```python
# Parameterised INSERT:
note = Note(content=content)
self._db.add(note)

# Parameterised DELETE:
await self._db.execute(delete(Note).where(Note.id == note_id))
```

Never use `text()` with f-strings or string concatenation.

**Validation approach:** `bandit -r app/` — zero `B608` findings. Integration test: inject `'); DROP TABLE notes; --` as content → stored as literal, table intact.

---

### RISK-BACKEND-003: DIRECT-OUTPUT — Business logic mixed with HTML rendering

**Source behaviour:**
PHP `add_note()` executes INSERT and echoes `<li>` HTML in the same function. No separation of concerns.

**Target implementation:**
Three-layer separation: `routers/notes.py` → `services/note_service.py` → `models/note.py`. Routers return Pydantic JSON. No HTML anywhere in the backend.

**Validation approach:** `Select-String "<[a-zA-Z]" (Get-ChildItem app -Recurse -Filter "*.py").FullName` → zero matches.

---

### RISK-BACKEND-004: DATE-INTERPOLATION — PHP date formatting in output

**Source behaviour:**
`date('Y-m-d H:i', strtotime($row['created_at']))` hard-codes a display format in the backend response.

**Target implementation:**
`NoteRead.created_at: datetime` — Pydantic serialises to ISO 8601 automatically. No `strftime()` in the backend. Frontend handles display formatting.

**Validation approach:** Integration test: `GET /notes` — assert `created_at` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`. Grep for `strftime` → zero matches.

---

### RISK-BACKEND-005: NULL-RETURN — Silent success on delete of non-existent ID

**Source behaviour:**
`delete_note()` returns `['ok' => true]` even when `mysql_affected_rows() == 0`. No distinction between deleted and not-found.

**Target implementation:**
Check `result.rowcount` after DELETE. Raise `HTTPException(404)` when zero. Deliberate behavioural change from legacy (BR-BACKEND-007, pending SME confirmation).

```python
result = await self._db.execute(delete(Note).where(Note.id == note_id))
if result.rowcount == 0:
    raise HTTPException(status_code=404, detail="Note not found")
await self._db.commit()
```

**Validation approach:** `DELETE /notes/99999` → `404`. Delete same note twice → first `204`, second `404`.

---

### RISK-BACKEND-006: DEPRECATED-EXT — `mysql_*` functions removed in PHP 7

**Source behaviour:**
`mysql_connect()`, `mysql_query()`, `mysql_fetch_assoc()` — removed in PHP 7. Source is unmaintainable.

**Target implementation:**
SQLAlchemy 2.x async engine + `asyncpg`. `requirements.txt`: `sqlalchemy>=2.0.0`, `asyncpg>=0.29.0`. No `pymysql`, no `psycopg2`.

**Validation approach:** Assert no `mysql`/`pymysql`/`MySQLdb` in `requirements.txt`. Full test suite against PostgreSQL passes.

---

### RISK-BACKEND-007: STRLEN-MULTIBYTE — Byte-count vs character-count mismatch

**Source behaviour:**
PHP `strlen()` counts bytes. For multi-byte UTF-8 (emoji, CJK), byte count > character count. PHP 500-byte limit is more restrictive than Python 500-character limit.

**Target implementation:**
Python `len()` counts characters. `Field(..., max_length=500)` uses character count (BR-BACKEND-002 ambiguity resolved as character semantics). Pending SME confirmation — override path documented in §6 if byte semantics required.

**Validation approach:** `NoteCreate(content="😀" * 500)` → valid. `NoteCreate(content="😀" * 501)` → `ValidationError`.

---

### RISK-BACKEND-008: NO-CSRF — No CSRF protection

**Source behaviour:** No CSRF in PHP source.

**Target implementation:** No action required. JSON API with no cookie-based auth (BR-BACKEND-004) is not subject to CSRF. Do not add CSRF middleware.

**Validation approach:** No CSRF middleware in `main.py`. No cookie auth added.

---

## §7 — Cross-Module Stubs (if applicable)

N/A — no cross-module dependencies.

The comprehension document (Section 4) confirms this module has zero cross-module dependencies. The legacy source is a single-file PHP application with no shared includes, sessions, or external module calls. No stub classes are required.

---

## §8 — Data Migration (if applicable)

N/A — schema created fresh.

The target PostgreSQL database is provisioned new. The `notes` table is created via §1 DDL at application startup. No existing MySQL data is ported as part of this MWU.

For reference — if historical data migration is requested in a future MWU:

| MySQL column | MySQL type | PostgreSQL type | Conversion note |
|---|---|---|---|
| `id` | `INT AUTO_INCREMENT` | `BIGSERIAL` | Preserve IDs; reset sequence to `MAX(id)+1` after import |
| `content` | `VARCHAR(500)` | `VARCHAR(500)` | ASCII range: character semantics match |
| `created_at` | `DATETIME` (no tz) | `TIMESTAMPTZ` | Apply UTC assumption; `AT TIME ZONE 'UTC'` cast in migration SQL |

---

## §9 — Test Strategy

### BR test matrix

| BR ID | Test type | Scenario | Expected result |
|-------|-----------|----------|-----------------|
| BR-BACKEND-001 | Unit | `NoteCreate(content="")` | `ValidationError`: "Note cannot be empty" |
| BR-BACKEND-001 | Unit | `NoteCreate(content="   ")` | `ValidationError`: empty after strip |
| BR-BACKEND-001 | Unit | `NoteCreate(content="\t\n")` | `ValidationError`: empty after strip |
| BR-BACKEND-001 | Integration | `POST /notes` `{"content": ""}` | `422 Unprocessable Entity` |
| BR-BACKEND-002 | Unit | `NoteCreate(content="a" * 500)` | Valid |
| BR-BACKEND-002 | Unit | `NoteCreate(content="a" * 501)` | `ValidationError` |
| BR-BACKEND-002 | Unit | `NoteCreate(content="  " + "a"*499 + "  ")` | Valid — stripped to 499 chars |
| BR-BACKEND-002 | Integration | `POST /notes` 501-char content | `422` |
| BR-BACKEND-003 | Integration | `DELETE /notes/0` | `422` |
| BR-BACKEND-003 | Integration | `DELETE /notes/-1` | `422` |
| BR-BACKEND-003 | Integration | `DELETE /notes/abc` | `422` |
| BR-BACKEND-004 | Code review | Search for auth imports | Zero: no `OAuth2`, `JWT`, `get_current_user` |
| BR-BACKEND-004 | Integration | `POST /notes` no Authorization header | `201` |
| BR-BACKEND-005 | Integration | Create 3 notes at different times; `GET /notes` | Newest-first order |
| BR-BACKEND-006 | Unit | `NoteCreate(content="  hello  ")` | `content == "hello"` |
| BR-BACKEND-006 | Unit | `NoteCreate(content="\thello\n")` | `content == "hello"` |
| BR-BACKEND-007 | Integration | `DELETE /notes/99999` | `404 Not Found`, `{"detail": "Note not found"}` |
| BR-BACKEND-007 | Integration | Create → delete → delete again | First `204`, second `404` |
| BR-BACKEND-008 | Integration | Seed 1000 notes; `GET /notes` | All 1000 returned |
| BR-BACKEND-008 | Code review | List query for LIMIT/OFFSET | Zero occurrences |

### Happy path coverage

| Flow | Expected result |
|------|-----------------|
| `POST /notes` valid content | `201`, response has `id`, `content`, `created_at` |
| `GET /notes` empty DB | `200`, `[]` |
| `GET /notes` 3 notes | `200`, list ordered newest-first |
| `DELETE /notes/{id}` existing | `204`, note absent from subsequent `GET` |
| Full flow: create 3 → list → delete middle → list | Passes at each step; remaining 2 ordered correctly |

### Key fixtures

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.session import get_db
from app.main import app
from app.models.note import Base

TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost/notes_test"

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

### Edge cases

| Edge case | Input | Expected |
|-----------|-------|----------|
| Whitespace variants | `"\t"`, `"\n"`, `"\r\n"` | All rejected (422) |
| Exactly 500 chars | `"a" * 500` | Accepted (201) |
| Exactly 501 chars | `"a" * 501` | Rejected (422) |
| SQL injection in content | `"'); DROP TABLE notes; --"` | Stored as literal; table intact |
| 500 emoji (multi-byte) | `"😀" * 500` | Accepted (character semantics) |
| Delete already-deleted note | `DELETE /notes/{id}` twice | Second → 404 |
| List after all notes deleted | Create 2 → delete both → `GET /notes` | `200`, `[]` |

---

**Artifacts:**
- Planning document written to: `E:\Claude\note-list-leg2\output\mkb\backend\track-a\planning-001.md`
- MKB UUID: `21301749-a4e9-42b6-920b-b5050dbcf7d4`