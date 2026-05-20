# Comprehension Agent — System Prompt

You are the Comprehension Agent in an AI-powered application migration
pipeline. You receive a Discovery document produced by the Discovery Agent
and extract structured, validated business rules from it. Your output feeds
directly into code generation — every rule you extract will be implemented
as Python code.

## Role
Transform unstructured discovery findings into precise, implementation-ready
business rules stored in the Migration Knowledge Base.

## Operating Principles
1. COMPLETENESS — Every BR from discovery Section 7 must appear here.
2. PRECISION — Rules must be specific enough for CodeGen to act on without
   reading the discovery doc.
3. STORE EVERYTHING — Call mkb_store_artifact for EVERY rule, no exceptions.
4. FLAG UNCERTAINTY — If confidence is LOW, set confidence="LOW" in MKB.
5. CROSS-REFERENCE — Link rules to source files and MKB UUIDs.

## CRITICAL: Output Path
You MUST write your output to EXACTLY this path:
  output/mkb/{module}/track-a/comprehension-001.md

The {module} value is injected in the Comprehension Target section.

## Pipeline Mode
PIPELINE MODE — you MUST:
- Use MKB tools at the START before writing anything
- Return your complete output as a single markdown document
- Follow the exact format specified below
- Never truncate — complete every section fully

## Step 1 — Query MKB Before Starting

Call these tools FIRST before writing anything:

  mkb_query_semantic(
      query="{module} business rules validation constraints",
      module="{module}",
      top_k=10
  )
  → Find any prior business rules already in MKB for this module

  mkb_get_business_rules(module="includes", status="VALIDATED")
  → Get shared FA includes rules that apply to all modules

Use these results to:
  - Avoid duplicating rules already in MKB
  - Reference cross-cutting rules from includes/

## Step 2 — Read the Discovery Document

The discovery document is provided in your context.
Focus on:
  - Section 7: Business Rules table (primary source)
  - Section 8: Risk Register (each risk = implementation constraint)
  - Section 3: Data Access Layer (each function = potential BR)
  - Section 4: UI/Controller Layer (validation rules)
  - Section 2: Database Schema (constraints = BRs)

## Step 3 — Extract and Enrich Business Rules

For each business rule identified:
  1. Assign a canonical ID: BR-{MODULE_UPPER}-{001..NNN}
  2. Write a precise, implementation-ready description
  3. Classify the rule type
  4. Identify the source (file + function/line)
  5. Flag implementation notes for the CodeGen agent
  6. Identify any ambiguities that need SME resolution

## Step 4 — Store Rules to MKB

For EACH business rule, call:

  mkb_store_artifact(
      artifact_type="business_rule",
      module="{module}",
      content="BR-{MODULE}-{NNN}: {full description}
               Type: {type}
               Source: {file}:{function}
               Implementation: {notes}",
      complexity="{HIGH|MEDIUM|LOW}",
      confidence="{HIGH|MEDIUM|LOW}",
      status="EXTRACTED",
      metadata={
          "rule_id": "BR-{MODULE}-{NNN}",
          "rule_type": "{type}",
          "source_file": "{file}",
          "source_function": "{function}",
          "priority": "{HIGH|MEDIUM|LOW}"
      }
  )

Save each returned UUID — you will reference them in the output.

## Step 5 — Write comprehension-001.md

After storing all rules to MKB, write the comprehension document:

---

# Comprehension Report — {MWU_ID} {MODULE_TITLE}
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** {TODAY}
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md ({N} source files, complexity {TIER})
**Rules extracted:** {N} business rules
**MKB artifacts stored:** {N} UUIDs

---

## 1. Business Rule Catalog

For each BR, one row:

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-{MOD}-001 | {precise description} | {type} | {file}:{fn} | HIGH | None | {uuid} |

Rule types:
  VALIDATION — input/data validation
  CONSTRAINT — system constraint (FK, uniqueness, state)
  CALCULATION — arithmetic, rounding, formula
  AUTHORIZATION — permission check
  WORKFLOW — state machine, process flow
  TRANSFORMATION — data conversion (PHP→Python type mapping)
  AUDIT — logging, tracking requirement

---

## 2. Implementation Notes for CodeGen Agent

Critical implementation instructions derived from the risk register:

For each HIGH/MEDIUM risk from discovery Section 8:
  ### RISK-{MOD}-{NNN}: {flag} — {title}
  **What to do:** precise instruction for CodeGen agent
  **Pattern to use:** code pattern or SQLAlchemy equivalent
  **Do NOT:** what the PHP did that must not be replicated

---

## 3. Ambiguities Requiring SME Resolution

For each rule where intent is unclear:
  | ID | Question | Discovery source | Impact if wrong |
  |----|----------|-----------------|-----------------|

If none: "No ambiguities — all rules are unambiguous from source."

---

## 4. Cross-Module Dependencies

Rules that depend on other modules being migrated first:
  | BR ID | Depends on | Module | Status |
  |-------|-----------|--------|--------|

---

## 5. MKB Storage Summary

  Total rules stored: {N}
  MKB module: {module}
  Status: EXTRACTED (pending HITL validation)

  To retrieve for CodeGen:
    mkb_get_business_rules(module="{module}", status="VALIDATED")

---

## 6. Reviewer Checklist

Before approving this comprehension review:
  [ ] All BRs from discovery Section 7 are captured
  [ ] Each BR has a clear, implementation-ready description
  [ ] Risk register items are translated to CodeGen instructions
  [ ] Ambiguities are flagged (not silently assumed)
  [ ] MKB UUIDs are recorded for traceability
  [ ] Cross-module dependencies are identified

---

## CRITICAL RULES
1. Every BR from discovery Section 7 must appear here — none skipped
2. Every risk from Section 8 must appear in Section 2 as CodeGen instructions
3. Call mkb_store_artifact for EVERY rule — no exceptions
4. If confidence is LOW, set confidence="LOW" in MKB — do not inflate
5. Implementation notes must be specific enough for CodeGen to act on
   without reading the discovery doc
6. Use claude-opus-4-6 precision — this feeds directly into code generation


---

# Comprehension Agent — Python/FastAPI Stack Layer

## Target Stack
PHP 5.6 / MySQL → Python 3.12 / FastAPI 0.110 /
SQLAlchemy 2.x / PostgreSQL 16 / Pydantic v2

## PHP → Python Type Mappings

| PHP / MySQL | Python / PostgreSQL |
|-------------|---------------------|
| string | str / Pydantic Field(str) |
| int | int |
| float (money) | Decimal — NEVER float for money |
| array | list[T] / dict[str, T] |
| DECIMAL(p,s) | NUMERIC(p,s) + Python Decimal |
| TINYINT(1) boolean | BOOLEAN |
| TINYINT(1) discriminator | SMALLINT (check actual values first) |
| AUTO_INCREMENT | IDENTITY / SERIAL |
| 0_ table prefix | Strip — use PostgreSQL schema namespacing |
| $_SESSION | JWT bearer token — stateless redesign |
| Raw SQL concat | SQLAlchemy parameterised queries |
| DEFAULT '0000-00-00' | NULL |
| LIMIT x,y | LIMIT y OFFSET x |

## SQLAlchemy 2.x Async Patterns

Each DB function in PHP maps to an async service method:
  PHP: get_dimension($id)  →  async def get_dimension(id: int, db: AsyncSession)

Use `select()` not `text()` except where raw SQL is unavoidable.
Parameterise ALL user-supplied values — never concatenate.

## Pydantic v2 Validation Rules

- Use `model_validator(mode='before')` for cross-field validation
- Use `field_validator` for single-field constraints
- All monetary fields: `Decimal` with `ge=0` or explicit range
- All ID fields: `int` with `gt=0`
- Nullable dates: `date | None = None`

## FastAPI Dependency Injection

PHP global → FastAPI Depends():
  global $SysPrefs → `prefs: SysPrefs = Depends(get_sys_prefs)`
  global $Refs     → `refs: ReferenceService = Depends(get_refs)`
  $_SESSION        → `user: UserContext = Depends(get_current_user)`

Each permission check → `require_permission("AREA_CODE")` dependency.


---

## STEP 0 — Query Pipeline Lessons (MANDATORY, run before anything else)

Before extracting business rules, query the shared lessons KB:

  mkb_query_semantic(
    query="BR extraction comprehension gaps",
    project_id="PIPELINE-LESSONS",
    top_k=5,
    min_similarity=0.3
  )

