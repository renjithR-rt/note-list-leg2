# Discovery Document — MWU-NL2-001 Backend
**Module:** backend  
**Date:** 2026-05-19  
**Agent:** Discovery Agent (Python/FastAPI Stack Layer)  
**Status:** EXTRACTED  
**Complexity:** LOW  

---

## 1. Source File Inventory

| File | Lines | Role | Notes |
|------|-------|------|-------|
| `source/index.php` | 121 | Mixed: business logic + request handler + HTML renderer | Three BL functions, POST/GET handling, full page HTML output |
| `source/db.php` | 11 | Database connection bootstrap | Deprecated `mysql_*` extension; env-var config with fallback defaults |
| `source/db/schema.sql` | 8 | DDL — canonical schema | Single table `notes`; `VARCHAR(500) NOT NULL`; `DATETIME DEFAULT CURRENT_TIMESTAMP` |
| `source/db/seed.sql` | 8 | Seed data | 5 sample notes; confirms content is free-text |

**Scope Boundary:** Business logic and data access only. UI/HTML layer (lines 69–120 of index.php) is out of scope for this MWU — it belongs to MWU-NL2-002-FE.

---

## 2. Database Schema

### Table: `notes`
**Source:** `source/db/schema.sql:4-8`

| Column | MySQL Type | Constraint | PG Target Type | Flags |
|--------|-----------|------------|----------------|-------|
| `id` | `INT` | `AUTO_INCREMENT PRIMARY KEY` | `SERIAL PRIMARY KEY` | — |
| `content` | `VARCHAR(500)` | `NOT NULL` | `VARCHAR(500) NOT NULL` | DB-enforced length matches application constant `MAX_NOTE_LENGTH=500` |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | `TIMESTAMP WITH TIME ZONE DEFAULT now()` | **PG-NULL-DATE** N/A — no `0000-00-00` default used; safe migration |

