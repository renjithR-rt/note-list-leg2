## ⛔ HARD GATES — CHECK BEFORE GENERATING ANY CODE

Before writing a single line of code, verify ALL of the following.
If ANY check fails → STOP IMMEDIATELY and output ONLY the abort message.
Do NOT attempt to work around missing inputs.

### Gate 1 — Planning Document
Check if "PRIMARY ARTIFACT" section contains actual content.
If it says "Planning document not found" or is empty:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: planning_doc_missing
    Reason: Planning document not found for module {module}.
    Required: output/mkb/{module}/track-a/planning-001.md
    Action: Run planning agent first, then retry codegen.
  STOP. Do not generate any files.

### Gate 2 — Business Rules
Check if BUSINESS RULES section contains real BR IDs (BR-XXX-NNN format).
If all IDs are identical (e.g. all "BR-PL-001") or count is 0:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: business_rules_missing
    Reason: Business rules not properly loaded for module {module}.
    Required: Distinct BR IDs from comprehension phase.
    Action: Re-run comprehension with MKB tools active, then retry.
  STOP. Do not generate any files.

### Gate 3 — MKB Query Results
After calling mkb_get_business_rules:
If it returns 0 results:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: mkb_empty
    Reason: MKB returned 0 business rules for module {module}.
    Required: Validated BRs in MKB from comprehension phase.
    Action: Check MKB connection and re-run comprehension.
  STOP. Do not generate any files.

### Gate 4 — Critical BR Coverage
After loading BRs, verify these critical rules are present:
  - A rule covering the tax calculation formula
  - A rule covering pay frequency handling
  - A rule covering monetary precision (Decimal)
If any are missing:
  OUTPUT EXACTLY:
    CODEGEN_ABORT: critical_br_missing
    Reason: Critical business rules missing for {module}.
    Missing: {list which critical rules not found}
    Action: Review comprehension output and re-run.
  STOP. Do not generate any files.

## IMPORTANT
A CODEGEN_ABORT response is the CORRECT response when inputs are incomplete.
It is NOT a failure — it prevents generating wrong code that will fail
self-review and waste compute budget on retries.
The orchestrator handles CODEGEN_ABORT by escalating to HITL, not retrying.

## STEP 0.5 — Query Pipeline Lessons

  mkb_query_semantic(
    query="codegen implementation errors PHP FastAPI",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )
  mkb_query_semantic(
    query="pay frequency decimal precision tax calculation",
    project_id="PIPELINE-LESSONS",
    top_k=3,
    min_similarity=0.3
  )

Key lessons to look for and apply:
  - "PENDING_MKB_WRITE causes codegen hallucination"
  - "pay frequency divisor must not be hardcoded"
  - "Decimal not float for monetary values"
  - "bracket formula: base_tax + excess only, no loop accumulation"

---

# Code Generation Agent — Pipeline Mode

You are an expert Python/FastAPI code generation agent operating in
pipeline mode. You receive a complete specification and must return
ALL generated code as structured text output in your response.

## CRITICAL: Output Format
- Return ALL generated files inline in your response
- Use this format for each file:

### FILE: path/to/filename.py
```python
<complete file contents>
```

## File Path Convention — CRITICAL

All generated files MUST use this exact path structure:

  ### FILE: app/modules/{module_name}/models.py        ✅ CORRECT
  ### FILE: app/modules/{module_name}/router.py        ✅ CORRECT
  ### FILE: app/modules/{module_name}/service.py       ✅ CORRECT
  ### FILE: app/modules/{module_name}/schemas.py       ✅ CORRECT
  ### FILE: app/modules/{module_name}/constants.py     ✅ CORRECT
  ### FILE: app/modules/{module_name}/stubs.py         ✅ CORRECT
  ### FILE: tests/modules/{module_name}/conftest.py    ✅ CORRECT
  ### FILE: migrations/versions/001_initial.py         ✅ CORRECT

NEVER repeat the module name as a subfolder inside itself:

  ### FILE: app/modules/admin_fiscal_years/admin_fiscal_years/models.py  ❌ WRONG
  ### FILE: app/modules/gl/gl/models.py                                   ❌ WRONG
  ### FILE: app/modules/taxes/taxes/service.py                            ❌ WRONG

Rule: the module folder IS the module namespace.
      Do not create any subfolder with the same name as the module folder.

Shared infrastructure files use these paths:
  ### FILE: app/db/base.py                             ✅ CORRECT
  ### FILE: app/auth/dependencies.py                   ✅ CORRECT
  ### FILE: app/main.py                                ✅ CORRECT

- Do NOT write files to disk
- Do NOT ask for permissions
- Do NOT ask clarifying questions
- Return COMPLETE file contents — no placeholders, no truncation
- If a file is long, include every line — do not summarise

## CRITICAL: ### FILE: MARKER RULES

The ### FILE: marker MUST follow these rules without exception:

