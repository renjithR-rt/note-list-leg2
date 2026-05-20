# Discovery Document — MWU-NL2-001 Backend
**Module:** backend  
**MWU ID:** MWU-NL2-001  
**Date:** 2026-05-20  
**Agent:** Discovery Agent (Python/FastAPI Stack Layer)  
**Status:** EXTRACTED  

---

## 1. Source File Inventory

| # | File | Lines | Role | Notes |
|---|------|-------|------|-------|
| 1 | `source/index.php` | 121 | Main application — business logic + request handler + HTML template | Mixed concerns; all three layers in one file |
| 2 | `source/db.php` | 11 | Database connection — MySQL via deprecated `mysql_*` ext | Env-driven config; uses `global $conn` |
| 3 | `source/db/schema.sql` | 8 | DDL — `notes` table definition | Single table; InnoDB; utf8 charset |
| 4 | `source/db/seed.sql` | 7 | Seed data — 5 sample notes | For dev/test only; not business logic |

**Total:** 4 files, 147 lines, 1 database table, 3 PHP functions, 2 request handlers.

---

## 2. Database Schema

### Source (MySQL 5.7)

```sql
CREATE TABLE notes (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    content    VARCHAR(500) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARACTER SET utf8;
```

### PostgreSQL 16 Target Mapping

| MySQL Column | Type | PG Target Type | Flags |
|---|---|---|---|
| `id` | `INT AUTO_INCREMENT` | `INTEGER GENERATED ALWAYS AS IDENTITY` | — |
| `content` | `VARCHAR(500) NOT NULL` | `VARCHAR(500) NOT NULL` | MySQL VARCHAR(500) is byte-counted for some charsets; PG counts characters — **DECIMAL-REVIEW** for non-ASCII content |
| `created_at` | `DATETIME DEFAULT CURRENT_TIMESTAMP` | `TIMESTAMPTZ DEFAULT now()` | No `0000-00-00` default found — no **PG-NULL-DATE** flag needed |

**Schema flags:**
- No `TINYINT(1)` columns — no **TYPE-EXCEPTION** flag
- No monetary columns — no **DECIMAL-REVIEW** / **FLOAT-MONEY** flag
- No `GROUP BY` queries — no **PG-STRICT-MODE** flag
- `mysql_real_escape_string` used in `add_note` → **RAW-SQL-CONCAT** (must be replaced with parameterized queries)

---

## 3. Data Access Layer — Function Inventory

### `get_notes()` — `index.php:8–19`

```php
function get_notes() {
    global $conn;                                     // GLOBAL-VAR
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

| Property | Value |
|---|---|
| Operation | SELECT — full table scan, ordered DESC |
| Returns | Array of `{id, content, created_at}` |
| Validation | None |
| Error handling | None — `mysql_query` failure returns `false`; loop proceeds on falsy result → **NULL-RETURN** |
| Patterns | **GLOBAL-VAR** (`$conn`), deprecated `mysql_query` |
| Migration target | `async def list_notes(db: AsyncSession) -> list[Note]` |

### `add_note($content)` — `index.php:21–33`

```php
function add_note($content) {
    global $conn;                                       // GLOBAL-VAR
    $content = trim($content);
    if (empty($content)) {                              // BR-BACKEND-001
        return array('ok' => false, 'err' => 'Note cannot be empty');
    }
    if (strlen($content) > MAX_NOTE_LENGTH) {          // BR-BACKEND-002
        return array('ok' => false, 'err' => 'Note too long (max 500 chars)');
    }
    $safe = mysql_real_escape_string($content, $conn); // RAW-SQL-CONCAT
    mysql_query("INSERT INTO notes (content) VALUES ('$safe')", $conn);
    return array('ok' => true, 'id' => mysql_insert_id($conn));
}
```

| Property | Value |
|---|---|
| Operation | INSERT — single row |
| Returns | `{ok: true, id: int}` on success; `{ok: false, err: string}` on validation failure |
| Validation | `trim`, `empty()` check, `strlen > 500` check |
| Error handling | Validation returns error array; DB errors silently ignored → **NULL-RETURN** |
| Patterns | **GLOBAL-VAR**, **RAW-SQL-CONCAT**, `mysql_real_escape_string` |
| Migration target | `async def create_note(content: str, db: AsyncSession) -> Note` |

### `delete_note($id)` — `index.php:35–43`

```php
function delete_note($id) {
    global $conn;                                      // GLOBAL-VAR
    $id = (int)$id;
    if ($id <= 0) {                                    // BR-BACKEND-003
        return array('ok' => false, 'err' => 'Invalid note ID');
    }
    mysql_query("DELETE FROM notes WHERE id = $id", $conn);
    return array('ok' => true);
}
```

| Property | Value |
|---|---|
| Operation | DELETE by primary key |
| Returns | `{ok: true}` always (even when no row deleted) |
| Validation | `(int)$id > 0` guard |
| Error handling | No row-not-found check — silently returns `ok: true` → **NEEDS_VALIDATION** |
| Patterns | **GLOBAL-VAR** |
| Migration target | `async def delete_note(note_id: int, db: AsyncSession) -> None` (should raise 404 if not found) |

---

## 4. UI / Controller Layer

### Request Dispatcher — `index.php:47–66`

```php
// POST /  with content param → add_note
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['content'])) {
    $result = add_note($_POST['content']);
}

