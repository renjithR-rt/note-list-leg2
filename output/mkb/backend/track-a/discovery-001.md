# Discovery — MWU-NL2-001 — Backend Module

**Date:** 2026-05-20
**MWU:** MWU-NL2-001
**Module:** backend
**Analyst:** Discovery Agent
**Stack:** PHP 5.6 / MySQL 5.7 → Python 3.12 / FastAPI 0.110 / SQLAlchemy 2.x / PostgreSQL 16 / Pydantic v2

**Lessons Applied (STEP 0):**
- Lesson (sim 0.43): SELF_REVIEW → HUMAN_REVIEW → TESTING transition required; never skip HUMAN_REVIEW state
- Lesson (sim 0.42): Codegen aborts if BRs are missing — all 9 BRs stored to MKB before pipeline advances
- Lesson (sim 0.34): MKB namespace vs module — following injected `module="backend"` per system prompt instruction

---

## 1. Source File Inventory

| # | File | Lines | Purpose | Concerns |
|---|------|-------|---------|----------|
| 1 | `source/index.php` | 121 | Monolithic: business logic + HTTP handler + HTML template | Mixed concerns; `mysql_*` ext; global state |
| 2 | `source/db.php` | 11 | Database connection bootstrap | Deprecated `mysql_connect`; env vars with hardcoded fallbacks |
| 3 | `source/db/schema.sql` | 8 | DDL for `notes` table | `DATETIME` (not `TIMESTAMP`); charset `utf8` (not `utf8mb4`) |
| 4 | `source/db/seed.sql` | 7 | 5 sample rows | Test/dev data only; not migrated to production |
| 5 | `source/style.css` | 28 | CSS styles | Frontend only — out of scope for this MWU |

**Scope for this MWU:** `source/index.php` (business logic functions + request handling) and `source/db.php` + `source/db/schema.sql`.
`style.css` is frontend scope (MWU-NL2-002-FE).

---

## 2. Database Schema

### Table: `notes`

| Column | MySQL Type | Constraints | PG Target Type | Flags |
|--------|-----------|-------------|----------------|-------|
| `id` | `INT AUTO_INCREMENT` | PRIMARY KEY | `SERIAL PRIMARY KEY` (or `BIGSERIAL`) | — |
| `content` | `VARCHAR(500)` | NOT NULL | `VARCHAR(500) NOT NULL` | Business rule: max 500 chars enforced at app layer too |
| `created_at` | `DATETIME` | DEFAULT CURRENT_TIMESTAMP | `TIMESTAMP WITH TIME ZONE DEFAULT NOW()` | **PG-NULL-DATE** flag: MySQL default is safe (no 0000-00-00) but type upgrade required |

**Character set:** MySQL schema declares `utf8` (3-byte, no emoji support). PostgreSQL uses UTF-8 natively (4-byte, full emoji support). No collation issues expected for existing data.

**Migration Notes:**
- `INT AUTO_INCREMENT` → `SERIAL` (prefer `BIGSERIAL` for future-proofing against ID exhaustion)
- `DATETIME` → `TIMESTAMP WITH TIME ZONE` — timezone-aware; seed data has no TZ info, assume UTC
- `ENGINE=InnoDB` — not applicable in PostgreSQL; omit
- No foreign keys, no secondary indexes beyond PK
- No cascade rules needed (single table, no references)

---

## 3. Data Access Layer — Function Inventory

### 3.1 `get_notes()` — `index.php:8–19`

```php
function get_notes() {
    global $conn;
    $result = mysql_query(
        "SELECT id, content, created_at FROM notes ORDER BY created_at DESC",
        $conn
    );
    $notes = array();
    while ($row = mysql_fetch_assoc($result)) {
        $notes[] = $row;
    }
    return $notes;
}
```

| Attribute | Value |
|-----------|-------|
| SQL | `SELECT id, content, created_at FROM notes ORDER BY created_at DESC` |
| Returns | Array of all notes, newest-first |
| Error handling | None — `mysql_query` failure silently returns `false` |
| Flags | **GLOBAL-VAR** (`global $conn`), no **N+1-QUERY** (single bulk SELECT) |

**FastAPI target:** `GET /api/notes` → `NoteService.list_all(db)` → `SELECT * FROM notes ORDER BY created_at DESC`

---

### 3.2 `add_note($content)` — `index.php:21–33`