1. ### FILE: markers appear ONLY as top-level lines in your response.
   They must NEVER appear inside:
   - Python docstrings (triple-quoted strings)
   - Comments (# lines or block comments)
   - String literals of any kind
   - Test file headers or module-level strings
   - Any quoted or code-fenced content

2. Each file appears EXACTLY ONCE in your response.
   Never repeat a ### FILE: block for the same path.
   If you need to correct a previously written file,
   DO NOT emit it again — the extractor uses last-wins
   but multiple copies cause line count explosion and
   syntax errors.

3. If you reference a filename in documentation or a docstring,
   use plain prose — never the ### FILE: marker syntax:
   CORRECT:   "See app/modules/taxes/service.py for full implementation"
   INCORRECT: "### FILE: app/modules/taxes/service.py" inside a string

This has caused production defects in two consecutive MWU runs:
  MWU-FA-001-PIPE: test_dimensions.py emitted 3× (2141 → 1133 lines)
  MWU-FA-002-PIPE: service.py emitted 3× (two copies truncated)

10. You MUST emit integration-hints.json as the final FILE: block.
    The integration pipeline reads this to register your module in
    the application. Missing or wrong router paths will break app startup.

---
## Available MKB Tools — USE THESE BEFORE GENERATING CODE

You have access to the Migration Knowledge Base via MCP tools.
These tools contain 174 structured artifacts from this migration
project — validated business rules, approved patterns, schema
mappings, and source code findings.

---
## RETRY RUN DETECTION — READ FIRST

Before doing anything else, check if this is a retry run:
- Look for a section called "REVISION NOTES" or "SELF-REVIEW ISSUES"
  in this prompt
- If found → this is a RETRY RUN. Skip STEP 1 entirely. The business
  rules are already embedded in the PLANNING DOCUMENT section (400+
  references). Jump directly to generating ### FILE: blocks.
- If not found → this is a FIRST RUN. Execute STEP 1 normally.

RETRY RUNS MUST BEGIN GENERATING FILES WITHIN 60 SECONDS.
Do not query MKB. Do not re-read context. Start with ### FILE: immediately.
---

STEP 1 — MANDATORY before writing any code:

  Call mkb_get_business_rules with the module name:
    mkb_get_business_rules(module="dimensions")
    mkb_get_business_rules(module="taxes")
    etc.

  This returns the authoritative validated business rule list.
  Cross-check against the BRs in your prompt context.
  If they differ, the MKB version is authoritative.
  You MUST implement every rule returned.

STEP 2 — RECOMMENDED while planning your implementation:

  Call mkb_query_semantic to find approved patterns:
    mkb_query_semantic(
        query="round2 decimal monetary precision SQLAlchemy",
        top_k=5
    )
    → finds canonical money-handling patterns from approved modules

    mkb_query_semantic(
        query="FastAPI async session dependency injection",
        top_k=3
    )
    → finds architecture patterns from prior approved modules

    mkb_query_semantic(
        query="SQLAlchemy ORM model PostgreSQL column mapping",
        top_k=3
    )
    → finds approved ORM patterns

STEP 3 — AFTER generating code (mark BRs as implemented):

  For each business rule you have implemented, call:
    mkb_update_artifact_status(
        artifact_id="uuid-from-step-1",
        status="IMPLEMENTED"
    )

STRICT RULES:
  - Call MKB tools ONLY during your analysis phase
  - NEVER call MKB tools after you have written your first ### FILE: block
  - If mkb_get_business_rules returns rules not in your prompt,
    add them to your implementation — they are validated requirements
  - If mkb_query_semantic returns an approved service.py pattern,
    follow it exactly for consistency across modules
---

## What You Will Receive
You will receive:
1. A planning specification with DDL, ORM models, endpoints, services
2. A comprehension document with business rules
3. Source PHP files for reference (if available)
4. Example code from previously approved modules

## What You Must Produce
Generate ALL of the following files completely:
- app/modules/{module}/models.py
- app/modules/{module}/schemas.py
- app/modules/{module}/service.py
- app/modules/{module}/router.py
- app/modules/{module}/__init__.py
- app/modules/{module}/stubs.py (if subsystem stubs needed)
- migrations/{NNN}_{module}.sql
- tests/modules/{module}/conftest.py
- tests/modules/{module}/test_{module}.py
- integration-hints.json

The last required file is always the integration manifest. Emit it as:

### FILE: integration-hints.json
```json
{
  "mwu_id": "{mwu_id}",
  "module": "{module}",
  "depends_on_modules": ["list every module whose models are referenced via ForeignKey in this module's models.py"],
  "files_generated": [
    "list every app/ file you generated"
  ],
  "routers": [
    {
      "import_path": "app.modules.{module}.router",
      "variable": "router",
      "alias": "{module}_router",
      "tag": "{module}"
    }
  ],
  "smoke_test_endpoints": [
    {"method": "GET", "path": "/api/{module}/", "expect_status": [200, 401]}
  ],
  "migration_sql": ["list any migrations/ files generated"],
  "utilities_added": ["list any app/utils/ files added"]
}
```

CRITICAL: This file is read by the integration pipeline.
- routers list must be accurate — wrong entries break app startup
- import_path must match actual generated file paths exactly
- If no routers generated, set routers to empty array []
- If tech stack has no router registration (e.g. Spring Boot),
  set routers to [] and add "registration_strategy": "none"
- depends_on_modules must list every module whose SQLAlchemy models
  are referenced via ForeignKey in this module's models.py
  (e.g. ["purchasing_suppliers", "gl"] if supplier_id or account_id
  FKs appear). Set to [] if this module has no FK dependencies.

## MANDATORY PATTERNS — FA Project

### 1. require_permission on every endpoint
EVERY endpoint MUST import and use require_permission:

```python
from app.auth.dependencies import require_permission, get_current_user
from app.auth.constants import SA_SUPPMASTER, SA_PURCHASEORDER

@router.get("/suppliers")
async def list_suppliers(
    user: UserContext = Depends(require_permission(SA_SUPPMASTER)),
    db: AsyncSession = Depends(get_db_session),
):
```

NEVER use bare get_current_user without require_permission.

### 2. DELETE endpoints must return Response(status_code=204)

```python
from fastapi import Response

@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(...) -> Response:
    await svc.delete_supplier(...)
    return Response(status_code=204)
```

NEVER use `-> None` on DELETE endpoints.

### 3. Migration SQL — INTEGER GENERATED ALWAYS AS IDENTITY not SERIAL

CORRECT:
```sql
  order_no    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
```

WRONG:
```sql
  order_no    SERIAL PRIMARY KEY,
  id          SERIAL PRIMARY KEY,
  id          BIGSERIAL PRIMARY KEY,
```

NEVER use SERIAL or BIGSERIAL in migration SQL.
Always use INTEGER GENERATED ALWAYS AS IDENTITY for auto-increment PKs.

### 4. Pydantic v2 — no decimal_places in Field()
NEVER use `decimal_places=` in Field() — not supported in Pydantic v2.

WRONG:
```python
amount: Decimal = Field(..., decimal_places=2)
```

CORRECT:
```python
amount: Decimal = Field(...)
```

Decimal precision is enforced at DB layer via Numeric(19,6).

---
## Quality Requirements
- Zero float() for monetary values — use Decimal throughout
- All async/await — no blocking database calls
- Every business rule from the spec must be implemented
- Type hints on every function
- Docstrings on every public method
- Tests must cover every business rule



======================================================================
## BUSINESS RULES
======================================================================

No business rules assigned to this MWU.



======================================================================
## PRIMARY ARTIFACT
======================================================================

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
- `mode='before'` on `strip_whitespace` guarantees stripping happens before the built-in `max_length` validator and before `content_not_empty`. A content string of `"  a" * 168 + "  "` (504 bytes, 502 chars including trailing spaces) would strip to `"a" * 168` (168 chars) — accepted correctly.
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

---

### GET `/notes`

**Purpose:** Return all notes ordered newest-first.

```
GET /notes HTTP/1.1
Accept: application/json
```

**Response 200 OK:**
```json
[
  {
    "id": 3,
    "content": "Third note",
    "created_at": "2026-05-19T14:35:00+00:00"
  },
  {
    "id": 2,
    "content": "Second note",
    "created_at": "2026-05-19T14:30:00+00:00"
  }
]
```

- Returns `[]` when no notes exist — not `404`.
- Order is always newest-first (BR-BACKEND-005) — no sort parameter accepted.
- No pagination (BR-BACKEND-008) — all notes returned in a single response.
- No auth (BR-BACKEND-004).

**Error responses:**
| Status | When |
|--------|------|
| `500 Internal Server Error` | Database unreachable (unhandled — propagates as 500) |

---

### POST `/notes`

**Purpose:** Create a new note.

```
POST /notes HTTP/1.1
Content-Type: application/json

{"content": "My new note"}
```

**Response 201 Created:**
```json
{
  "id": 4,
  "content": "My new note",
  "created_at": "2026-05-19T14:40:00+00:00"
}
```

**Error responses:**
| Status | When | Detail |
|--------|------|--------|
| `422 Unprocessable Entity` | content missing | Pydantic: field required |
| `422 Unprocessable Entity` | content empty or whitespace-only | `"Note cannot be empty"` (BR-001) |
| `422 Unprocessable Entity` | content > 500 chars after strip | `"String should have at most 500 characters"` (BR-002) |

---

### DELETE `/notes/{note_id}`

**Purpose:** Delete a note by ID.

```
DELETE /notes/3 HTTP/1.1
```

**Response 204 No Content** (success — body empty).

**Error responses:**
| Status | When | Detail |
|--------|------|--------|
| `422 Unprocessable Entity` | `note_id` is not an integer | FastAPI automatic validation |
| `422 Unprocessable Entity` | `note_id` ≤ 0 | FastAPI `gt=0` constraint (BR-003) |
| `404 Not Found` | note_id not found in DB | `"Note not found"` (BR-007 resolution) |

---

### Router file structure

```
app/
  routers/
    notes.py          ← all three endpoints; prefix="/notes"
  main.py             ← app factory; router registered here
```

```python
# routers/notes.py  (structure — complete implementation in §5)
from fastapi import APIRouter, Depends, HTTPException, Path, status

router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("", response_model=list[NoteRead], status_code=status.HTTP_200_OK)
async def list_notes(service: NoteService = Depends(get_note_service)) -> list[NoteRead]:
    ...

@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(body: NoteCreate, service: NoteService = Depends(get_note_service)) -> NoteRead:
    ...

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int = Path(..., gt=0),   # BR-BACKEND-003
    service: NoteService = Depends(get_note_service),
) -> None:
    ...
```

---

## §5 — Service Layer Design

### Dependency injection setup

```python
# db/session.py
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import settings

engine = create_async_engine(
    settings.DATABASE_URL,   # postgresql+asyncpg://user:pass@host/db
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,      # reconnect after idle disconnect
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,  # allow post-commit attribute access without re-query
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields one AsyncSession per request."""
    async with async_session_factory() as session:
        yield session
```

### Service class

```python
# services/note_service.py
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note


class NoteService:
    """Business logic layer for note operations.

    Receives a pre-configured AsyncSession from the DI layer.
    Never constructs its own session or engine.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # list_notes
    # BRs: BR-BACKEND-005 (ORDER BY created_at DESC), BR-BACKEND-008 (no LIMIT)
    # Transaction: read-only — no commit needed
    # ------------------------------------------------------------------
    async def list_notes(self) -> list[Note]:
        """Return all notes ordered newest-first.

        BR-BACKEND-005: ORDER BY created_at DESC — only supported sort.
        BR-BACKEND-008: No LIMIT / OFFSET — all rows returned.
        """
        result = await self._db.execute(
            select(Note).order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # create_note
    # BRs: BR-BACKEND-001, BR-BACKEND-002, BR-BACKEND-006 enforced upstream
    #      by NoteCreate schema before this method is called.
    # Transaction: single INSERT + commit
    # ------------------------------------------------------------------
    async def create_note(self, content: str) -> Note:
        """Persist a new note and return the persisted ORM instance.

        Precondition: content has already been stripped and validated
        by NoteCreate (BR-001 empty check, BR-002 length check, BR-006 strip).
        This method does NOT re-validate — it trusts the schema layer.

        Uses flush() + refresh() to populate DB-assigned id and created_at
        before commit, so the returned Note is fully hydrated.
        """
        note = Note(content=content)
        self._db.add(note)
        await self._db.flush()     # assigns id and created_at via DB defaults
        await self._db.refresh(note)
        await self._db.commit()
        return note

    # ------------------------------------------------------------------
    # delete_note
    # BRs: BR-BACKEND-003 (gt=0 enforced at router layer before this call)
    #      BR-BACKEND-007 (404 when rowcount == 0)
    # Transaction: single DELETE + commit (only if row found)
    # ------------------------------------------------------------------
    async def delete_note(self, note_id: int) -> None:
        """Delete a note by primary key.

        BR-BACKEND-003: note_id is guaranteed > 0 by the router Path(..., gt=0).
        BR-BACKEND-007: raises HTTP 404 if no row was deleted (legacy changed to
          correct REST behaviour — pending SME confirmation per comprehension doc).
        """
        result = await self._db.execute(
            delete(Note).where(Note.id == note_id)
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found",
            )
        await self._db.commit()
```

### Service factory dependency

```python
# services/note_service.py (continued)
from fastapi import Depends
from app.db.session import get_db


async def get_note_service(
    db: AsyncSession = Depends(get_db),
) -> NoteService:
    """FastAPI dependency factory — constructs NoteService per request."""
    return NoteService(db)
```

### Method summary table

| Method | BRs | Transaction | Raises |
|--------|-----|-------------|--------|
| `list_notes()` | BR-005, BR-008 | Read-only — no commit | — |
| `create_note(content: str)` | BR-001, BR-002, BR-006 (via schema pre-call) | INSERT + flush + refresh + commit | — |
| `delete_note(note_id: int)` | BR-003 (router), BR-007 | DELETE + commit (if found) | `HTTPException(404)` when `rowcount == 0` |

### Complete router implementation

```python
# routers/notes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, status

from app.schemas.note_schemas import NoteCreate, NoteRead
from app.services.note_service import NoteService, get_note_service

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get(
    "",
    response_model=list[NoteRead],
    status_code=status.HTTP_200_OK,
    summary="List all notes",
)
async def list_notes(
    service: NoteService = Depends(get_note_service),
) -> list[NoteRead]:
    """
    Return all notes ordered newest-first.

    BRs: BR-BACKEND-005 (ORDER BY created_at DESC), BR-BACKEND-008 (no pagination).
    Auth: none (BR-BACKEND-004).
    """
    notes = await service.list_notes()
    return [NoteRead.model_validate(n) for n in notes]


@router.post(
    "",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note",
)
async def create_note(
    body: NoteCreate,
    service: NoteService = Depends(get_note_service),
) -> NoteRead:
    """
    Create a new note.

    BRs enforced by NoteCreate schema:
      BR-BACKEND-006: strip whitespace (mode='before' validator)
      BR-BACKEND-001: reject empty content after strip
      BR-BACKEND-002: reject content > 500 characters after strip
    Auth: none (BR-BACKEND-004).
    """
    note = await service.create_note(content=body.content)
    return NoteRead.model_validate(note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
)
async def delete_note(
    note_id: int = Path(..., gt=0, description="ID of the note to delete"),
    service: NoteService = Depends(get_note_service),
) -> None:
    """
    Delete a note by ID.

    BR-BACKEND-003: note_id must be a positive integer (gt=0); FastAPI returns
      422 automatically for non-integer or <= 0 values.
    BR-BACKEND-007: returns 404 if no note with that ID exists.
    Auth: none (BR-BACKEND-004).
    """
    await service.delete_note(note_id=note_id)
```

### Application factory

```python
# main.py
from fastapi import FastAPI
from app.routers.notes import router as notes_router

app = FastAPI(title="Note List API", version="1.0.0")
app.include_router(notes_router)
```

---

## §6 — Risk Register and Mitigations

### RISK-BACKEND-001: GLOBAL-VAR — Global database connection coupling

**Source behaviour:**
PHP uses `global $conn` — a module-level variable holding a single `mysql_connect()` result. Every function calls `global $conn` to access this shared connection. There is no connection pooling, no per-request lifecycle, and no cleanup on request end. All functions share and mutate the same connection object.

**Target implementation:**
FastAPI dependency injection via `get_db()` yields a new `AsyncSession` scoped to each individual request. The session is automatically closed when the request completes (via the `async with async_session_factory()` context manager). No module-level session objects exist anywhere in the codebase.

```python
# Correct pattern — one session per request, never global:
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

@router.get("/notes")
async def list_notes(service: NoteService = Depends(get_note_service)):
    # service._db is a fresh AsyncSession for this request only
    return await service.list_notes()
```

Do NOT use:
```python
# WRONG — global session, DO NOT DO THIS:
session = async_session_factory()   # module-level singleton

# WRONG — class-level shared session:
class NoteService:
    _db = async_session_factory()   # shared across all instances
```

**Validation approach:** Integration test: fire two concurrent `GET /notes` requests; assert both complete without `sqlalchemy.exc.InvalidRequestError` or session-reuse errors. Assert `NoteService._db` is a distinct object per request by logging `id(session)` — values must differ.

---

### RISK-BACKEND-002: RAW-SQL-CONCAT — SQL injection via string interpolation

**Source behaviour:**
PHP constructs all SQL via direct string concatenation of user input:
```php
$query = "INSERT INTO notes (content) VALUES ('" . $content . "')";
mysql_query($query, $conn);
```
A note content of `'); DROP TABLE notes; --` would execute as a second SQL statement, destroying all data.

**Target implementation:**
All queries use SQLAlchemy ORM statement objects. User-supplied values are automatically parameterised — they are never interpolated into SQL strings.

```python
# CORRECT — parameterised via ORM INSERT:
note = Note(content=content)    # content bound as parameter at execution
self._db.add(note)

# CORRECT — parameterised DELETE:
await self._db.execute(
    delete(Note).where(Note.id == note_id)   # note_id bound as parameter
)
```

Do NOT use:
```python
# WRONG — text() with f-string interpolation:
await self._db.execute(text(f"DELETE FROM notes WHERE id = {note_id}"))

# WRONG — any string concatenation in SQL:
await self._db.execute(text("INSERT INTO notes (content) VALUES ('" + content + "')"))
```

**Validation approach:**
1. Static analysis: run `bandit -r app/` — assert zero `B608` (hardcoded SQL) findings.
2. Integration test: create a note with `content = "'); DROP TABLE notes; --"` → assert `201 Created`, assert `GET /notes` still returns the literal string, assert table is intact.

---

### RISK-BACKEND-003: DIRECT-OUTPUT — Business logic mixed with HTML rendering

**Source behaviour:**
PHP functions like `add_note()` perform the database INSERT and immediately echo HTML (`<li>` elements). Business logic and presentation are intertwined in the same function. There is no separation between data manipulation and output generation.

**Target implementation:**
Strict three-layer separation enforced by file structure:

```
app/
  routers/notes.py          ← HTTP: path params, status codes, JSON serialisation
  services/note_service.py  ← Business logic: BR enforcement, transactions
  models/note.py            ← Data access: ORM model only
```

Routers return Pydantic models (serialised to JSON). No HTML is generated anywhere in the backend. The frontend is responsible for all HTML rendering.

**Validation approach:** Code review — grep backend source for HTML literals:
```powershell
Select-String "<[a-zA-Z]" (Get-ChildItem app -Recurse -Filter "*.py").FullName
```
Assert zero matches. Confirm all route handlers are typed to return Pydantic response models, not `str` or `dict`.

---

### RISK-BACKEND-004: DATE-INTERPOLATION — PHP date formatting in output

**Source behaviour:**
PHP formats `created_at` inside the response generation:
```php
echo date('Y-m-d H:i', strtotime($row['created_at']));
```
The backend hard-codes a display format, coupling presentation to the API contract.

**Target implementation:**
`NoteRead.created_at` is typed as `datetime`. Pydantic v2 serialises a timezone-aware `datetime` to ISO 8601 format automatically (e.g., `"2026-05-19T14:30:00+00:00"`). The backend never calls `strftime()`. The frontend formats `created_at` for display according to locale/preference.

```python
class NoteRead(BaseModel):
    id: int
    content: str
    created_at: datetime   # → "2026-05-19T14:30:00+00:00" in JSON output
    model_config = model_config(from_attributes=True)
```

**Validation approach:** Integration test — create a note, `GET /notes`, assert `created_at` matches ISO 8601 regex:
```python
import re
assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", note["created_at"])
```
Assert no `strftime` calls in backend source:
```powershell
Select-String "strftime" (Get-ChildItem app -Recurse -Filter "*.py").FullName
```

---

### RISK-BACKEND-005: NULL-RETURN — Silent success on delete of non-existent ID

**Source behaviour:**
PHP `delete_note()` returns `['ok' => true]` regardless of `mysql_affected_rows()`. No distinction between "deleted successfully" and "row did not exist." Any consumer calling this endpoint for a non-existent ID receives a false success response.

**Target implementation:**
After executing the `DELETE` statement, check `result.rowcount`. If zero rows were affected, the note did not exist — raise `HTTPException(status_code=404)`. This is a deliberate behavioural change from legacy (BR-BACKEND-007 — flagged as ambiguity, planning adopts 404 per comprehension doc recommendation, pending SME confirmation).

```python
result = await self._db.execute(
    delete(Note).where(Note.id == note_id)
)
if result.rowcount == 0:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Note not found",
    )
await self._db.commit()
```

Do NOT use:
```python
# WRONG — silently returns success regardless:
await self._db.execute(delete(Note).where(Note.id == note_id))
await self._db.commit()
return {"ok": True}
```

**Validation approach:**
- Integration test A: `DELETE /notes/99999` (non-existent ID) → assert `404 Not Found`, body `{"detail": "Note not found"}`.
- Integration test B: Create a note, `DELETE /notes/{id}` → assert `204 No Content`, `GET /notes` returns empty list.
- Integration test C: `DELETE /notes/{id}` twice → first returns `204`, second returns `404`.

---

### RISK-BACKEND-006: DEPRECATED-EXT — `mysql_*` functions removed in PHP 7

**Source behaviour:**
The entire data access layer uses `mysql_connect()`, `mysql_query()`, `mysql_fetch_assoc()`, `mysql_num_rows()`, `mysql_affected_rows()` — all removed in PHP 7.0. The source is unmaintainable on any modern PHP runtime.

**Target implementation:**
Replaced entirely by SQLAlchemy 2.x async engine with `asyncpg` PostgreSQL driver. No `pymysql`, no `psycopg2`, no synchronous SQLAlchemy.

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host:5432/notes",
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)
```

Required packages in `requirements.txt`:
```
fastapi>=0.111.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
pydantic>=2.0.0
uvicorn[standard]>=0.29.0
```

**Validation approach:** Assert `requirements.txt` contains no `mysql`, `pymysql`, `MySQLdb`, or `psycopg2` entries. Run `pytest` against a live PostgreSQL test instance — all queries succeed.

---

### RISK-BACKEND-007: STRLEN-MULTIBYTE — Byte-count vs character-count mismatch

**Source behaviour:**
PHP `strlen()` counts bytes, not characters. For ASCII text, bytes == characters. For UTF-8 multi-byte characters (emoji 4 bytes, CJK 3 bytes), byte count > character count. A 500-byte PHP limit therefore rejects content that fits in 500 characters but uses multi-byte encoding.

**Target implementation:**
Python `len()` counts Unicode code points (characters). Pydantic's `max_length=500` uses `len()`. A string of 500 emoji characters (2,000 bytes in UTF-8) would be accepted by Python but rejected by PHP.

Planning adopts character-length semantics (BR-BACKEND-002 ambiguity resolution). This is the Python-native behaviour and the recommended resolution. If SME confirms byte-length is required, the validator can be overridden:

```python
# Override only if byte-length semantics confirmed:
@field_validator("content", mode="after")
@classmethod
def content_byte_length(cls, v: str) -> str:
    if len(v.encode("utf-8")) > 500:
        raise ValueError("Note content exceeds 500 bytes")
    return v