// GET /  with ?delete=N → delete_note
if (isset($_GET['delete'])) {
    $result = delete_note((int)$_GET['delete']);
}

// Always — fetch all notes for render
$notes = get_notes();
```

**Flags:**
- DELETE via HTTP GET (`?delete=N`) — REST violation → must become `DELETE /api/notes/{id}` in FastAPI (**NEEDS_VALIDATION**: confirm FE is updated to use DELETE method)
- All three operations served from single route `/` — no routing framework
- No CSRF protection on POST

### HTML Template — `index.php:69–120`
Mixed into same file after PHP logic. Contains:
- Navbar, note-list rendering, add-note form, delete anchor links
- `htmlspecialchars()` used on all output — XSS prevention present
- `date('d M Y', strtotime($n['created_at']))` — **DATE-INTERPOLATION** → Python `datetime.strftime('%d %b %Y')`

---

## 5. List / Search / Inquiry Pages

| Page / Feature | PHP Entry Point | Query | Sort | Pagination | Filter |
|---|---|---|---|---|---|
| Note list (main view) | `index.php:66` via `get_notes()` | `SELECT id, content, created_at FROM notes` | `created_at DESC` | None (full table) | None |

**No search, no filter, no pagination** in legacy app. FastAPI migration must replicate exact behavior (no new features). If pagination is added later it is out of scope for this MWU.

---

## 6. Dependency Map

```
index.php
  ├── db.php              (require_once — DB connection, global $conn)
  ├── DB: MySQL notelist  (mysql_connect → notes table)
  └── style.css           (HTML template link — frontend concern, not in this MWU)

db.php
  ├── ENV: DB_HOST, DB_USER, DB_PASS, DB_NAME  (with fallback literals)
  └── mysql_* extension   (PHP 5.6 — removed in PHP 8)