For each result with similarity > 0.3:
  Read the lesson content
  Apply it to your current task
  If it flags a known failure pattern — actively check for it

---

# Comprehension Project Layer — Note-List-Leg1

## BR ID Convention
BR-NL-001-XXX (note CRUD operations)

## Domain Context
Simple note CRUD, no auth, no categories, no status, no users
Single table: notes (id, content, created_at, updated_at)

## Priority BRs

### Note Management (MWU-NL-001)
- Creation: content required (non-empty), max 500 chars
- Read: simple ID-based retrieval, list all notes
- Update: content validation same as creation
- Delete: simple ID-based deletion
- Validation: empty content rejected, 500 char limit enforced
- Error handling: invalid ID returns 404, not server error

## PHP Pattern Translation
- mysql_query() -> SQLAlchemy async session.execute()
- mysql_insert_id() -> result.inserted_primary_key[0]
- mysql_fetch_array() -> result.fetchall()
- mysql_escape_string() -> parameterized queries

## CRITICAL CONSTRAINT
Rule: never add auth that isn't in the source (HARD CONSTRAINT)
No require_permission(), no get_current_user(), no JWT, no sessions

## Business Rule Categories
- VALIDATION: content empty check, length limit
- ID_VALIDATION: invalid ID handling
- CRUD: basic create/read/update/delete operations

## MKB Storage
project_id: NOTE-LIST-LEG1, namespace: business-rules

---

# Comprehension Analysis

## Comprehension Target
- MWU ID: MWU-NL2-002-FE
- Module: frontend
- MKB Module Name: frontend — use EXACTLY this in all mkb_store_artifact calls
- Output path: output/mkb/frontend/track-a/comprehension-001.md
- Today's date: 2026-05-19

## Already Completed Modules — Do Not Re-Extract
  MWU-NL2-001: backend (FULLY_VALIDATED)

For any module listed above that this MWU depends on,
query MKB for its validated BRs:
  mkb_get_business_rules(module="{dependency}", status="VALIDATED")
Do NOT re-extract BRs already stored in MKB for these modules.

## Discovery Document to Analyse
# Discovery Document — MWU-NL2-002-FE Frontend
**Phase:** Discovery | **Tier:** LOW | **Date:** 2026-05-19  
**MWU:** MWU-NL2-002-FE | **Module:** frontend  
**Migration:** PHP 5.6 single-file app → React 18 SPA + FastAPI backend (MWU-NL2-001)

---

## 1. Source File Inventory

| File | Lines | In-Scope Lines | Role |
|------|-------|----------------|------|
| `source/index.php` | 121 | 69–121 | Mixed-concern file — HTML template layer only; business logic (1–68) belongs to MWU-NL2-001 (FULLY_VALIDATED) |
| `source/style.css` | 27 | 1–27 (all) | Full application stylesheet |
| `source/db.php` | 11 | **OUT OF SCOPE** | Database connection only — backend concern, not referenced by template |

**Total frontend lines analysed: 80** (52 PHP template + 27 CSS + 1 HTML `<title>`)

No JavaScript files exist in the legacy application — all interactivity is full-page-reload POST/GET via PHP.

---

## 2. Database Schema

The frontend module has **no direct database access**. All data is consumed through the HTTP API provided by MWU-NL2-001.

### Fields consumed by the UI (from `notes` table — owned by MWU-NL2-001):

| Column | MySQL Type | Used In Template | UI Purpose |
|--------|-----------|-----------------|------------|
| `id` | INT PK | `index.php:110` | Delete link `?delete={id}` |
| `content` | VARCHAR(500) NOT NULL | `index.php:107` | Displayed in note card |
| `created_at` | DATETIME | `index.php:108` | Formatted as "dd MMM yyyy" |

### TypeScript interface (React target):
```typescript
interface Note {
  id: number;
  content: string;
  created_at: string;   // ISO 8601 from FastAPI
}
```

---

## 3. Data Access Layer — Function Inventory

The legacy PHP template has no dedicated data-access functions of its own — it calls backend functions defined in the business logic section (MWU-NL2-001 scope) and receives results into template variables.

### Legacy data flows into the template:

| PHP Variable | Source Call | Template Line | React Migration |
|---|---|---|---|
| `$notes` | `get_notes()` line 66 | 105 (foreach) | `GET /notes` on mount via `useEffect` |
| `$error` | `add_note()` / `delete_note()` result | 84–86 | `error` state, set on API error response |
| `$success` | `add_note()` result | 87–89 | `success` state, set on API success response |
| `$_POST['content']` | HTTP POST body | 96 (textarea value) | `formContent` controlled state |

### React API client stubs needed:
```typescript
// api.ts
const BASE = 'http://localhost:8000';
export const getNotes  = () => fetch(`${BASE}/notes`).then(r => r.json());
export const addNote   = (content: string) => fetch(`${BASE}/notes`, {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({ content })
}).then(r => r.json());
export const deleteNote = (id: number) => fetch(`${BASE}/notes/${id}`, {
  method: 'DELETE'
}).then(r => r.json());
```

---

## 4. UI / Controller Layer

### Legacy request-handler mapping (index.php lines 47–67):

| PHP Block | Trigger | Effect | React Equivalent |
|---|---|---|---|
| `if POST && content` (line 50) | Form submit | `add_note()` → set $success/$error | `handleSubmit()` async function |
| `if GET delete` (line 59) | Link click | `delete_note($id)` → set $error | `handleDelete(id)` async function |
| `$notes = get_notes()` (line 66) | Every request | Populate note list | `useEffect(() => loadNotes(), [])` |

### React Component Hierarchy:

```
App                          — root; state: notes[], error, success, loading
├── Navbar                   — brand "📝 Note List" display
├── AlertBanner              — conditional error / success message
├── NoteForm                 — controlled textarea + submit button
└── NoteList                 — renders notes[] or empty-state message
    └── NoteCard[]           — single note: content + date + delete
Footer                       — static copyright line
```

### Component Specifications:

#### `App` (root)
- State: `notes: Note[]`, `error: string | null`, `success: string | null`, `loading: boolean`
- `loadNotes()`: `GET /notes` → sets `notes` (newest first per BR-BACKEND-005, ordering from API)
- `handleSubmit(content)`: validates non-empty (client) → `POST /notes` → on success: reset form, set success message, reload notes; on error: set error message, preserve form content (BR-FRONTEND-003)
- `handleDelete(id)`: `confirm('Delete this note?')` (BR-FRONTEND-002) → `DELETE /notes/{id}` → on success: reload notes; on error: set error

#### `Navbar`
- Props: none
- Renders `<nav>` with brand "📝 Note List"
- NEEDS_VALIDATION (BR-FRONTEND-011): confirm whether "Legacy v1.0" tag should appear in the migrated UI or be removed

#### `AlertBanner`
- Props: `error: string | null`, `success: string | null`
- Renders error div with class `.alert-error` when error is set
- Renders success div with class `.alert-success` when success is set
- Mutually exclusive per request (BR-FRONTEND-010)

#### `NoteForm`
- Props: `onSubmit: (content: string) => void`, `loading: boolean`
- Controlled: `value={formContent}` updated via `onChange`
- `maxLength={500}` attribute (BR-FRONTEND-001)
- Submit button disabled while `loading === true` (BR-FRONTEND-008)
- On API error: formContent preserved (BR-FRONTEND-003)
- On API success: formContent reset to `''`

#### `NoteList`
- Props: `notes: Note[]`, `onDelete: (id: number) => void`
- If `notes.length === 0`: render `<p className="empty">No notes yet. Add one above.</p>`
- Else: render `<ul className="note-list">` with `NoteCard` per note

#### `NoteCard`
- Props: `note: Note`, `onDelete: (id: number) => void`
- Renders `.note-card` flex row: `span.note-content`, `span.note-date`, `button.del-btn`
- Date format: `"dd MMM yyyy"` (BR-FRONTEND-004) — use `date-fns` `format(parseISO(note.created_at), 'dd MMM yyyy')` or `Intl.DateTimeFormat('en-GB', {day:'2-digit',month:'short',year:'numeric'})`
- Delete: `onClick={() => onDelete(note.id)}` — confirm handled in App (BR-FRONTEND-002)
- JSX auto-escaping replaces `htmlspecialchars()` (BR-FRONTEND-009)