**Engine:** InnoDB → no special PostgreSQL migration concern.  
**Charset:** `utf8` (MySQL's 3-byte UTF-8) → PostgreSQL default `UTF8` (full 4-byte); emoji in notes will now be stored correctly.  
**No foreign keys, no indexes beyond PK.**

---

## 3. Data Access Layer — Function Inventory

### 3.1 `get_notes()` — `index.php:8-19`
```
SELECT id, content, created_at FROM notes ORDER BY created_at DESC
```
- Returns all notes as PHP associative array; newest first.
- No pagination, no filtering.
- **GLOBAL-VAR:** uses `global $conn` → migrate to FastAPI `AsyncSession` dependency injection.
- **N+1-QUERY:** Not present — single bulk fetch.

**FastAPI target:** `GET /notes` → `List[NoteRead]`

---

### 3.2 `add_note($content)` — `index.php:21-33`
```
INSERT INTO notes (content) VALUES ('{escaped}')
```
- Pre-validates: `trim()` → empty check → length check (> 500).
- Escapes via `mysql_real_escape_string()` — **RAW-SQL-CONCAT** flag: still string-interpolated SQL.
- Returns `['ok' => true, 'id' => mysql_insert_id()]` on success.
- Returns `['ok' => false, 'err' => '...']` on validation failure.
- **GLOBAL-VAR:** `global $conn`.

**FastAPI target:** `POST /notes` body `NoteCreate` → `NoteRead`

---

### 3.3 `delete_note($id)` — `index.php:35-43`
```
DELETE FROM notes WHERE id = {int_cast_id}
```
- Casts `$id` to `(int)`.
- Guards: `$id <= 0` → returns `['ok' => false, 'err' => 'Invalid note ID']`.
- Does **NOT** check whether the note exists before DELETE — returns `['ok' => true]` even when no row matched.
- **GLOBAL-VAR:** `global $conn`.
- **NULL-RETURN:** Silent success on missing ID is a logic gap → FastAPI must raise `HTTPException(404)` when `rowcount == 0`.

**FastAPI target:** `DELETE /notes/{id}` → `204 No Content` or `404`

---

### 3.4 Database Connection — `db.php:1-11`
- Uses deprecated `mysql_connect()` / `mysql_select_db()` — removed in PHP 7.
- Credentials from env vars with hardcoded defaults: `localhost / noteuser / notepass / notelist`.
- Sets `utf8` charset via `mysql_query("SET NAMES 'utf8'")`.
- **GLOBAL-VAR:** `$conn` assigned at module scope, consumed via `global $conn` in every function.

**FastAPI target:** SQLAlchemy 2.x async engine → `AsyncSession` via `get_db()` dependency.

---

## 4. UI / Controller Layer

### Request Handling — `index.php:45-66` (OUT OF SCOPE for this MWU)
| Trigger | Method | Handler |
|---------|--------|---------|
| Form submit | `POST` with `$_POST['content']` | `add_note()` |
| Delete link | `GET` with `$_GET['delete']` | `delete_note()` |

- No routing framework — PHP single-file request dispatch.
- No CSRF protection.
- Error/success stored in `$error` / `$success` variables, rendered inline.

### HTML Output — `index.php:69-120` (OUT OF SCOPE for this MWU)
- Full page render: navbar, form, note list, footer.
- **DIRECT-OUTPUT:** `echo` / `<?= ?>` in business logic file → separate completely in FastAPI.
- **DATE-INTERPOLATION:** `date('d M Y', strtotime($n['created_at']))` — display formatting only; backend should return ISO 8601 datetime and let frontend format.
- `htmlspecialchars()` used throughout for XSS prevention — Pydantic models provide equivalent protection.

---

## 5. List / Search / Inquiry Pages

| Page/Feature | Source Location | Query | Sort | Pagination | Filter |
|-------------|----------------|-------|------|------------|--------|
| Note list | `index.php:8-19` | `SELECT id, content, created_at FROM notes` | `created_at DESC` | None — full table scan | None |

No search, no filtering, no pagination in legacy. Migration scope: replicate exact behaviour; pagination is a future enhancement, NOT in scope.

---

## 6. Dependency Map

```
index.php
├── requires db.php              (database connection bootstrap)
│   └── mysql_connect()          (deprecated PHP mysql extension)
├── define('MAX_NOTE_LENGTH')    (application constant)
├── get_notes()                  (data access — read)
├── add_note()                   (data access — write)
└── delete_note()                (data access — delete)

FastAPI target graph:
app/
├── routers/notes.py             ← replaces request handling in index.php
├── services/note_service.py     ← replaces get_notes / add_note / delete_note
├── models/note.py               ← SQLAlchemy ORM (notes table)
├── schemas/note.py              ← Pydantic NoteCreate / NoteRead
└── core/database.py             ← replaces db.php (async engine + get_db)
```

**Cross-module dependencies:** None. This is a self-contained single-module application.  
**External services:** MySQL 5.7 → PostgreSQL 16.  
**No shared includes, no session, no auth.**

---

## 7. Business Rules

> All rules below apply to module `backend`. Rules marked `NEEDS_VALIDATION` require product owner confirmation before implementation.

| Rule ID | Category | Priority | Confidence | Status | Source |
|---------|----------|----------|------------|--------|--------|
| BR-BACKEND-001 | VALIDATION_RULE | HIGH | HIGH | NEEDS_VALIDATION | `index.php:24-26` |
| BR-BACKEND-002 | VALIDATION_RULE | HIGH | HIGH | NEEDS_VALIDATION | `index.php:27-29` |
| BR-BACKEND-003 | ID_VALIDATION | HIGH | HIGH | NEEDS_VALIDATION | `index.php:37-40` |
| BR-BACKEND-004 | ANY_AUTH_PATTERN | CRITICAL | HIGH | NEEDS_VALIDATION | `index.php` (absence) |
| BR-BACKEND-005 | SORT_ORDER | MEDIUM | HIGH | EXTRACTED | `index.php:10-13` |
| BR-BACKEND-006 | INPUT_NORMALIZATION | MEDIUM | HIGH | EXTRACTED | `index.php:23` |
| BR-BACKEND-007 | ID_VALIDATION | HIGH | MEDIUM | NEEDS_VALIDATION | `index.php:41-43` |
| BR-BACKEND-008 | DATA_VOLUME | LOW | HIGH | EXTRACTED | `index.php:8-19` |

---

### BR-BACKEND-001: Empty Note Rejection
**Category:** VALIDATION_RULE  
**Priority:** HIGH — NEEDS_VALIDATION  
**Source:** `index.php:24-26`

Notes with empty content (after trim) MUST NOT be saved. The check occurs after `trim()`, so a note containing only whitespace is treated as empty.

```php
$content = trim($content);
if (empty($content)) {
    return array('ok' => false, 'err' => 'Note cannot be empty');
}
```

**FastAPI implementation:** Pydantic validator on `NoteCreate.content` — `@field_validator('content') ... if not v.strip(): raise ValueError('Note cannot be empty')`.  
**PostgreSQL:** `content VARCHAR(500) NOT NULL` enforces non-null but not non-empty — application layer must enforce blank check.

---

### BR-BACKEND-002: Maximum Note Length 500 Characters
**Category:** VALIDATION_RULE  
**Priority:** HIGH — NEEDS_VALIDATION  
**Source:** `index.php:4, 27-29`; `source/db/schema.sql:6`

Note content is limited to 500 characters. The application constant `MAX_NOTE_LENGTH = 500` matches the DB column `VARCHAR(500)`.

```php
if (strlen($content) > MAX_NOTE_LENGTH) {
    return array('ok' => false, 'err' => 'Note too long (max 500 chars)');
}
```

**Important:** `strlen()` counts bytes; multi-byte UTF-8 characters (emoji, CJK) count as multiple bytes. Target PostgreSQL uses character-length semantics. **NEEDS_VALIDATION:** should limit be 500 characters or 500 bytes?

**FastAPI implementation:** `content: str = Field(..., max_length=500)` in `NoteCreate` (character-length).

---

### BR-BACKEND-003: Delete Requires Valid Positive Integer ID
**Category:** ID_VALIDATION  
**Priority:** HIGH — NEEDS_VALIDATION  
**Source:** `index.php:37-40`

Delete operations must validate that the ID is a positive integer (`> 0`). IDs ≤ 0 are rejected with an error.

```php
$id = (int)$id;
if ($id <= 0) {
    return array('ok' => false, 'err' => 'Invalid note ID');
}
```

**FastAPI implementation:** FastAPI path parameter `id: int` with `gt=0` constraint handles this automatically via Pydantic. Non-integer IDs return `422 Unprocessable Entity`.

---

### BR-BACKEND-004: No Authentication — All Endpoints Are Public
**Category:** ANY_AUTH_PATTERN  
**Priority:** CRITICAL — NEEDS_VALIDATION  
**Source:** `index.php` (confirmed absence of any auth check)

The legacy application has zero authentication, session management, or access control. All note operations (list, create, delete) are fully public. This is a deliberate design choice — **do NOT add authentication** in the FastAPI migration.

**FastAPI implementation:** No `Depends(get_current_user)` anywhere. No OAuth2, JWT, or session middleware.

---

### BR-BACKEND-005: Notes Listed Newest First
**Category:** SORT_ORDER  
**Priority:** MEDIUM  
**Source:** `index.php:10-13`

All note listings are ordered by `created_at DESC` — the newest note appears at the top.

```php
"SELECT id, content, created_at FROM notes ORDER BY created_at DESC"
```

**FastAPI implementation:** `ORDER BY created_at DESC` in the ORM query.

---

### BR-BACKEND-006: Content Is Trimmed Before Validation and Storage
**Category:** INPUT_NORMALIZATION  
**Priority:** MEDIUM  
**Source:** `index.php:23`

Note content is `trim()`-ed before any validation or database write. This means leading/trailing whitespace is silently stripped.

```php
$content = trim($content);
```

**FastAPI implementation:** `@field_validator('content', mode='before') def strip_content(cls, v): return v.strip()` — apply before the empty check.

---

### BR-BACKEND-007: Delete on Non-Existent Note Returns Silent Success
**Category:** ID_VALIDATION  
**Priority:** HIGH — NEEDS_VALIDATION  
**Source:** `index.php:41-43`  
**Confidence:** MEDIUM (behaviour is implicit, not documented)

The legacy `delete_note()` executes `DELETE WHERE id = $id` and returns `['ok' => true]` regardless of whether any row was affected. A delete of a non-existent ID silently succeeds.

**Migration decision required:** The FastAPI implementation SHOULD raise `HTTPException(status_code=404, detail="Note not found")` when `result.rowcount == 0`, as this is the correct REST behaviour. However, if any consumer relies on the silent-success behaviour, this is a breaking change.

**Marked NEEDS_VALIDATION** — confirm with product owner that 404 on missing delete is acceptable.

---

### BR-BACKEND-008: No Pagination — Full Table Returned
**Category:** DATA_VOLUME  
**Priority:** LOW  
**Source:** `index.php:8-19`

The list endpoint returns all notes in a single query with no limit or offset. This is intentional for a personal note-taking app with small data volume.

**FastAPI implementation:** Replicate exact behaviour. Do NOT add pagination silently. Future enhancement if needed.

---

## 8. Risk Register

| ID | Flag | Location | Severity | Description | FastAPI Mitigation |
|----|------|----------|----------|-------------|-------------------|
| R-001 | **GLOBAL-VAR** | `index.php:9,22,36` | HIGH | `global $conn` couples all functions to module-level state | FastAPI `get_db()` `AsyncSession` dependency injection |
| R-002 | **RAW-SQL-CONCAT** | `index.php:30-31` | HIGH | `mysql_real_escape_string` + string concat — SQL injection risk even with escaping | SQLAlchemy parameterised ORM queries eliminate entirely |
| R-003 | **DIRECT-OUTPUT** | `index.php:69-120` | MEDIUM | HTML mixed with business logic in same file | Router + Service layer separation; Jinja2 or React handles render |
| R-004 | **DATE-INTERPOLATION** | `index.php:108` | MEDIUM | `date('d M Y', strtotime($n['created_at']))` — PHP date formatting in output | Return ISO 8601 from API; frontend formats for display |
| R-005 | **NULL-RETURN** | `index.php:41-43` | MEDIUM | `delete_note` silently succeeds for non-existent IDs | Check `rowcount`; raise `HTTPException(404)` — see BR-BACKEND-007 |
| R-006 | **DEPRECATED-EXT** | `db.php:7-9` | HIGH | `mysql_connect()` removed in PHP 7; `mysql_*` functions deprecated since PHP 5.5 | Replace entirely with SQLAlchemy 2.x async engine |
| R-007 | **STRLEN-MULTIBYTE** | `index.php:27` | LOW | `strlen()` counts bytes not characters; 500-byte limit may reject valid multi-byte content | Use `len()` (character-count) in Python — verify intent with product owner |
| R-008 | **NO-CSRF** | `index.php:50-57` | LOW | POST form has no CSRF token — acceptable for single-user local app | FastAPI REST API with JSON body is not subject to CSRF in same way; no action needed unless cookie auth is added (it won't be, per BR-BACKEND-004) |

---

## 9. Semgrep Pre-Analysis Confirmation

The following patterns were identified during manual review that a Semgrep scan should confirm:

| Rule | Pattern | File | Line |
|------|---------|------|------|
| `php.lang.security.injection.tainted-sql-string` | `mysql_query("...('$safe')")` | `index.php` | 31 |
| `php.lang.security.injection.tainted-sql-string` | `mysql_query("DELETE ... WHERE id = $id")` | `index.php` | 41 |
| `php.lang.deprecated.deprecated-mysql-extension` | `mysql_connect`, `mysql_query`, `mysql_real_escape_string` | `db.php`, `index.php` | multiple |
| `php.lang.maintainability.global-variable` | `global $conn` | `index.php` | 9, 22, 36 |
| `php.lang.security.xss.echo-unescaped` | Any `echo` / `<?=` — all use `htmlspecialchars()` | `index.php` | 85, 88, 96, 107, 108 |

**All `echo` outputs confirmed to use `htmlspecialchars()` — XSS risk is mitigated in legacy code.**  
No raw `$_POST` or `$_GET` values reach SQL directly (ID is cast to int; content uses escape).

---

## 10. Migration Complexity Assessment

**Overall Complexity: LOW**

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Schema complexity | LOW | Single table, no FKs, no indexes beyond PK |
| Business rule count | LOW | 8 rules, all straightforward |
| Data volume risk | LOW | Personal app — expected < 1000 rows |
| Integration complexity | LOW | No external services, no auth, no sessions |
| SQL complexity | LOW | 3 queries: SELECT all, INSERT, DELETE by ID |
| State management | LOW | No sessions, no caching, no transactions needed |
| Type mapping risk | LOW-MEDIUM | `strlen` bytes vs characters (R-007); `DATETIME` → `TIMESTAMP WITH TIME ZONE` |

**Estimated FastAPI endpoint count:** 3  
- `GET /notes` — list all notes
- `POST /notes` — create note
- `DELETE /notes/{id}` — delete note

**Estimated Pydantic model count:** 2  
- `NoteCreate` — input validation (content, max_length=500, strip)
- `NoteRead` — response shape (id, content, created_at as ISO 8601)

---

## 11. FastAPI Migration Sketch

```
Router:   app/routers/notes.py — 3 endpoints
          GET    /notes           → List[NoteRead]
          POST   /notes           → NoteRead (201 Created)
          DELETE /notes/{id}      → 204 No Content | 404 Not Found

Schemas:  app/schemas/note.py
          NoteCreate  — content: str (stripped, min_length=1, max_length=500)
          NoteRead    — id: int, content: str, created_at: datetime

Service:  app/services/note_service.py — NoteService
          list_notes()              → list[Note]
          create_note(content: str) → Note
          delete_note(note_id: int) → None (raises 404 if not found)

ORM:      app/models/note.py
          class Note(Base):
              __tablename__ = "notes"
              id         = Column(Integer, primary_key=True, autoincrement=True)
              content    = Column(String(500), nullable=False)
              created_at = Column(DateTime(timezone=True), server_default=func.now())

DB:       app/core/database.py
          Async SQLAlchemy engine → postgresql+asyncpg://...
          get_db() → AsyncGenerator[AsyncSession, None]

Stubs:    None — no cross-module dependencies
```

---

## 12. Files Written

| File | Purpose |
|------|---------|
| `output/mkb/backend/track-a/discovery-001.md` | This document — pipeline handoff artifact |

**MKB Storage:** Stored via `mkb_store_artifact` (artifact_type=`discovery_finding`, module=`backend`, project_id=`NOTE-LIST-2`)  
**Business Rules stored:** BR-BACKEND-001 through BR-BACKEND-008  
**Cross-validation:** Executed post-storage