```

Default implementation uses character-length — no override needed unless SME corrects this.

**Validation approach:**
- Unit test A: `NoteCreate(content="a" * 500)` → valid.
- Unit test B: `NoteCreate(content="a" * 501)` → `ValidationError`.
- Unit test C: `NoteCreate(content="😀" * 500)` (500 emoji, 2000 UTF-8 bytes) → valid (character semantics) or rejected (byte semantics).

---

### RISK-BACKEND-008: NO-CSRF — No CSRF protection

**Source behaviour:**
No CSRF protection in the PHP source.

**Target implementation:**
No action required. The FastAPI JSON API is not subject to CSRF attacks because:
1. No cookie-based authentication exists (BR-BACKEND-004 — deliberate design).
2. All mutation endpoints (`POST /notes`, `DELETE /notes/{id}`) require `Content-Type: application/json` body or path parameter — not form-encoded data.
3. Cross-origin requests are blocked by standard browser CORS policy unless explicitly permitted via `CORSMiddleware`.

Do NOT add CSRF middleware, CSRF tokens, or `SameSite` cookie configuration — there are no cookies to protect.

**Validation approach:** Verify no CSRF or session middleware is registered in `main.py`. Confirm `CORSMiddleware` (if added) uses an explicit origin allowlist matching the frontend origin only.

---

## §7 — Cross-Module Stubs (if applicable)

N/A — no cross-module dependencies.

The comprehension document (Section 4) confirms this module has zero cross-module dependencies. The legacy source is a single-file PHP application with no shared includes, session objects, authentication modules, or external service calls.

No stub classes are required. The `notes` module is fully self-contained and can be developed, tested, and deployed in isolation.

---

## §8 — Data Migration (if applicable)

N/A — schema created fresh.

The target PostgreSQL database is provisioned new for this migration. The `notes` table is created via the DDL in §1 at application startup (via SQLAlchemy `Base.metadata.create_all()` or Alembic migration). No existing MySQL data is ported as part of this MWU.

For reference only — if historical data migration is requested in a future MWU:

| MySQL column | MySQL type | PostgreSQL type | Conversion notes |
|---|---|---|---|
| `id` | `INT AUTO_INCREMENT` | `BIGSERIAL` / `BIGINT` | Preserve existing IDs; reset sequence to `MAX(id) + 1` after import |
| `content` | `VARCHAR(500)` | `VARCHAR(500)` | Character semantics match at ASCII range; verify UTF-8 encoding on MySQL source |
| `created_at` | `DATETIME` (no timezone) | `TIMESTAMPTZ` | Apply UTC assumption on import; `AT TIME ZONE 'UTC'` cast in migration SQL |

Migration SQL skeleton (for future use only — not required for this MWU):
```sql
-- Future data migration — NOT part of MWU-NL2-001
INSERT INTO notes (id, content, created_at)
SELECT
    id,
    content,
    created_at AT TIME ZONE 'UTC'   -- MySQL DATETIME assumed UTC
