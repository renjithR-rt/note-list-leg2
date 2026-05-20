# Comprehension Report — MWU-NL2-001 Backend
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** 2026-05-20
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md (4 source files, complexity LOW)
**Rules extracted:** 10 business rules
**MKB artifacts stored:** 10 UUIDs

---

## 1. Business Rule Catalog

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-BACKEND-001 | Note content after trim() must not be empty; rejected with "Note cannot be empty" | VALIDATION | index.php:23-26 (add_note) | HIGH | None | ef333461-d5bf-4185-baf7-2cb1cad53f26 |
| BR-BACKEND-002 | Note content must not exceed 500 characters (MAX_NOTE_LENGTH); rejected with "Note too long (max 500 chars)" | VALIDATION | index.php:27-29 (add_note) | HIGH | PHP strlen() counts bytes vs Python chars — see Ambiguity #1 | 8e2cb74c-b837-4744-9ba3-fabfcf1a8d4f |
| BR-BACKEND-003 | Content is trimmed (whitespace stripped) BEFORE empty check and length check; trimmed value is stored | TRANSFORMATION | index.php:23 (add_note) | MEDIUM | None | 7b5e07f8-d010-4a62-9c75-24981e20f853 |
| BR-BACKEND-004 | Delete rejects note IDs that are zero or negative after integer cast | VALIDATION | index.php:37-40 (delete_note) | HIGH | None | 474c33ea-bf41-4a33-a7f4-48516bc38dfc |
| BR-BACKEND-005 | Delete on non-existent (but valid) note ID must return 404 — GAP REMEDIATION (legacy returns ok:true silently) | CONSTRAINT | index.php:35-43 (delete_note) | HIGH | Behaviour change — see Ambiguity #2 | 5a2af8de-026c-4fd9-acfb-f7348bfdace8 |
| BR-BACKEND-006 | **CRITICAL**: All endpoints are public — zero authentication, zero authorization. Adding any auth is a regression. | AUTHORIZATION | index.php (entire file) | CRITICAL | None | 86e22203-23d2-4de8-94f2-fcbbcdee547a |
| BR-BACKEND-007 | Notes always returned in descending creation order (newest first); no user-configurable sort | CONSTRAINT | index.php:11 (get_notes) | MEDIUM | None | b28fe766-5a7b-4247-9ce9-2452e9b6a5b4 |
| BR-BACKEND-008 | Note content stored/retrieved as UTF-8; MySQL 3-byte utf8 upgrades to PostgreSQL 4-byte UTF-8 | CONSTRAINT | db.php:10, db/schema.sql | LOW | None | ca362b1c-1775-4d14-9d24-6f66a30186ea |
| BR-BACKEND-009 | created_at is auto-set by database (DEFAULT CURRENT_TIMESTAMP); never supplied by application layer | CONSTRAINT | db/schema.sql:7, index.php:31 | LOW | None | ed761a82-0b76-4b48-a63f-4422a0d8bf58 |
| BR-BACKEND-010 | DB credentials read from environment variables (DB_HOST, DB_USER, DB_PASS, DB_NAME) with hardcoded fallbacks in legacy | CONSTRAINT | db.php:2-5 | LOW | None | 6c7d8a7a-d22a-4de0-84c5-5ee6b495624d |

### Validation Chain (BR-003 → BR-001 → BR-002)

The three validation BRs execute in strict order:
1. **BR-003** strip whitespace
2. **BR-001** reject if empty
3. **BR-002** reject if > 500 chars

CodeGen must implement these as a single Pydantic validator chain, not independent checks.

---

## 2. Implementation Notes for CodeGen Agent

### RISK-BACKEND-001: HIGH — mysql_* Extension Removal
**What to do:** Rewrite the entire Data Access Layer using SQLAlchemy 2.x async ORM. All three PHP functions (`get_notes`, `add_note`, `delete_note`) become async service methods with `AsyncSession` dependency injection.
**Pattern to use:** `async def list_notes(db: AsyncSession) -> list[Note]` with `select(Note).order_by(Note.created_at.desc())`
**Do NOT:** Use any compatibility shim, raw `text()` queries, or synchronous SQLAlchemy. No `mysql_*` function equivalents exist.

### RISK-BACKEND-002: MEDIUM — Global Connection State
**What to do:** Replace `global $conn` with FastAPI `Depends(get_db)` pattern. The `get_db()` function yields an `AsyncSession` from a session factory.
**Pattern to use:** `async def get_db() -> AsyncGenerator[AsyncSession, None]: async with async_session() as session: yield session`
**Do NOT:** Use module-level global connection objects, connection pooling outside SQLAlchemy's built-in pool, or store sessions in app state.