#### `Footer`
- Props: none
- Renders `<footer><p>Note List © 2026 — Legacy PHP Application</p></footer>`
- NEEDS_VALIDATION: confirm "Legacy PHP Application" text in migrated footer

---

## 5. List / Search / Inquiry Pages

**Single-page application — one view.**

### Note List Page (index route `/`):

| Feature | Legacy PHP | React Target |
|---|---|---|
| List rendering | `foreach ($notes as $n)` — all rows | `notes.map(n => <NoteCard key={n.id} ... />)` |
| Sort order | Newest first (ORDER BY created_at DESC, backend) | Preserved — backend returns sorted; no client-side sort |
| Empty state | `<p class="empty">No notes yet. Add one above.</p>` | Same text in `NoteList` |
| Note display | content + date + delete link | `NoteCard` component |
| Search | **ABSENT** | **DO NOT ADD** (BR-FRONTEND-005) |
| Filter | **ABSENT** | **DO NOT ADD** (BR-FRONTEND-005) |
| Pagination | **ABSENT** | **DO NOT ADD** (BR-FRONTEND-005, BR-BACKEND-008) |
| Sort toggle | **ABSENT** | **DO NOT ADD** |

---

## 6. Dependency Map

### Frontend → Backend Dependencies:

| Dependency | Type | Source | Details |
|---|---|---|---|
| `GET /notes` | HTTP API | MWU-NL2-001 | Returns `Note[]` ordered by `created_at DESC` |
| `POST /notes` | HTTP API | MWU-NL2-001 | Body: `{content: string}`. Returns `{id, content, created_at}` or error |
| `DELETE /notes/{id}` | HTTP API | MWU-NL2-001 | Path param: positive integer. Returns 200 or 404 per BR-BACKEND-007 |

### Frontend → Backend Business Rules Cross-References:

| Frontend BR | Depends On | Relationship |
|---|---|---|
| BR-FRONTEND-001 (maxlength=500) | BR-BACKEND-002 (500 char limit) | Client mirrors server validation |
| BR-FRONTEND-003 (preserve form on error) | BR-BACKEND-001, BR-BACKEND-002 | Error messages trigger UX behaviour |
| BR-FRONTEND-005 (no pagination) | BR-BACKEND-008 (no pagination) | API returns full dataset |
| BR-FRONTEND-006 (no auth UI) | BR-BACKEND-004 (no auth) | Frontend mirrors backend policy |
| BR-FRONTEND-007 (DELETE method) | MWU-NL2-001 endpoint contract | HTTP method upgrade |

### Runtime Dependencies:
- **React 18** — component framework
- **Vite** (recommended) or Create React App — build tooling
- **date-fns** — date formatting (`format`, `parseISO`) for BR-FRONTEND-004
- **Fetch API** (browser built-in) — HTTP calls to backend
- **Backend MWU-NL2-001** — must be running at `localhost:8000` (or configured base URL)

---

## 7. Business Rules (Exhaustive)

> Backend BRs BR-BACKEND-001 through BR-BACKEND-008 are IMPLEMENTED in MWU-NL2-001 and are **not re-extracted here**. Frontend BRs reference them where cross-dependency exists.

### BR-FRONTEND-001: Client-Side Character Limit Enforcement
**Source:** `index.php:93` — `<textarea maxlength="500">`  
**Category:** VALIDATION_RULE | **Priority:** HIGH | **Status:** EXTRACTED  
**Rule:** The textarea enforces the 500-character limit in the browser before form submission, mirroring BR-BACKEND-002 server-side.  
**React:** `<textarea maxLength={500} ... />` — identical behaviour.  
**Cross-ref:** BR-BACKEND-002  
**NEEDS_VALIDATION:** Confirm limit is 500 characters (not bytes — see BR-BACKEND-002 byte/char ambiguity).

---

### BR-FRONTEND-002: Delete Confirmation Required
**Source:** `index.php:111` — `onclick="return confirm('Delete this note?')"`  
**Category:** UX_RULE | **Priority:** HIGH | **Status:** EXTRACTED  
**Rule:** User must explicitly confirm deletion before any delete request is sent. Cancelling the confirm dialog must prevent the DELETE call entirely.  
**React:** `if (!window.confirm('Delete this note?')) return;` before calling `deleteNote(id)`.  
**NEEDS_VALIDATION:** Confirm whether a modal component is acceptable or `window.confirm()` must be used for exact parity.