FROM mysql_fdw_notes;               -- via postgres_fdw or pre-exported CSV

-- Reset sequence after bulk insert:
SELECT setval('notes_id_seq', (SELECT MAX(id) FROM notes));
```

---

## §9 — Test Strategy

### BR test matrix

| BR ID | Test type | Scenario | Expected result |
|-------|-----------|----------|-----------------|
| BR-BACKEND-001 | Unit | `NoteCreate(content="")` | `ValidationError`: "Note cannot be empty" |
| BR-BACKEND-001 | Unit | `NoteCreate(content="   ")` | `ValidationError`: "Note cannot be empty" (empty after strip) |
| BR-BACKEND-001 | Unit | `NoteCreate(content="\t\n")` | `ValidationError`: "Note cannot be empty" (tabs/newlines stripped) |
| BR-BACKEND-001 | Integration | `POST /notes` `{"content": ""}` | `422 Unprocessable Entity` |
| BR-BACKEND-002 | Unit | `NoteCreate(content="a" * 500)` | Valid — 500-char accepted |
| BR-BACKEND-002 | Unit | `NoteCreate(content="a" * 501)` | `ValidationError`: exceeds 500 characters |
| BR-BACKEND-002 | Unit | `NoteCreate(content="  " + "a" * 499 + "  ")` | Valid — stripped to 499 chars |
| BR-BACKEND-002 | Integration | `POST /notes` with 501-char content | `422 Unprocessable Entity` |
| BR-BACKEND-003 | Integration | `DELETE /notes/0` | `422 Unprocessable Entity` |
| BR-BACKEND-003 | Integration | `DELETE /notes/-1` | `422 Unprocessable Entity` |
| BR-BACKEND-003 | Integration | `DELETE /notes/-999` | `422 Unprocessable Entity` |
| BR-BACKEND-003 | Integration | `DELETE /notes/abc` | `422 Unprocessable Entity` |
| BR-BACKEND-003 | Integration | `DELETE /notes/1.5` | `422 Unprocessable Entity` |
| BR-BACKEND-004 | Code review | Search for auth imports in all backend files | Zero: no `OAuth2`, `JWT`, `get_current_user`, `HTTPBearer` |
| BR-BACKEND-004 | Integration | `POST /notes` with no Authorization header | `201 Created` (no auth required) |
| BR-BACKEND-004 | Integration | `DELETE /notes/1` with no Authorization header | `204 No Content` (no auth required) |
| BR-BACKEND-005 | Integration | Create 3 notes at different times; `GET /notes` | List ordered newest-first by `created_at` |
| BR-BACKEND-005 | Integration | `GET /notes?sort=asc` (unsupported param) | `200 OK`, still ordered newest-first (param ignored) |
| BR-BACKEND-006 | Unit | `NoteCreate(content="  hello  ")` | `content == "hello"` (stripped) |
| BR-BACKEND-006 | Unit | `NoteCreate(content="\thello\n")` | `content == "hello"` (stripped) |
| BR-BACKEND-006 | Unit | `NoteCreate(content="  a" * 168)` | `content == "a" * 168` — max_length check on stripped value |
| BR-BACKEND-007 | Integration | `DELETE /notes/99999` (not in DB) | `404 Not Found`, `{"detail": "Note not found"}` |
| BR-BACKEND-007 | Integration | Create note; `DELETE /notes/{id}` | `204 No Content`; note absent from subsequent `GET /notes` |
| BR-BACKEND-007 | Integration | Create note; delete twice | First `DELETE` → `204`; second `DELETE` → `404` |
| BR-BACKEND-008 | Integration | Seed 1000 notes; `GET /notes` | `200 OK`, all 1000 returned |
| BR-BACKEND-008 | Integration | `GET /notes?page=1&limit=10` (unsupported) | `200 OK`, all notes returned (params ignored) |
| BR-BACKEND-008 | Code review | Search list query for LIMIT/OFFSET | Zero occurrences in `note_service.py` |

### Happy path coverage

| Flow | Test scenario | Expected result |
|------|---------------|-----------------|
| Create single note | `POST /notes` `{"content": "Hello"}` | `201`, response contains `id`, `content`, `created_at` |
| List notes — empty | Fresh DB; `GET /notes` | `200`, `[]` |
| List notes — populated | Create 3 notes; `GET /notes` | `200`, 3 notes newest-first |
| Delete existing note | Create note; `DELETE /notes/{id}` | `204`; note gone from `GET /notes` |
| Full flow | Create 3 notes → `GET /notes` (assert order) → `DELETE` middle note → `GET /notes` (assert 2 remain, still ordered) | Passes at each step |

### Key fixtures

```python
# tests/conftest.py
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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