### RISK-BACKEND-003: HIGH — Raw SQL Concatenation
**What to do:** Replace ALL `mysql_real_escape_string` + string interpolation with SQLAlchemy parameterized queries. This eliminates SQL injection risk entirely.
**Pattern to use:** `session.execute(insert(Note).values(content=data.content))` or ORM `session.add(Note(content=data.content))`
**Do NOT:** Use `text()` with f-string interpolation. Never concatenate user input into SQL strings. Never use `mysql_real_escape_string` equivalent.

### RISK-BACKEND-004: MEDIUM — DELETE via HTTP GET
**What to do:** Legacy uses `GET /?delete=N` for deletion. FastAPI must use `DELETE /api/notes/{id}` with proper HTTP method semantics.
**Pattern to use:** `@router.delete("/api/notes/{note_id}", status_code=204)`
**Do NOT:** Accept deletion via GET parameters. Coordinate with MWU-NL2-002-FE to ensure frontend sends DELETE requests.

### RISK-BACKEND-005: LOW — mysql_insert_id Replacement
**What to do:** After inserting a note, retrieve the auto-generated ID using SQLAlchemy's built-in mechanisms.
**Pattern to use:** `session.add(note); await session.flush(); await session.refresh(note)` — `note.id` is now populated.
**Do NOT:** Use `text("SELECT lastval()")` or any manual ID retrieval. Do NOT use RETURNING clause manually — let SQLAlchemy handle it.

### RISK-BACKEND-006: LOW — strlen Byte vs Character Count
**What to do:** PHP `strlen()` counts bytes; PostgreSQL `VARCHAR(500)` and Pydantic `max_length=500` both count characters. For pure ASCII content the behaviour is identical. For multi-byte Unicode content, the Python/PG behaviour is more permissive (allows longer byte sequences).
**Pattern to use:** `content: str = Field(max_length=500)` — character count is the correct semantic.
**Do NOT:** Implement byte-length checking to match PHP behaviour. Character-count is the intended semantics.

### RISK-BACKEND-007: MEDIUM — No Row-Not-Found Check on Delete
**What to do:** Add a 404 check when delete affects zero rows. This is a GAP REMEDIATION (see BR-BACKEND-005).
**Pattern to use:** `result = await session.execute(delete(Note).where(Note.id == note_id)); if result.rowcount == 0: raise HTTPException(404, "Note not found")`
**Do NOT:** Silently return success when no row was deleted (legacy behaviour).

### RISK-BACKEND-008: LOW — DATETIME to TIMESTAMPTZ
**What to do:** MySQL `DATETIME` (no timezone) becomes PostgreSQL `TIMESTAMP WITH TIME ZONE`. Existing seed data timestamps are treated as UTC.
**Pattern to use:** `mapped_column(DateTime(timezone=True), server_default=func.now())`
**Do NOT:** Use `DateTime()` without `timezone=True`. Do NOT use `init=False` in `mapped_column()` — raises `InvalidRequestError` (pipeline lesson R-010).

### RISK-BACKEND-009: MEDIUM — No Error Handling on mysql_query Failures
**What to do:** SQLAlchemy raises exceptions on failure (unlike `mysql_query` which returns `false`). Wrap service calls in try/except and return appropriate HTTP status codes.
**Pattern to use:** Let FastAPI's default exception handler convert `SQLAlchemyError` to 500. For known error cases (duplicate key, constraint violation), catch specifically and return 409/422.
**Do NOT:** Silently swallow database errors. Do NOT return ok:true/false array pattern — use HTTP status codes.

### RISK-BACKEND-010: HIGH — init=False in mapped_column() (PIPELINE LESSON)
**What to do:** Never use `init=False` in `mapped_column()` for DB-generated columns. This raises `InvalidRequestError` at runtime.
**Pattern to use:** `created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())` — omit `init=False` entirely.
**Do NOT:** Use `mapped_column(init=False)` or `mapped_column(default=None, init=False)`. The `server_default` parameter handles DB-side defaults without needing `init=False`.

---

## 3. Ambiguities Requiring SME Resolution