```php
function add_note($content) {
    global $conn;
    $content = trim($content);
    if (empty($content)) {
        return array('ok' => false, 'err' => 'Note cannot be empty');
    }
    if (strlen($content) > MAX_NOTE_LENGTH) {
        return array('ok' => false, 'err' => 'Note too long (max 500 chars)');
    }
    $safe = mysql_real_escape_string($content, $conn);
    mysql_query("INSERT INTO notes (content) VALUES ('$safe')", $conn);
    return array('ok' => true, 'id' => mysql_insert_id($conn));
}
```

| Attribute | Value |
|-----------|-------|
| Validation order | `trim()` → empty check → length check (500 chars) |
| SQL | `INSERT INTO notes (content) VALUES ('$safe')` |
| Returns | `['ok' => true, 'id' => <new_id>]` on success; `['ok' => false, 'err' => '...']` on validation failure |
| Flags | **GLOBAL-VAR**, **RAW-SQL-CONCAT** (string interpolation despite `mysql_real_escape_string`), **DIRECT-OUTPUT** (return dict consumed by controller) |

**FastAPI target:** `POST /api/notes` → Pydantic `NoteCreate(content: str)` validates → `NoteService.create(db, content)` → parameterized INSERT → return `NoteRead`

---

### 3.3 `delete_note($id)` — `index.php:35–43`

```php
function delete_note($id) {
    global $conn;
    $id = (int)$id;
    if ($id <= 0) {
        return array('ok' => false, 'err' => 'Invalid note ID');
    }
    mysql_query("DELETE FROM notes WHERE id = $id", $conn);
    return array('ok' => true);
}
```

| Attribute | Value |
|-----------|-------|
| ID validation | Cast to int; rejects `<= 0` with "Invalid note ID" |
| SQL | `DELETE FROM notes WHERE id = $id` (integer cast — injection-safe) |
| Returns | `['ok' => true]` **even when no row matched** — silent no-op on missing IDs |
| Flags | **NULL-RETURN** (no 404 signal on missing record), **GLOBAL-VAR** |

**Critical Gap (RISK-001):** PHP returns `ok: true` when deleting a non-existent ID. The stated business requirement is "operations on non-existent note IDs return proper errors." FastAPI MUST check `rowcount` after DELETE and raise `HTTPException(status_code=404)` when 0 rows affected.

**FastAPI target:** `DELETE /api/notes/{id}` → `NoteService.delete(db, id)` → raises 404 if 0 rows deleted → returns 204 No Content on success

---

### 3.4 DB Connection — `db.php:1–11`

| Attribute | Value |
|-----------|-------|
| Connection | `mysql_connect()` — removed in PHP 7+; deprecated in PHP 5.5 |
| Credentials | `getenv()` with hardcoded fallbacks (`noteuser` / `notepass` / `notelist`) |
| Charset | `SET NAMES 'utf8'` |
| Error handling | `die()` on connection failure — hard crash, no recovery |
| Flags | **GLOBAL-VAR** (`$conn` injected into every function), deprecated ext |

**FastAPI target:** SQLAlchemy `async_sessionmaker` with `AsyncSession`; `get_db()` FastAPI dependency; connection string from `DATABASE_URL` env var (no hardcoded fallbacks)

---

## 4. UI / Controller Layer

The PHP controller is embedded in `index.php:46–67`.

| Route | Method | Parameters | Handler | Issues |
|-------|--------|-----------|---------|--------|
| `/` | `POST` | `$_POST['content']` | `add_note()` | No PRG — re-POST on refresh duplicates notes |
| `/` | `GET` | `$_GET['delete']` | `delete_note()` | DELETE via HTTP GET violates REST; CSRF-vulnerable |
| `/` | `GET` | _(none)_ | `get_notes()` | Loads all notes — no pagination |

**Issues flagged:**
- **No PRG pattern** (`index.php:50–57`): browser refresh after POST re-submits form; duplicates note
- **DELETE via GET** (`index.php:59–63`): violates HTTP semantics; any `<img src="/?delete=1">` silently deletes
- **No CSRF protection**: form at `index.php:92` has no token field
- **No pagination**: `get_notes()` always returns all rows; potential performance issue at scale

**FastAPI migration eliminates all of these** via proper REST endpoints and JSON API.

---

## 5. List / Search / Inquiry Pages

| Page | Legacy Path | Data Source | Columns Displayed | Sort | Filter | Pagination |
|------|-------------|-------------|-------------------|------|--------|-----------|
| Note List | `/` (`index.php`) | `notes` table | `id` (implicit), `content`, `created_at` | `created_at DESC` | None | None |

**Display logic (template layer, `index.php:101–115`):**
- Empty state: "No notes yet. Add one above."
- Date format: `date('d M Y', strtotime($n['created_at']))` — e.g. "20 May 2026" — **DATE-INTERPOLATION** flag
- Content escaping: `htmlspecialchars()` applied on output (correct XSS defense)
- Delete: `href="?delete={id}"` with JS `confirm()` dialog