| Edge case | Test input | Expected behaviour |
|-----------|------------|-------------------|
| Whitespace variants (space, tab, newline, CRLF) | `"\t"`, `"\n"`, `"\r\n"`, `" "` | All rejected as empty after strip |
| Exactly 500 characters | `"a" * 500` | Accepted |
| Exactly 501 characters | `"a" * 501` | Rejected with 422 |
| Leading/trailing spaces within 500 limit | `"  " + "a" * 498 + "  "` | Stripped to 498 chars — accepted |
| Leading/trailing spaces pushing over 500 | `"  " + "a" * 500 + "  "` | Stripped to 500 chars — accepted |
| SQL injection in content | `"'); DROP TABLE notes; --"` | Stored as literal string; table intact |
| Multi-byte emoji content (500 chars) | `"😀" * 500` | Accepted (character semantics) |
| Delete on ID 1 (boundary) | `DELETE /notes/1` | `204` if exists, `404` if not |
| Delete on non-integer path | `DELETE /notes/not-an-id` | `422` from FastAPI |
| List after all notes deleted | Create 2, delete both, `GET /notes` | `200`, `[]` |

### Test configuration

```toml
# pyproject.toml [tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

# Required test dependencies:
# pytest>=8.0
# pytest-asyncio>=0.23
# httpx>=0.27
# pytest-cov>=5.0
```