```

**Cross-MWU dependencies:**
- **MWU-NL2-002-FE (frontend)**: Consumes the REST endpoints this MWU will produce. FE currently uses `?delete=N` GET — must coordinate DELETE method change.
- No shared authentication, no session, no user tables.

---

## 7. Business Rules (Exhaustive)

> Notation: `[VALIDATION_RULE]`, `[ID_VALIDATION]`, `[ANY_AUTH_PATTERN]` flags as required by project layer.

### BR-BACKEND-001 — Empty Note Guard
- **Rule:** Note content, after `trim()`, must not be empty. Save is rejected with error `"Note cannot be empty"`.
- **Source:** `index.php:23–26`
- **Priority:** HIGH
- **Status:** NEEDS_VALIDATION
- **Flag:** `[VALIDATION_RULE]`
- **Migration note:** Implement as Pydantic `@field_validator` on `NoteCreate.content` with `min_length=1` after strip.

### BR-BACKEND-002 — Maximum Note Length
- **Rule:** Note content must not exceed 500 characters (`MAX_NOTE_LENGTH` constant). Save is rejected with `"Note too long (max 500 chars)"`.
- **Source:** `index.php:4` (constant), `index.php:27–29`
- **Priority:** HIGH
- **Status:** NEEDS_VALIDATION
- **Flag:** `[VALIDATION_RULE]`
- **Migration note:** Enforce as both Pydantic `max_length=500` and DB constraint `VARCHAR(500) NOT NULL`. `strlen()` in PHP counts bytes; Pydantic `max_length` counts characters — behavior is identical for ASCII content; NEEDS_VALIDATION for Unicode.

### BR-BACKEND-003 — Invalid ID Guard
- **Rule:** Delete operations validate that `$id` cast to `int` is `> 0`. Values ≤ 0 return `"Invalid note ID"` error.
- **Source:** `index.php:37–40`
- **Priority:** HIGH
- **Status:** NEEDS_VALIDATION
- **Flag:** `[ID_VALIDATION]`
- **Migration note:** FastAPI path parameter `note_id: int` with `gt=0` (`Path(gt=0)`) covers this. Additionally, a 404 should be raised when the note does not exist (legacy does not do this — **behaviour change**, NEEDS_VALIDATION).

### BR-BACKEND-004 — Reverse Chronological Order
- **Rule:** `get_notes()` always returns notes sorted `ORDER BY created_at DESC`. Most recently created note is first.
- **Source:** `index.php:11`
- **Priority:** MEDIUM
- **Status:** EXTRACTED
- **Migration note:** Replicate exactly in SQLAlchemy: `select(Note).order_by(Note.created_at.desc())`.

### BR-BACKEND-005 — No Authentication (CRITICAL)
- **Rule:** All note operations (list, create, delete) are public — no login, no session, no token.
- **Source:** `index.php` (entire file — no auth check present)
- **Priority:** CRITICAL
- **Status:** EXTRACTED
- **Flag:** `[ANY_AUTH_PATTERN]`
- **Migration note:** FastAPI endpoints must NOT use any `Depends(get_current_user)` or OAuth2 scheme. Zero auth dependencies. Any auth pattern introduced is a regression.

### BR-BACKEND-006 — Content Trimmed Before Validation
- **Rule:** `add_note()` calls `trim($content)` before empty-check and before storage. Leading/trailing whitespace is stripped from stored content.
- **Source:** `index.php:23`
- **Priority:** MEDIUM
- **Status:** NEEDS_VALIDATION
- **Flag:** `[VALIDATION_RULE]`
- **Migration note:** Pydantic v2 `model_validator` or `field_validator(mode='before')` with `.strip()` before `min_length` check. Confirm with stakeholder: is stripped content stored, or is original content stored and only display trimmed?

### BR-BACKEND-007 — Silent Delete on Missing ID
- **Rule:** `delete_note()` does not check `mysql_affected_rows()` — returns `ok: true` even when no row was deleted (ID valid integer but does not exist).
- **Source:** `index.php:35–43`
- **Priority:** LOW
- **Status:** NEEDS_VALIDATION
- **Flag:** `[ID_VALIDATION]`
- **Migration note:** FastAPI best practice is to raise `HTTP 404` when note not found. This is a **behaviour change from legacy**. Confirm with stakeholder before implementing 404 path.

### BR-BACKEND-008 — DB Credentials from Environment
- **Rule:** DB connection reads `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` from environment, with hardcoded fallbacks (`localhost / noteuser / notepass / notelist`).
- **Source:** `db.php:2–5`
- **Priority:** LOW
- **Status:** EXTRACTED
- **Migration note:** FastAPI equivalent: `DATABASE_URL` from `.env` via `pydantic-settings`. Remove hardcoded fallback credentials in production config.

---

## 8. Risk Register

| # | Risk | Severity | Flag | Mitigation |
|---|------|----------|------|-----------|
| R-001 | `mysql_*` extension removed in PHP 7/8 — entire DAL must be rewritten | HIGH | — | Full SQLAlchemy async rewrite; no compatibility shim possible |
| R-002 | `global $conn` — state shared across all functions | MEDIUM | **GLOBAL-VAR** | Replace with `get_db()` FastAPI dependency injecting `AsyncSession` |
| R-003 | `mysql_real_escape_string` for SQL safety — not parameterized | HIGH | **RAW-SQL-CONCAT** | All queries must use SQLAlchemy ORM or `text()` with `:param` binds |
| R-004 | DELETE via HTTP GET (`?delete=N`) — REST semantics violation | MEDIUM | — | FE must be updated to use `DELETE /api/notes/{id}`; coordinate with MWU-NL2-002-FE |
| R-005 | `mysql_insert_id()` for returned ID — no `RETURNING` clause | LOW | — | SQLAlchemy `session.refresh(obj)` after flush populates `obj.id` |
| R-006 | `strlen()` byte-count vs character-count on non-ASCII notes | LOW | — | PostgreSQL `VARCHAR(500)` and Pydantic `max_length=500` both count characters; consistent but different from PHP bytes |
| R-007 | No row-not-found check on delete — silent no-op | MEDIUM | **NULL-RETURN** | Add `db.get(Note, note_id)` pre-check; raise `HTTP 404` (NEEDS_VALIDATION behaviour change) |
| R-008 | `DATETIME` (no timezone) in MySQL → `TIMESTAMPTZ` in PostgreSQL | LOW | — | Existing timestamps lose timezone on migration; seed data only, no prod data at risk |
| R-009 | No error handling on `mysql_query` failures | MEDIUM | **NULL-RETURN** | SQLAlchemy raises exceptions on failure; wrap in try/except and return `HTTP 500` |
| R-010 | init=False in mapped_column() raises InvalidRequestError | HIGH | PIPELINE-LESSON | Never use `init=False` in `mapped_column()`; use `server_default=` for DB-generated columns |

---

## 9. Semgrep Pre-Analysis Confirmation

Patterns found and flagged in source:

| Pattern | Location | Flag |
|---|---|---|
| `mysql_real_escape_string` | `index.php:30` | **RAW-SQL-CONCAT** |
| `global $conn` | `index.php:9,22,36` | **GLOBAL-VAR** |
| `mysql_query("... VALUES ('$safe')")` | `index.php:31` | **RAW-SQL-CONCAT** |
| `mysql_query("DELETE FROM notes WHERE id = $id")` | `index.php:41` | Direct int interpolation (safe via cast but not parameterized) |
| `echo/print` equiv: `<?= ... ?>` in business file | `index.php:85–118` | **DIRECT-OUTPUT** |
| `strtotime($n['created_at'])` | `index.php:108` | **DATE-INTERPOLATION** |
| No auth check | `index.php` (all) | `[ANY_AUTH_PATTERN]` — ABSENCE confirmed, must stay absent |
| No `$_GET`/`$_POST` sanitization beyond cast | `index.php:60` | Input validation via `(int)` cast only |

**No patterns found:**
- TINYINT(1) discriminator — none
- Monetary float — none
- IMPLICIT-JOIN — none
- N+1-QUERY — none (no loop with DB call)
- FLOAT-MONEY — none

---

## 10. Migration Complexity Assessment

**Overall Complexity: LOW**

| Dimension | Score | Rationale |
|---|---|---|
| Data model | TRIVIAL | 1 table, 3 columns, no foreign keys, no constraints beyond NOT NULL |
| Business logic | LOW | 3 functions; validation is simple (empty, length, int cast) |
| Query complexity | TRIVIAL | 1 SELECT, 1 INSERT, 1 DELETE — no joins, no subqueries, no aggregates |
| Authentication | TRIVIAL | None present, none needed |
| Error handling | LOW | Return-array pattern → FastAPI exception raising |
| Integration surface | LOW | No external APIs, no file I/O, no queues |
| FE coordination | LOW | One breaking change (GET delete → DELETE method) needs FE update |

**FastAPI Migration Sketch:**

```
Router:   routers/notes.py — 3 endpoints
  GET    /api/notes           → list all notes (created_at DESC)
  POST   /api/notes           → create note (validate trim, empty, max_len)
  DELETE /api/notes/{id}      → delete note (validate id > 0, raise 404 if missing)