| # | ID | Question | Discovery Source | Impact if Wrong |
|---|-----|----------|-----------------|-----------------|
| 1 | BR-BACKEND-002 | PHP `strlen()` counts bytes, Pydantic `max_length` counts characters. For multi-byte Unicode content (e.g., CJK, emoji), a 500-byte PHP string could be far fewer than 500 characters. Should the 500 limit be bytes (legacy-exact) or characters (Python-natural)? | index.php:27-29, R-006 | Notes that were too long in PHP could pass validation in Python, or vice versa for edge cases with non-ASCII content. LOW impact for ASCII-only usage. |
| 2 | BR-BACKEND-005 | Legacy `delete_note()` returns `ok:true` when deleting a non-existent ID. The FastAPI implementation raises 404. Is this behaviour change approved? Discovery flags it as NEEDS_VALIDATION. | index.php:35-43, R-007 | If stakeholder expects legacy-exact behaviour, the 404 path should be removed and delete should return 204 regardless. |
| 3 | BR-BACKEND-003 | After `trim()`, is the stripped content what gets stored, or is the original content stored and only display is trimmed? PHP source stores the trimmed value. Confirm this is intentional. | index.php:23 | If original content should be preserved, the Pydantic validator must strip for validation only but pass original to DB. LOW impact — current PHP stores trimmed. |

---

## 4. Cross-Module Dependencies

| BR ID | Depends On | Module | Status |
|-------|-----------|--------|--------|
| BR-BACKEND-004 (Invalid ID) | Frontend must send DELETE requests with valid integer IDs | frontend (MWU-NL2-002-FE) | FULLY_VALIDATED |
| BR-BACKEND-005 (404 on missing) | Frontend must handle 404 responses on delete | frontend (MWU-NL2-002-FE) | FULLY_VALIDATED |
| BR-BACKEND-007 (Note ordering) | Frontend renders notes in the order returned by API (no client-side sort) | frontend (MWU-NL2-002-FE) | FULLY_VALIDATED |

The frontend module (MWU-NL2-002-FE) is already FULLY_VALIDATED. The key coordination point is the REST API contract:
- `GET /api/notes` — list all notes (newest first)
- `POST /api/notes` — create note (JSON body with `content` field)
- `DELETE /api/notes/{id}` — delete note (replaces legacy `GET /?delete=N`)

---

## 5. MKB Storage Summary

Total rules stored: 10
MKB module: backend
Project ID: NOTE-LIST-LEG2
Status: EXTRACTED (pending HITL validation)

| Rule ID | MKB UUID |
|---------|----------|
| BR-BACKEND-001 | ef333461-d5bf-4185-baf7-2cb1cad53f26 |
| BR-BACKEND-002 | 8e2cb74c-b837-4744-9ba3-fabfcf1a8d4f |
| BR-BACKEND-003 | 7b5e07f8-d010-4a62-9c75-24981e20f853 |
| BR-BACKEND-004 | 474c33ea-bf41-4a33-a7f4-48516bc38dfc |
| BR-BACKEND-005 | 5a2af8de-026c-4fd9-acfb-f7348bfdace8 |
| BR-BACKEND-006 | 86e22203-23d2-4de8-94f2-fcbbcdee547a |
| BR-BACKEND-007 | b28fe766-5a7b-4247-9ce9-2452e9b6a5b4 |
| BR-BACKEND-008 | ca362b1c-1775-4d14-9d24-6f66a30186ea |
| BR-BACKEND-009 | ed761a82-0b76-4b48-a63f-4422a0d8bf58 |
| BR-BACKEND-010 | 6c7d8a7a-d22a-4de0-84c5-5ee6b495624d |

To retrieve for CodeGen:
```
mkb_get_business_rules(module="backend", status="VALIDATED", project_id="NOTE-LIST-LEG2")
```

---

## 6. Reviewer Checklist

- [x] All 8 BRs from discovery Section 7 are captured (BR-001 through 005, 006, 007, 010)
- [x] 2 additional BRs derived from Section 2 schema analysis (BR-008 UTF-8, BR-009 created_at)
- [x] Each BR has a clear, implementation-ready description
- [x] All 10 risk register items (R-001 through R-010) translated to CodeGen instructions in Section 2
- [x] 3 ambiguities flagged for SME resolution (not silently assumed)
- [x] All 10 MKB UUIDs recorded for traceability
- [x] Cross-module dependencies identified (3 touchpoints with frontend MWU-NL2-002-FE)
- [x] Pipeline lesson R-010 (init=False) incorporated into BR-009 and Risk Section
- [x] Validation chain order documented (BR-003 → BR-001 → BR-002)
- [x] CRITICAL constraint BR-006 (no auth) prominently flagged