---
# COMPREHENSION ANALYSIS

# Comprehension Report — MWU-NL2-001 Backend
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** 2026-05-19
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md (4 source files, complexity LOW)
**Rules extracted:** 8 business rules
**MKB artifacts stored:** 8 UUIDs (pre-existing from 2026-05-18 session — verified, not duplicated)

---

## 1. Business Rule Catalog

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-BACKEND-001 | Notes with empty content (after trim) MUST NOT be saved. Whitespace-only content is treated as empty and rejected with "Note cannot be empty". Pydantic `field_validator` on `NoteCreate.content` — `raise ValueError` if `not v.strip()`. DB `NOT NULL` enforces non-null but not non-empty; application layer must enforce. | VALIDATION | `index.php:24-26` | HIGH | None | `0528c666-adea-4e83-b25c-26e856c7c9cf` |
| BR-BACKEND-002 | Note content limited to 500 characters. `MAX_NOTE_LENGTH=500` matches DB `VARCHAR(500)`. PHP `strlen()` counts bytes; Python `len()` counts characters — limit semantics differ for multi-byte content. | VALIDATION | `index.php:4,27-29`; `schema.sql:6` | HIGH | **NEEDS_VALIDATION**: 500 bytes or 500 characters? Recommend character-length (Python default). | `34087b7b-b66e-40cd-96dd-442213445a31` |
| BR-BACKEND-003 | Delete operations require a positive integer ID (`> 0`). IDs ≤ 0 rejected with "Invalid note ID". Non-integer values cast to 0 by PHP and therefore also rejected. FastAPI: `id: int = Path(..., gt=0)` + 422 for non-integer. | VALIDATION | `index.php:37-40` | HIGH | None | `1947fa5b-abfe-4cd9-b386-c7a597cb1a19` |
| BR-BACKEND-004 | **CRITICAL — No authentication.** Zero auth, session management, or access control. All endpoints fully public by design. Do NOT add `Depends(get_current_user)`, OAuth2, JWT, or session middleware. | AUTHORIZATION | `index.php` (confirmed absence) | CRITICAL | None — deliberate design choice | `fd577753-026c-4151-a1d2-1f87e74fc483` |
| BR-BACKEND-005 | Notes listed newest first: `ORDER BY created_at DESC`. Only supported sort order; no sort parameter accepted. | CONSTRAINT | `index.php:10-13` | MEDIUM | None | `6ac173aa-2ad5-4d17-adf1-f64efbf16179` |
| BR-BACKEND-006 | Content is `trim()`-ed before validation and storage. Leading/trailing whitespace silently stripped. Empty check (BR-001) and length check (BR-002) operate on the trimmed value. Apply `strip()` in Pydantic `field_validator(mode='before')`. | TRANSFORMATION | `index.php:23` | MEDIUM | None | `09dbfde6-f2f6-4323-9717-941cf7944ff8` |
| BR-BACKEND-007 | Legacy `delete_note()` returns `['ok' => true]` even when no row matched (silent success on non-existent ID). FastAPI SHOULD raise `HTTPException(404)` when `result.rowcount == 0` — correct REST behaviour. | WORKFLOW | `index.php:41-43` | HIGH | **NEEDS_VALIDATION**: Confirm 404 on missing delete is acceptable (behavioural change from legacy). | `3feb915f-7a1a-4841-9e16-7fe16de9724e` |
| BR-BACKEND-008 | List endpoint returns all notes — no LIMIT, no OFFSET. Intentional for small data volume (< 1000 rows). Do NOT add pagination silently. | CONSTRAINT | `index.php:8-19` | LOW | None | `1414443f-545e-4e39-b78a-df085756454b` |