Schemas (Pydantic v2):
  NoteCreate:  content: str  — @field_validator: strip, min_length=1, max_length=500
  NoteRead:    id: int, content: str, created_at: datetime
  NoteListResponse: notes: list[NoteRead]

Service:  services/notes_service.py — NotesService
  list_notes(db)               → list[NoteRead]
  create_note(data, db)        → NoteRead
  delete_note(note_id, db)     → None  (raises HTTPException 404 if not found)

ORM Model:  models/note.py — Note
  id:         Mapped[int]      = mapped_column(primary_key=True)
  content:    Mapped[str]      = mapped_column(String(500), nullable=False)
  created_at: Mapped[datetime] = mapped_column(server_default=func.now())
  ⚠ DO NOT use init=False in mapped_column() — raises InvalidRequestError (pipeline lesson)

DB Dependency:  database.py
  get_db() → AsyncGenerator[AsyncSession, None]
  DATABASE_URL from pydantic-settings (.env)

Stubs needed:
  - database.py (get_db AsyncSession)
  - No cross-module stubs; this is the only service
```

**Estimated effort:** 2–3 hours for a single developer.  
**Test surface:** 8–10 unit/integration tests covering all BRs + error paths.

---

## 11. Files Written

| Path | Type | Status |
|---|---|---|
| `output/mkb/backend/track-a/discovery-001.md` | Discovery document (this file) | WRITTEN |
| MKB — `discovery_finding` artifact | PostgreSQL via mkb_store_artifact | PENDING (stored after this write) |
| MKB — `business_rule` artifacts × 8 (BR-BACKEND-001 … 008) | PostgreSQL | PENDING |