**Migration notes:**
- Date formatting (`d M Y`) is UI concern → frontend formats `created_at` ISO 8601 string
- `htmlspecialchars` escaping is frontend concern → React handles XSS natively
- No search, filter, or sort controls exist in legacy

---

## 6. Dependency Map

```
index.php
  ├── db.php                     (DB connection bootstrap: $conn global)
  │     └── mysql_connect()      (PHP ext, deprecated/removed)
  ├── get_notes()                → SELECT id, content, created_at FROM notes
  ├── add_note($content)         → INSERT INTO notes (content)
  └── delete_note($id)           → DELETE FROM notes WHERE id = $id

External dependencies:
  MySQL 5.7 @ localhost:3310/notelist
  PHP 5.6 (mysql_* extension)

No external HTTP calls
No session management
No authentication
No file I/O
No caching layer
No queues or background jobs
```

**Cross-module dependencies:** None. This module is entirely self-contained.

**MWU-NL2-002-FE consumes** 3 REST endpoints produced by this MWU:
- `GET  /api/notes`
- `POST /api/notes`
- `DELETE /api/notes/{id}`

---

## 7. Business Rules (Exhaustive)

### BR-BACKEND-001 — Empty Note Guard
**Source:** `index.php:24–26`
**Rule:** A note cannot be saved if its content is empty after whitespace trimming.
**Logic:** `trim($content)` → `empty($content)` → reject with "Note cannot be empty"
**Error message:** "Note cannot be empty"
**Priority:** HIGH | **Status:** NEEDS_VALIDATION
**FastAPI impl:** Pydantic `@field_validator('content')` raises `ValueError('Note cannot be empty')` if `content.strip() == ""`

---

### BR-BACKEND-002 — Note Length Limit (500 chars)
**Source:** `index.php:27–29`, `db/schema.sql:6`
**Rule:** Note content is limited to 500 characters. Enforced at application layer; also enforced as DB column width.
**Logic:** `strlen($content) > 500` → reject with "Note too long (max 500 chars)"
**Constant:** `MAX_NOTE_LENGTH = 500` (`index.php:4`)
**Error message:** "Note too long (max 500 chars)"
**Priority:** HIGH | **Status:** NEEDS_VALIDATION
**FastAPI impl:** Pydantic `Field(max_length=500)` + ORM `String(500)` column

---

### BR-BACKEND-003 — Content Trimming Before Validation
**Source:** `index.php:23`
**Rule:** Content whitespace is trimmed BEFORE the empty check and length check. The trimmed value is what gets stored.
**Logic:** `$content = trim($content)` executed before any validation check
**Priority:** MEDIUM | **Status:** NEEDS_VALIDATION
**FastAPI impl:** Pydantic validator applies `.strip()` before validation; stripped value stored to DB

---

### BR-BACKEND-004 — Invalid ID Guard (Non-positive Integer)
**Source:** `index.php:37–40`
**Rule:** Delete operations must reject IDs that are zero or negative.
**Logic:** `$id = (int)$id; if ($id <= 0) return error`
**Error message:** "Invalid note ID"
**Priority:** HIGH | **Status:** NEEDS_VALIDATION
**FastAPI impl:** Path parameter `note_id: int = Path(ge=1)` → 422 Unprocessable Entity on invalid; no service call made

---

### BR-BACKEND-005 — Missing Note Returns Error (404) — NEEDS_VALIDATION
**Source:** `index.php:35–43` — **GAP: this behaviour is ABSENT in legacy code**
**Rule:** Delete operations on a valid but non-existent note ID must return a not-found error.
**Gap:** Current PHP returns `ok: true` silently when 0 rows are deleted.
**Priority:** HIGH | **Status:** NEEDS_VALIDATION
**Recommendation:** FastAPI checks `result.rowcount` after DELETE; raises `HTTPException(status_code=404, detail="Note not found")` when 0 rows affected.

---

### BR-BACKEND-006 — No Authentication (Public API)
**Source:** `index.php` — no session, no login, no access control anywhere
**Rule:** All note endpoints are public. No authentication is required and NONE must be added.
**CRITICAL:** Adding any auth layer violates this rule.
**Priority:** CRITICAL | **Status:** NEEDS_VALIDATION
**FastAPI impl:** No `Depends(get_current_user)`. No auth middleware. No API keys. Document explicitly in router.

---