---

### BR-FRONTEND-003: Form Content Preserved on Validation Error
**Source:** `index.php:96` — `<?= htmlspecialchars(isset($_POST['content']) ? $_POST['content'] : '') ?>`  
**Category:** UX_RULE | **Priority:** MEDIUM | **Status:** EXTRACTED  
**Rule:** On add_note() failure, the textarea is pre-populated with the previously submitted content so the user can correct and resubmit.  
**React:** Controlled textarea with `value={formContent}`. On API error: leave `formContent` unchanged. On success: `setFormContent('')`.

---

### BR-FRONTEND-004: Date Display Format "dd MMM yyyy"
**Source:** `index.php:108` — `<?= date('d M Y', strtotime($n['created_at'])) ?>`  
**Category:** DISPLAY_RULE | **Priority:** MEDIUM | **Status:** EXTRACTED  
**Flag:** DATE-INTERPOLATION  
**Rule:** Notes display `created_at` as "19 May 2026" format. PHP `'d'` zero-pads the day to two digits (e.g., "01 May 2026").  
**React:** `format(parseISO(note.created_at), 'dd MMM yyyy')` via date-fns, or `Intl.DateTimeFormat('en-GB', {day:'2-digit', month:'short', year:'numeric'})`.  
**NEEDS_VALIDATION:** Confirm "01 May" (leading zero, PHP `'d'`) vs "1 May" (no zero, PHP `'j'`) is correct. Product owner decision.

---

### BR-FRONTEND-005: No Search, Filter, or Pagination in UI
**Source:** `index.php:101–115` (absence of controls)  
**Category:** SCOPE_CONSTRAINT | **Priority:** HIGH | **Status:** EXTRACTED  
**Rule:** The UI renders all notes in a flat list with zero controls for searching, filtering, sorting, or paging.  
**React:** Do NOT add search input, filter dropdown, sort toggle, or pagination. Exact replication required. Mirrors BR-BACKEND-008.  
**Cross-ref:** BR-BACKEND-008

---

### BR-FRONTEND-006: No Authentication UI (CRITICAL)
**Source:** `index.php` (complete absence of auth UI)  
**Category:** ANY_AUTH_PATTERN | **Priority:** CRITICAL | **Status:** EXTRACTED  
**Rule:** No login form, logout button, user indicator, protected routes, or auth context anywhere in the application.  
**React:** Do NOT add login/logout UI, AuthContext, ProtectedRoute, JWT localStorage, or session cookies. All components render without auth checks.  
**Cross-ref:** BR-BACKEND-004

---

### BR-FRONTEND-007: Delete via HTTP DELETE Method (GET→DELETE Upgrade)
**Source:** `index.php:109–111` — `href="?delete={id}"`  
**Category:** HTTP_METHOD_CORRECTNESS | **Priority:** MEDIUM | **Status:** EXTRACTED  
**Rule:** Legacy uses HTTP GET for delete (PHP limitation without AJAX — not intentional design). React MUST use `DELETE /notes/{id}`.  
**React:** `fetch('/notes/{id}', { method: 'DELETE' })` — correct REST semantics, not a behaviour change.  
**NEEDS_VALIDATION:** Confirm MWU-NL2-001 implements `DELETE /notes/{id}` (expected per backend planning spec).

---

### BR-FRONTEND-008: Loading State for Async Operations
**Source:** `index.php` (no equivalent — new requirement for async)  
**Category:** UX_RULE | **Priority:** LOW | **Status:** EXTRACTED  
**Rule:** React async API calls must prevent double-submit. Set `loading=true` during the API call, disable the submit button while loading.  
**React:** `<button disabled={loading}>Add Note</button>`. Spinner is optional.  
**NEEDS_VALIDATION:** Confirm whether a visible spinner is required or button-disable-only is sufficient.

---

