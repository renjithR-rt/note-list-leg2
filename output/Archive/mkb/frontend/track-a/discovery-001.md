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