### BR-BACKEND-007 — Note Ordering (Newest First)
**Source:** `index.php:11`
**Rule:** Notes are always returned in descending creation order (newest first).
**Logic:** `ORDER BY created_at DESC`
**Priority:** MEDIUM | **Status:** NEEDS_VALIDATION
**FastAPI impl:** SQLAlchemy `.order_by(Note.created_at.desc())` in list query

---

### BR-BACKEND-008 — UTF-8 Storage
**Source:** `db.php:10`, `db/schema.sql:1`
**Rule:** Note content is stored and retrieved as UTF-8.
**Logic:** `mysql_query("SET NAMES 'utf8'")` + schema `DEFAULT CHARACTER SET utf8`
**Note:** MySQL `utf8` is 3-byte (no emoji). PostgreSQL UTF-8 is 4-byte — an upgrade.
**Priority:** LOW | **Status:** NEEDS_VALIDATION
**FastAPI impl:** PostgreSQL uses UTF-8 natively; specify `client_encoding=utf8` in connection string

---

### BR-BACKEND-009 — Created-At Timestamp Auto-Set by Database
**Source:** `db/schema.sql:7`
**Rule:** `created_at` is set automatically by the database on INSERT. The application layer does not supply this value.
**Logic:** `DEFAULT CURRENT_TIMESTAMP` — never set in `add_note()`
**Priority:** LOW | **Status:** NEEDS_VALIDATION
**FastAPI impl:** SQLAlchemy `Column(DateTime(timezone=True), server_default=func.now())`; no app-layer assignment in `NoteCreate` schema

---

## 8. Risk Register

| ID | Risk | Severity | Source Location | Migration Action |
|----|------|----------|-----------------|-----------------|
| RISK-001 | `delete_note` silent no-op — returns `ok:true` when note ID not found | HIGH | `index.php:35–43` | FastAPI must check `rowcount` after DELETE → raise 404 if 0 rows affected |
| RISK-002 | SQL injection via string interpolation despite `mysql_real_escape_string` | HIGH | `index.php:30–31` | Replace with SQLAlchemy parameterized ORM insert |
| RISK-003 | `mysql_*` deprecated API — removed in PHP 7 | MEDIUM | `index.php`, `db.php` | Already resolved by migration to SQLAlchemy |
| RISK-004 | DELETE via HTTP GET — CSRF-vulnerable, violates REST semantics | MEDIUM | `index.php:59–63` | FastAPI uses `DELETE /api/notes/{id}` — correct HTTP method |
| RISK-005 | No PRG pattern — form re-submit on browser refresh duplicates notes | MEDIUM | `index.php:50–57` | FastAPI REST + SPA frontend eliminates this |
| RISK-006 | `DATETIME` → `TIMESTAMP WITH TIME ZONE` migration — timezone assumption | MEDIUM | `db/schema.sql:7` | Seed data has no TZ; assume UTC; document assumption for operators |
| RISK-007 | MySQL `utf8` is 3-byte; emoji/4-byte chars fail silently | LOW | `db.php:10`, `schema.sql:1` | PostgreSQL UTF-8 is 4-byte; full emoji support; no action needed |
| RISK-008 | Hardcoded DB credentials as env var fallbacks | LOW | `db.php:3–5` | Remove fallbacks; require `DATABASE_URL` env var; fail hard on missing |

---

## 9. Semgrep Pre-Analysis Confirmation

Semgrep patterns checked against all source files:

| Pattern | Flag | File | Line(s) | Finding |
|---------|------|------|---------|---------|
| `mysql_query` (deprecated ext) | — | `index.php` | 10, 31, 41 | **CONFIRMED** — 3 occurrences |
| `mysql_connect` (deprecated ext) | — | `db.php` | 7 | **CONFIRMED** |
| `global $var` (global state) | **GLOBAL-VAR** | `index.php` | 9, 22, 36 | **CONFIRMED** — all 3 functions use `global $conn` |
| SQL string concatenation/interpolation | **RAW-SQL-CONCAT** | `index.php` | 31 | **CONFIRMED** — `"INSERT INTO notes (content) VALUES ('$safe')"` |
| `echo`/HTML direct output in logic file | **DIRECT-OUTPUT** | `index.php` | 69+ | **CONFIRMED** — PHP template tags mixed with business logic |
| No CSRF token in form | — | `index.php` | 92 | **CONFIRMED** — form has no hidden token field |
| `die()` on error | **NULL-RETURN** | `db.php` | 8, 9 | **CONFIRMED** — hard crash on DB connection failure |
| Unvalidated GET parameter | — | `index.php` | 60 | **CONFIRMED** — `$_GET['delete']` cast to int only (safe for SQL, not for UX) |
| Date string manipulation | **DATE-INTERPOLATION** | `index.php` | 108 | **CONFIRMED** — `date('d M Y', strtotime($n['created_at']))` |