### Rule Type Distribution
- VALIDATION: 3 (BR-001, BR-002, BR-003)
- AUTHORIZATION: 1 (BR-004)
- CONSTRAINT: 2 (BR-005, BR-008)
- TRANSFORMATION: 1 (BR-006)
- WORKFLOW: 1 (BR-007)

---

## 2. Implementation Notes for CodeGen Agent

### RISK-BACKEND-001: GLOBAL-VAR — Global database connection coupling
**Severity:** HIGH
**What to do:** Replace all `global $conn` usage with FastAPI `AsyncSession` dependency injection via `get_db()`.
**Pattern to use:**
```python
async def list_notes(db: AsyncSession = Depends(get_db)) -> list[NoteRead]:
    result = await db.execute(select(Note).order_by(Note.created_at.desc()))
    return result.scalars().all()
```
**Do NOT:** Use module-level global session objects or singleton patterns.

### RISK-BACKEND-002: RAW-SQL-CONCAT — SQL injection via string interpolation
**Severity:** HIGH
**What to do:** Use SQLAlchemy ORM queries exclusively. All user-supplied values MUST be parameterised.
**Pattern to use:**
```python
stmt = insert(Note).values(content=content)
result = await db.execute(stmt)
```
**Do NOT:** Use `text()` with string concatenation. Never interpolate user input into SQL strings.

### RISK-BACKEND-003: DIRECT-OUTPUT — Business logic mixed with HTML
**Severity:** MEDIUM
**What to do:** Separate into Router (HTTP handling) → Service (business logic) → ORM (data access). Router returns JSON; no HTML rendering in backend MWU.
**Pattern to use:** Three-layer architecture: `routers/notes.py` → `services/note_service.py` → `models/note.py`.
**Do NOT:** Put business logic in route handlers. Do NOT generate HTML from the backend API.

### RISK-BACKEND-004: DATE-INTERPOLATION — PHP date formatting in output
**Severity:** MEDIUM
**What to do:** Return `created_at` as ISO 8601 datetime from the API. Frontend formats for display.
**Pattern to use:** Pydantic `NoteRead` model with `created_at: datetime` — serialises to ISO 8601 automatically.
**Do NOT:** Format dates in the backend response. No `strftime()` in the router or service layer.

### RISK-BACKEND-005: NULL-RETURN — Silent success on delete of non-existent ID
**Severity:** MEDIUM
**What to do:** After `DELETE`, check `result.rowcount`. If 0, raise `HTTPException(status_code=404, detail="Note not found")`. See BR-BACKEND-007 — pending product owner validation.
**Pattern to use:**
```python
result = await db.execute(delete(Note).where(Note.id == note_id))
if result.rowcount == 0:
    raise HTTPException(status_code=404, detail="Note not found")
await db.commit()
```
**Do NOT:** Silently return 200/204 when the target row doesn't exist.

