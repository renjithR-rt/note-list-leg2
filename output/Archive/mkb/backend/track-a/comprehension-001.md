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