**Semgrep verdict:** 9 patterns flagged. All are expected PHP 5.6-era patterns. No novel vulnerabilities beyond known migration scope. The integer cast on `$_GET['delete']` is sufficient SQL protection but the missing 404 check (RISK-001) remains a logic gap.

---

## 10. Migration Complexity Assessment

**Overall Complexity: LOW**

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Business logic | LOW | 3 functions, trivial CRUD, no domain complexity |
| Data model | LOW | 1 table, 3 columns, no FKs, no secondary indexes |
| SQL complexity | LOW | 1 SELECT, 1 INSERT, 1 DELETE — no joins, no subqueries |
| Authentication / security | LOW | No auth required by design — simplifies FastAPI |
| External integrations | TRIVIAL | No HTTP calls, no queues, no caches, no file I/O |
| PHP anti-patterns to resolve | MEDIUM | `global $conn`, deprecated `mysql_*`, SQL concat, no PRG, DELETE via GET |
| Gap remediation required | MEDIUM | RISK-001 (missing 404 on delete) requires new logic not in legacy |

**FastAPI Migration Sketch:**

```
Router:  app/api/notes.py — 3 endpoints
  GET    /api/notes          → list_notes()      → 200 list[NoteRead]
  POST   /api/notes          → create_note()     → 201 NoteRead
  DELETE /api/notes/{id}     → delete_note()     → 204 No Content | 404

Schemas (Pydantic v2):  app/schemas/note.py
  NoteCreate(content: str)
    @field_validator('content') → strip + validate empty + max 500
  NoteRead(id: int, content: str, created_at: datetime)
    model_config = ConfigDict(from_attributes=True)

Service:  app/services/note_service.py — NoteService
  .list_all(db: AsyncSession) -> list[Note]
      SELECT * FROM notes ORDER BY created_at DESC
  .create(db: AsyncSession, content: str) -> Note
      INSERT INTO notes (content) VALUES (:content) RETURNING *
  .delete(db: AsyncSession, note_id: int) -> None
      DELETE FROM notes WHERE id = :note_id
      if result.rowcount == 0: raise HTTPException(404, "Note not found")

ORM Models:  app/models/note.py
  class Note(Base):
      __tablename__ = "notes"
      id:         Mapped[int]      = mapped_column(primary_key=True)
      content:    Mapped[str]      = mapped_column(String(500), nullable=False)
      created_at: Mapped[datetime] = mapped_column(
                      DateTime(timezone=True), server_default=func.now()
                  )

Dependencies:  app/database.py
  async_sessionmaker → AsyncSession
  get_db() → AsyncGenerator[AsyncSession, None]

Entry:  app/main.py
  FastAPI(title="Note List API")
  app.include_router(notes_router, prefix="/api")
```

**Estimated implementation scope:**
- ~150 lines across 4 source files (excluding tests)
- ~12 test cases minimum (3 endpoints × 4 scenarios: happy path, empty, too-long, missing-id)

---

## 11. Files Written

| # | Artifact | Location | Status |
|---|----------|----------|--------|
| 1 | Discovery document | `output/mkb/backend/track-a/discovery-001.md` | WRITTEN |
| 2 | `discovery_finding` — backend module | MKB PostgreSQL (via `mkb_store_artifact`) | STORED |
| 3 | `BR-BACKEND-001` — Empty Note Guard | MKB PostgreSQL | STORED |
| 4 | `BR-BACKEND-002` — Note Length Limit | MKB PostgreSQL | STORED |
| 5 | `BR-BACKEND-003` — Content Trimming | MKB PostgreSQL | STORED |
| 6 | `BR-BACKEND-004` — Invalid ID Guard | MKB PostgreSQL | STORED |
| 7 | `BR-BACKEND-005` — Missing Note 404 | MKB PostgreSQL | STORED |
| 8 | `BR-BACKEND-006` — No Authentication | MKB PostgreSQL | STORED |
| 9 | `BR-BACKEND-007` — Note Ordering | MKB PostgreSQL | STORED |
| 10 | `BR-BACKEND-008` — UTF-8 Storage | MKB PostgreSQL | STORED |
| 11 | `BR-BACKEND-009` — Created-At Auto-Set | MKB PostgreSQL | STORED |

---

**Pipeline handoff:** This document satisfies the DISCOVERY phase gate for MWU-NL2-001.
Next phase: COMPREHENSION → PLANNING → CODEGEN.