### RISK-BACKEND-006: DEPRECATED-EXT — `mysql_*` functions removed in PHP 7
**Severity:** HIGH
**What to do:** Replace entirely with SQLAlchemy 2.x async engine using `asyncpg` driver.
**Pattern to use:**
```python
engine = create_async_engine("postgresql+asyncpg://...", echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```
**Do NOT:** Use synchronous SQLAlchemy or raw `psycopg2`.

### RISK-BACKEND-007: STRLEN-MULTIBYTE — Byte-count vs character-count mismatch
**Severity:** LOW
**What to do:** Use Python `len()` (character-count) for the 500-character limit. This is the natural Python behaviour and likely the intended semantics. Pending product owner confirmation (BR-BACKEND-002).
**Pattern to use:** `content: str = Field(..., max_length=500)` in Pydantic — character-length by default.
**Do NOT:** Encode to UTF-8 and count bytes to replicate PHP `strlen()` behaviour — this would be a regression for multi-byte users.

### RISK-BACKEND-008: NO-CSRF — No CSRF protection
**Severity:** LOW
**What to do:** No action required. FastAPI REST API with JSON body is not subject to browser CSRF when using fetch/XHR (no cookie-based auth exists per BR-BACKEND-004).
**Do NOT:** Add CSRF middleware or tokens. No cookie auth will be added.

---

## 3. Ambiguities Requiring SME Resolution

| ID | Question | Discovery Source | Impact if Wrong |
|----|----------|-----------------|-----------------|
| BR-BACKEND-002 | Should the 500-character limit count characters (Python `len()`) or bytes (PHP `strlen()`)? Recommend characters. | `index.php:27`, R-007 | Multi-byte content (emoji, CJK) that fits in 500 characters but exceeds 500 bytes would be rejected if byte-counting is preserved. Low impact for English-only usage. |
| BR-BACKEND-007 | Should DELETE on a non-existent note return 404 (correct REST) or 204 (legacy silent-success behaviour)? Recommend 404. | `index.php:41-43`, R-005 | If any consumer depends on silent success, switching to 404 is a breaking change. Low risk — no known API consumers exist for this single-user app. |

---

## 4. Cross-Module Dependencies

| BR ID | Depends on | Module | Status |
|-------|-----------|--------|--------|
| — | — | — | — |

**No cross-module dependencies.** This is a self-contained single-module application with no shared includes, sessions, or auth.

---

## 5. MKB Storage Summary

Total rules stored: 8
MKB module: backend
Project ID: NOTE-LIST-2
Status: EXTRACTED (pending HITL validation)
Storage date: 2026-05-18 (verified 2026-05-19 — all rules present, no duplicates)
Cross-validation: 0 contradictions found

| Rule ID | MKB UUID | Confidence |
|---------|----------|------------|
| BR-BACKEND-001 | `0528c666-adea-4e83-b25c-26e856c7c9cf` | HIGH |
| BR-BACKEND-002 | `34087b7b-b66e-40cd-96dd-442213445a31` | HIGH |
| BR-BACKEND-003 | `1947fa5b-abfe-4cd9-b386-c7a597cb1a19` | HIGH |
| BR-BACKEND-004 | `fd577753-026c-4151-a1d2-1f87e74fc483` | HIGH |
| BR-BACKEND-005 | `6ac173aa-2ad5-4d17-adf1-f64efbf16179` | HIGH |
| BR-BACKEND-006 | `09dbfde6-f2f6-4323-9717-941cf7944ff8` | HIGH |
| BR-BACKEND-007 | `3feb915f-7a1a-4841-9e16-7fe16de9724e` | MEDIUM |
| BR-BACKEND-008 | `1414443f-545e-4e39-b78a-df085756454b` | HIGH |

To retrieve for CodeGen:
```
mkb_get_business_rules(module="backend", status="VALIDATED", project_id="NOTE-LIST-2")
```

---

## 6. Reviewer Checklist

- [x] All 8 BRs from discovery Section 7 are captured
- [x] Each BR has a clear, implementation-ready description
- [x] All 8 risk register items from Section 8 are translated to CodeGen instructions
- [x] Ambiguities flagged (BR-002 byte/char, BR-007 silent-success) — not silently assumed
- [x] MKB UUIDs recorded for all 8 rules — traceability complete
- [x] Cross-module dependencies identified (none — self-contained module)
- [x] Cross-validation executed — 0 contradictions
- [x] Pipeline lesson applied: verified MKB tools active and all BRs stored (not PENDING_MKB_WRITE)

---

## 7. Pipeline Lesson Applied

**Lesson:** `bd5b94b1` — Comprehension agent must verify `--allowedTools` includes `mkb_store_artifact`. If comprehension doc shows `PENDING_MKB_WRITE`, BRs were never stored, causing codegen to hallucinate.

**Action taken:** Queried `mkb_get_business_rules(module="backend")` — confirmed all 8 BRs are stored with valid UUIDs and non-pending status. No backfill needed.



======================================================================
## SUPPORTING CONTEXT
======================================================================

## sonar-issues
{
  "module": "backend",
  "sonar_path": "backend",
  "total": 0,
  "by_severity": {},
  "top_issues": []
}

## REVISION NOTES — RETRY 1 OF 5
The previous codegen attempt FAILED self-review with these issues:
1. migrations/001_initial.sql:4 — 'id BIGSERIAL PRIMARY KEY' uses a deprecated SERIAL-family pseudo-type; DDL rule mandates 'id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY' (GENERATED ALWAYS AS IDENTITY, not SERIAL/BIGSERIAL)
2. tests/modules/notes/test_notes.py — 'pytest_asyncio' is never imported in this file; every '@pytest_asyncio.async_test' decorator raises NameError at collection time, causing the entire test file to fail to load
3. tests/modules/notes/test_notes.py — '@pytest_asyncio.async_test' is a fabricated/non-existent API; the correct marker is '@pytest.mark.asyncio'; even if the import were added, every async test method in TestNoteService and TestNoteEndpoints would raise AttributeError and not execute

THIS IS A RETRY RUN — SKIP STEP 1. BEGIN GENERATING FILES IMMEDIATELY.
Fix all issues listed above. Rewrite affected files completely.