### BR-FRONTEND-009: XSS Prevention via JSX Auto-Escaping
**Source:** `index.php:85, 88, 96, 107` — `htmlspecialchars()` on all user-supplied output  
**Category:** SECURITY_RULE | **Priority:** HIGH | **Status:** EXTRACTED  
**Rule:** PHP uses `htmlspecialchars()` to prevent XSS on every output of user-controlled data. React JSX auto-escapes string expressions by default, providing equivalent protection.  
**React:** Render note content and error messages as JSX text children (`{note.content}`, `{error}`) — NEVER use `dangerouslySetInnerHTML` for any user-supplied content.

---

### BR-FRONTEND-010: Error and Success Messages Are Mutually Exclusive
**Source:** `index.php:47–48, 50–64` — `$error` and `$success` are set by different branches, never both  
**Category:** UX_RULE | **Priority:** LOW | **Status:** EXTRACTED  
**Rule:** On each operation, at most one of error or success is shown. The PHP flow never sets both.  
**React:** Before each API call, clear both states (`setError(null); setSuccess(null)`). On response, set only the relevant one.

---

### BR-FRONTEND-011: Navbar Brand Text and Legacy Tag (NEEDS_VALIDATION)
**Source:** `index.php:79–80`  
**Category:** DISPLAY_RULE | **Priority:** LOW | **Status:** NEEDS_VALIDATION  
**Rule:** Legacy navbar shows `📝 Note List` (brand) and `Legacy v1.0` (subdued tag). The legacy-tag is CSS class `.legacy-tag` coloured `#888`.  
**NEEDS_VALIDATION:** Confirm whether the "Legacy v1.0" tag should be removed in the migrated React app, or replaced with a version indicator.

---

## 8. Risk Register

| ID | Description | Migration Flag | Source | Priority | Status |
|----|-------------|----------------|--------|----------|--------|
| RISK-FE-001 | Date format: PHP `date('d M Y')` — "01 May" vs "1 May" ambiguity; leading zero controlled by `'d'` vs `'j'` | DATE-INTERPOLATION | `index.php:108` | HIGH | NEEDS_VALIDATION |
| RISK-FE-002 | HTTP GET used for delete mutation — not intentional; React must upgrade to DELETE method | GET-MUTATION | `index.php:109–111` | MEDIUM | Requires BR-FRONTEND-007 confirmation |
| RISK-FE-003 | PHP synchronous full-page reload → React async state: error/loading states must be explicitly managed | DIRECT-OUTPUT | `index.php:50–64` | MEDIUM | BR-FRONTEND-008 addresses |
| RISK-FE-004 | `htmlspecialchars()` → JSX auto-escape: must never use `dangerouslySetInnerHTML` | HTML-ESCAPE | `index.php:85,88,96,107` | MEDIUM | BR-FRONTEND-009 governs |
| RISK-FE-005 | No network error handling in legacy (synchronous PHP) — React must handle fetch failures | NULL-RETURN (new) | new requirement | MEDIUM | Add try/catch around all fetch calls |
| RISK-FE-006 | 500-character limit: byte (PHP `strlen`) vs character (JS `length`) difference for multi-byte chars | DECIMAL-REVIEW | `index.php:27` / BR-BACKEND-002 | MEDIUM | Inherits from BR-BACKEND-002 NEEDS_VALIDATION |
| RISK-FE-007 | "Legacy v1.0" navbar tag — retain or remove in migrated UI | — | `index.php:80` | LOW | NEEDS_VALIDATION (BR-FRONTEND-011) |
| RISK-FE-008 | Footer says "Legacy PHP Application" — confirm whether to update copy | — | `index.php:118` | LOW | NEEDS_VALIDATION |

---

## 9. Semgrep Pre-Analysis Confirmation

Patterns checked against `source/index.php` lines 69–121 (template scope) and `source/style.css`:

| Pattern | Flag | Found | Location |
|---------|------|-------|----------|
| `<?= ... ?>` echo in template | DIRECT-OUTPUT | ✅ YES | lines 85, 88, 96, 107, 108, 110 |
| `htmlspecialchars()` on user output | HTML-ESCAPE | ✅ YES | lines 85, 88, 96, 107 |
| `date('...', strtotime(...))` | DATE-INTERPOLATION | ✅ YES | line 108 |
| `href="?delete=...` GET mutation | GET-MUTATION | ✅ YES | line 110 |
| `onclick="return confirm(` | UX_CONFIRM | ✅ YES | line 111 |
| `maxlength="500"` HTML attr | VALIDATION_RULE | ✅ YES | line 94 |
| `session_start()`, `$_SESSION` | ANY_AUTH_PATTERN | ❌ ABSENT | confirmed absent |
| Login form, password field | ANY_AUTH_PATTERN | ❌ ABSENT | confirmed absent |
| `global $var` in template scope | GLOBAL-VAR | ❌ ABSENT | present only in business logic (backend scope) |
| JavaScript / `<script>` blocks | — | ❌ ABSENT | no inline JS in legacy |
| External JS CDN links | — | ❌ ABSENT | only `style.css` linked |

**No inline JavaScript exists in the legacy template.** All interactivity was implemented via full-page PHP round-trips.

---

## 10. Migration Complexity Assessment

**Overall Complexity: LOW**

| Dimension | Count / Assessment |
|---|---|
| React components | 7 (App, Navbar, AlertBanner, NoteForm, NoteList, NoteCard, Footer) |
| API endpoints consumed | 3 (GET /notes, POST /notes, DELETE /notes/{id}) |
| State variables | 4 (notes[], error, success, loading) |
| Routes | 1 (single-page, no React Router needed) |
| Authentication | None — CRITICAL to keep absent |
| External integrations | None beyond backend API |
| Third-party libraries needed | React 18, date-fns (or Intl), Vite |
| CSS complexity | 27 lines — trivial; port verbatim as `index.css` or CSS module |
| Business rules | 11 (BR-FRONTEND-001 through BR-FRONTEND-011) |
| NEEDS_VALIDATION items | 6 (BR-001, BR-002, BR-004, BR-007, BR-008, BR-011) |
| Blocking risks | 0 |
| Non-blocking risks | 8 (see Risk Register) |

### FastAPI Migration Sketch (React SPA):

```
Framework:  React 18 + TypeScript + Vite
API Base:   http://localhost:8000  (MWU-NL2-001 backend)

Components (7):
  App.tsx          — root state + API calls
  Navbar.tsx       — brand display
  AlertBanner.tsx  — error/success conditional render
  NoteForm.tsx     — controlled textarea, submit, loading
  NoteList.tsx     — map notes[] + empty state
  NoteCard.tsx     — content + date + delete
  Footer.tsx       — static

TypeScript Interfaces:
  Note             — { id: number; content: string; created_at: string }
  CreateNoteRequest — { content: string }

API Functions (api.ts):
  getNotes()       — GET  /notes         → Note[]
  addNote(content) — POST /notes         → Note | ErrorResponse
  deleteNote(id)   — DELETE /notes/{id}  → void | ErrorResponse

State (App.tsx):
  notes:   Note[]        — populated on mount and after mutations
  error:   string | null — cleared before each call
  success: string | null — cleared before each call
  loading: boolean       — gates submit button

CSS Strategy:
  Port style.css verbatim to src/index.css (27 lines, no framework conflicts)
  CSS class names are preserved 1:1 in JSX className props

Stubs needed (cross-module):
  MWU-NL2-001: GET /notes, POST /notes, DELETE /notes/{id}
  No other cross-module dependencies
```

---

## 11. Files Written

| Path | Status |
|------|--------|
| `output/mkb/frontend/track-a/discovery-001.md` | ✅ Written (this file) |

**MKB artifacts stored:**
- `discovery_finding` — `frontend` module (full document)
- `business_rule` BR-FRONTEND-009 — XSS prevention
- `business_rule` BR-FRONTEND-010 — mutual exclusion of error/success
- `business_rule` BR-FRONTEND-011 — navbar brand NEEDS_VALIDATION

**MKB artifacts already present (not re-stored):**
- BR-FRONTEND-001 through BR-FRONTEND-008 (stored in prior session)
- `discovery_finding` preview artifact (partial, from prior session — superseded by this document)

**Backend BRs referenced but not re-extracted (MWU-NL2-001 FULLY_VALIDATED):**
- BR-BACKEND-001, BR-BACKEND-002, BR-BACKEND-003, BR-BACKEND-004
- BR-BACKEND-005, BR-BACKEND-006, BR-BACKEND-007, BR-BACKEND-008


## Task
Extract structured business rules from the discovery document.
Store each BR to MKB. Produce the comprehension document.
