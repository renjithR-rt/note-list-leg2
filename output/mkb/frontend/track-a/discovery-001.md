# Discovery Document — Frontend Module
**MWU:** MWU-NL2-002-FE  
**Module:** frontend  
**Date:** 2026-05-20  
**Agent:** Discovery Agent (Python/FastAPI Stack Layer)  
**Status:** EXTRACTED  

---

## 1. Source File Inventory

| File | Lines | Role | Concerns |
|------|-------|------|----------|
| `source/index.php` | 121 | Mixed: business logic + request dispatch + HTML rendering | DIRECT-OUTPUT — PHP mixes all layers in one file |
| `source/db.php` | 11 | Database connection bootstrap | GLOBAL-VAR — `$conn` is a global |
| `source/style.css` | 28 | Full UI stylesheet | Pure CSS — no preprocessor, no framework |

**Total source artefacts:** 3 files, 160 lines  
**Frontend-specific lines:** 70–120 in index.php (HTML template) + all of style.css = ~79 lines  

### Lessons Applied
- Pipeline lesson (sim 0.44): `init=False` inside `mapped_column()` raises `InvalidRequestError` → ORM models for frontend response types must **omit** `init=` entirely; use `server_default=` for DB-generated fields.
- Pipeline lesson (sim 0.43): Workflow path is `SELF_REVIEW → HUMAN_REVIEW → TESTING` — codegen must not skip `HUMAN_REVIEW`.

---

## 2. Database Schema

The frontend module does **not own** any database tables. All schema ownership belongs to `backend` (MWU-NL2-001).

**Consumed schema (read-only contract):**

```
notes (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  content     VARCHAR(500) NOT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**API contract** (shapes the frontend data layer):

| Field | PHP type | React type | Notes |
|-------|----------|------------|-------|
| `id` | int | `number` | used for delete key and React `key` prop |
| `content` | string | `string` | max 500 chars, already trimmed |
| `created_at` | MySQL TIMESTAMP string | `string` (ISO-8601) | FastAPI returns ISO-8601; React must reformat |

**DATE-INTERPOLATION flag:** Legacy formats dates via `date('d M Y', strtotime($n['created_at']))` (e.g., "20 May 2026"). React must replicate this format via `Intl.DateTimeFormat` or equivalent — exact format is a business expectation.

---

## 3. Data Access Layer — Function Inventory

The frontend has **no direct database access**. All data access is delegated to the backend FastAPI service via HTTP.

**Backend API endpoints consumed by this module (inferred from PHP request handling):**

| # | Method | Path | PHP trigger | Purpose |
|---|--------|------|-------------|---------|
| 1 | `GET` | `/notes` | `get_notes()` called unconditionally at line 66 | List all notes, newest first |
| 2 | `POST` | `/notes` | `$_POST['content']` at line 50 | Create a note |
| 3 | `DELETE` | `/notes/{id}` | `$_GET['delete']` at line 59 | Delete a note by ID |

**Legacy pattern flags:**
- **DIRECT-OUTPUT** (index.php:50–64): Request dispatch and HTML rendering are in the same file.
- **GLOBAL-VAR** (db.php:7): `$conn` is a PHP global injected into every function — React has no equivalent; the API client handles connection.
- **N+1-QUERY** risk absent: single `get_notes()` query fetches all; no per-note sub-queries.

---

## 4. UI / Controller Layer

### PHP Request Dispatch (lines 47–66)

```
POST ?  → add_note($_POST['content'])
            → ok  : $success = 'Note added.'
            → err : $error   = $result['err']

GET ?delete=N → delete_note((int)N)
            → err : $error = $result['err']

Always: $notes = get_notes()        ← full page reload fetches all notes
```

**DIRECT-OUTPUT flag:** Business logic, data access, and HTML are all rendered in one PHP execution cycle. Each user action results in a full-page HTTP round-trip.

### HTML Page Structure

```
<html lang="en">
  <head>
    charset=UTF-8
    title="Note List"
    link rel="stylesheet" href="style.css"
  </head>
  <body>
    <nav class="navbar">
      brand: "📝 Note List"
      legacy-tag: "Legacy v1.0"
    </nav>
    <div class="container">
      [alert-error]?    ← shown if $error non-empty
      [alert-success]?  ← shown if $success non-empty
      <div class="add-form">
        <form method="POST">
          <textarea name="content" maxlength="500" rows="3">
            [repopulates $_POST['content'] on error]
          </textarea>
          <button type="submit">Add Note</button>
        </form>
      </div>
      [empty state]     ← "No notes yet. Add one above." if $notes empty
      <ul class="note-list">
        <li class="note-card"> × N
          .note-content  ← htmlspecialchars($n['content'])
          .note-date     ← date('d M Y', strtotime($n['created_at']))
          <a class="del-btn" href="?delete={id}"
             onclick="return confirm('Delete this note?')">×</a>
        </li>
      </ul>
    </div>
    <footer>Note List © 2026 — Legacy PHP Application</footer>
  </body>
</html>
```

### React Migration Target Architecture

```
App (root)
├── Navbar                          ← static, no state
├── AlertBanner (type, message)     ← controlled, dismissable or auto-clear
├── AddNoteForm                     ← controlled textarea, submit handler
│     maxLength=500, preserves value on error
├── NoteList (notes[])
│     ├── EmptyState                ← shown when notes.length === 0
│     └── NoteCard × N (note)
│           ├── note-content
│           ├── note-date           ← formatted "dd MMM yyyy"
│           └── DeleteButton        ← confirm dialog → DELETE /notes/{id}
```

**Router:** `GET /notes` → `POST /notes` → `DELETE /notes/{id}`  
**Schemas:** `NoteRead {id, content, created_at}`, `NoteCreate {content}`  
**Service:** `NoteApiClient` — `listNotes()`, `createNote(content)`, `deleteNote(id)`  
**ORM Models:** none (frontend; consumed via REST)  
**Stubs needed:** FastAPI `GET /notes`, `POST /notes`, `DELETE /notes/{id}` from `backend` module

---

## 5. List / Search / Inquiry Pages

### Notes List View (sole view)

| Property | Legacy | React target |
|----------|--------|--------------|
| Page count | 1 (no pagination) | 1 (no pagination — out of scope) |
| Sort order | `created_at DESC` (server-enforced) | Preserve server sort; no client-side sort needed |
| Search/filter | None | None (out of scope) |
| Refresh | Full page reload | `useEffect` on mount + optimistic update after create/delete |
| Empty state | `<p class="empty">No notes yet. Add one above.</p>` | `<EmptyState>` component with same copy |
| Date format | `date('d M Y', ...)` → "20 May 2026" | `new Intl.DateTimeFormat('en-GB', {day:'2-digit', month:'short', year:'numeric'})` |
| Note key | `$n['id']` in foreach | `key={note.id}` in `.map()` |

**DATE-INTERPOLATION flag:** PHP `date('d M Y', strtotime($n['created_at']))` must match exactly. "20 May 2026" format requires `en-GB` locale or manual formatting — not the default US locale output.

---

## 6. Dependency Map

```
frontend (MWU-NL2-002-FE)
    └── depends on → backend (MWU-NL2-001)
            └── exposes → GET /notes
                          POST /notes
                          DELETE /notes/{id}

source/index.php
    └── requires → source/db.php   [GLOBAL-VAR: $conn]
    └── requires → source/style.css [external stylesheet]
```

**Cross-module BR dependencies (consumed from backend, NOT re-extracted):**

| Backend BR | Frontend implication |
|------------|---------------------|
| BR-BACKEND-001: Empty Note Guard | Display "Note cannot be empty" from API 422 response |
| BR-BACKEND-002: Note Length Limit 500 | Mirror with `maxLength={500}` on textarea; display API error if bypassed |
| BR-BACKEND-003: Content Trimming | Transparent to frontend; API strips whitespace |
| BR-BACKEND-004: Invalid ID Guard | DELETE must use valid numeric IDs; `NoteCard` receives `id: number` from list |
| BR-BACKEND-005: Missing Note → 404 | Frontend must handle 404 on delete gracefully |
| BR-BACKEND-006: No Authentication | CRITICAL — React must add NO auth UI whatsoever |
| BR-BACKEND-007: Newest First Order | Frontend relies on API order; no client-side sort |
| BR-BACKEND-008: UTF-8 Storage | JS strings are UTF-16; display renders correctly |
| BR-BACKEND-009: created_at Auto-Set | `NoteCreate` form omits `created_at`; only `NoteRead` shows it |

---

## 7. Business Rules (exhaustive)

### Frontend-Owned Business Rules

---

**BR-FRONTEND-001: Client-Side Length Enforcement (textarea maxlength)**

The add-note textarea carries `maxlength="500"` to prevent submission of oversized content at the browser level. This mirrors the server-side 500-char limit.

- Source: `index.php:94` — `maxlength="500"` attribute
- Priority: MEDIUM
- Status: NEEDS_VALIDATION
- FastAPI/React impl: `<textarea maxLength={500} ...>` — no extra JS needed
- Note: Server validation (BR-BACKEND-002) is authoritative; this is a UX aid only.

---

**BR-FRONTEND-002: Delete Confirmation Dialog**

The user must confirm before a note is deleted. A browser-native confirm dialog is displayed before the delete request is issued.

- Source: `index.php:111` — `onclick="return confirm('Delete this note?')"`
- Priority: HIGH
- Status: NEEDS_VALIDATION
- React impl: `window.confirm('Delete this note?')` in `DeleteButton.onClick`, or a React modal; `window.confirm` is acceptable for parity.
- Copy preserved: `"Delete this note?"`

---

**BR-FRONTEND-003: Date Display Format "dd MMM yyyy"**

Dates are displayed in the format "20 May 2026" (day as 2-digit, month as abbreviated name, 4-digit year).

- Source: `index.php:108` — `date('d M Y', strtotime($n['created_at']))`
- Priority: MEDIUM
- Status: NEEDS_VALIDATION
- React impl: `new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(note.created_at))`
- **DATE-INTERPOLATION flag** — format must match legacy exactly; locale mismatch will produce wrong month names.

---

**BR-FRONTEND-004: Textarea Content Preservation on Validation Error**

When a note submission fails validation, the textarea must retain the user's typed content so they can correct and resubmit without re-typing.

- Source: `index.php:96` — `<?= htmlspecialchars(isset($_POST['content']) ? $_POST['content'] : '') ?>`
- Priority: MEDIUM
- Status: NEEDS_VALIDATION
- React impl: controlled textarea with `value={content}` state; content is not cleared on API error, only on success.

---

**BR-FRONTEND-005: Empty State Message**

When no notes exist, display the message "No notes yet. Add one above." in place of the note list.

- Source: `index.php:102` — `<p class="empty">No notes yet. Add one above.</p>`
- Priority: LOW
- Status: NEEDS_VALIDATION
- React impl: conditional render `{notes.length === 0 && <EmptyState />}`
- Copy preserved exactly: `"No notes yet. Add one above."`

---

**BR-FRONTEND-006: Inline Alert Feedback (Error and Success)**

User-facing feedback is delivered as inline alert banners above the add-note form. Two variants exist: error (red) and success (green).

- Source: `index.php:84–89` — `.alert-error` / `.alert-success` divs; `style.css:9–10`
- Priority: HIGH
- Status: NEEDS_VALIDATION
- Success copy: `"Note added."`
- Error copies: propagated from backend (`"Note cannot be empty"`, `"Note too long (max 500 chars)"`, `"Invalid note ID"`)
- React impl: `AlertBanner` component with `type: 'error' | 'success'` prop; auto-dismissed after success or explicitly dismissed on navigation.
- **DIRECT-OUTPUT flag** (legacy): PHP echoes alerts inline; React separates into component.

---

**BR-FRONTEND-007: No Authentication UI**

The frontend presents no login form, no logout button, no session indicator, and no access control gate. All views are unconditionally public.

- Source: `index.php:1–121` (entire file — absence of auth is the rule)
- Priority: CRITICAL
- Status: NEEDS_VALIDATION
- React impl: No `PrivateRoute`, no `useAuth`, no auth headers, no API key input.
- Cross-reference: BR-BACKEND-006 (No Authentication on API side)
- **ANY_AUTH_PATTERN flag** — ANY auth UI component must be removed before merge.

---

**BR-FRONTEND-008: XSS-Safe Content Display**

Note content is rendered HTML-escaped. User input must never be rendered as raw HTML.

- Source: `index.php:107` — `htmlspecialchars($n['content'])` on display; `index.php:85,88` — `htmlspecialchars($error)`, `htmlspecialchars($success)`
- Priority: HIGH
- Status: NEEDS_VALIDATION
- React impl: React's JSX escapes string content by default — `{note.content}` is safe. Do NOT use `dangerouslySetInnerHTML`.

---

**BR-FRONTEND-009: Notes Displayed Newest First**

The frontend renders notes in the order returned by the API, which is newest first (ORDER BY created_at DESC). No client-side sorting is applied.

- Source: `index.php:11` (get_notes ORDER BY DESC), `index.php:104–113` (foreach render)
- Priority: MEDIUM
- Status: NEEDS_VALIDATION
- React impl: render `notes.map(...)` in array order as returned by `GET /notes`; do not sort client-side.
- Cross-reference: BR-BACKEND-007 (Note Ordering)

---

**BR-FRONTEND-010: Page Title and Brand Identity**

The page title is "Note List". The navbar brand reads "📝 Note List". The legacy-tag "Legacy v1.0" must NOT be carried into the React app (it is a legacy artefact).

- Source: `index.php:74` (`<title>Note List</title>`), `index.php:79–80` (brand + legacy-tag)
- Priority: LOW
- Status: NEEDS_VALIDATION
- React impl: `<title>Note List</title>` in `index.html`; Navbar brand: "📝 Note List"; omit "Legacy v1.0" tag.

---

**BR-FRONTEND-011: Footer Copyright Line**

A footer with "Note List © 2026 — Legacy PHP Application" is displayed at the bottom of the page.

- Source: `index.php:118`
- Priority: LOW
- Status: NEEDS_VALIDATION
- React impl: `<footer>` with updated copy — replace "Legacy PHP Application" with "Modern React Application" or remove the qualifier entirely. NEEDS_VALIDATION on exact copy.

---

## 8. Risk Register

| ID | Severity | Flag | Description | Mitigation |
|----|----------|------|-------------|------------|
| RISK-FE-001 | HIGH | DATE-INTERPOLATION | PHP `date('d M Y')` and JS `Intl.DateTimeFormat` may produce different month abbreviations in non-English locales | Pin locale to `en-GB`; add regression test comparing output for a known date |
| RISK-FE-002 | MEDIUM | DELETE-METHOD-CHANGE | Legacy uses `GET ?delete=N`; React must use `DELETE /notes/{id}` HTTP method. Browsers and crawlers can accidentally trigger legacy deletes via prefetch. | React implementation is an improvement; ensure backend rejects GET-based deletes |
| RISK-FE-003 | MEDIUM | DIRECT-OUTPUT | Full-page reload pattern replaced by SPA; user must not lose data if API call fails | Controlled form state; error displayed inline; content preserved on failure (BR-FRONTEND-004) |
| RISK-FE-004 | LOW | UX-GAP | No live character counter in legacy (only HTML `maxlength` stops typing at 500). React could add one — but this is out of scope for parity migration | Mark as enhancement candidate only; do not add in this MWU |
| RISK-FE-005 | LOW | CONFIRM-DIALOG | `window.confirm()` is synchronous and may be blocked in some embedded browsers | Acceptable for this simple app; document as known limitation |
| RISK-FE-006 | MEDIUM | API-ERROR-CONTRACT | React must correctly parse FastAPI 422 `detail` response to extract user-facing error messages | Map `HTTPException.detail` → `AlertBanner` message; test both validation paths |
| RISK-FE-007 | HIGH | ANY_AUTH_PATTERN | React ecosystem tooling (boilerplates, templates) commonly scaffold auth — must be actively prevented | Discovery agent flags; planning agent must include explicit "no auth" rule in codegen spec |
| RISK-FE-008 | LOW | BRAND-COPY | "Legacy v1.0" tag in navbar should be removed from modern app | Mark as intentional removal in migration notes |

---

## 9. Semgrep Pre-Analysis Confirmation

Semgrep was not run against frontend source files (PHP + CSS only — no JS to scan). The following patterns were checked manually:

| Pattern | Status | Location |
|---------|--------|----------|
| `dangerouslySetInnerHTML` | NOT PRESENT | No JS in legacy |
| Raw SQL string concat | NOT PRESENT in frontend | Present in backend layer (index.php:31) — owned by backend MWU |
| `eval()` / `exec()` | NOT PRESENT | — |
| `innerHTML` assignment | NOT PRESENT | No JS |
| Inline `onclick` with user data | PRESENT | `index.php:111` — `onclick="return confirm(...)"` — static string only, no XSS risk |
| Unescaped output | MITIGATED | All outputs use `htmlspecialchars()` |
| CORS headers | NOT PRESENT | Legacy is server-rendered; React/FastAPI will need CORS config |

**CORS gap:** The PHP app is server-rendered (no cross-origin requests). The React SPA will call FastAPI from a different origin (e.g., `localhost:3000` → `localhost:8000`). FastAPI must be configured with `CORSMiddleware` allowing the React dev origin. This is a backend concern but must be flagged here.

---

## 10. Migration Complexity Assessment

**Overall complexity: LOW**

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| UI complexity | LOW | Single view, ~50 lines of template HTML, minimal interactivity |
| State management | LOW | 3 state variables: notes list, form content, alert message |
| API surface | LOW | 3 endpoints, all simple CRUD |
| CSS complexity | LOW | 28 lines of handwritten CSS, no framework, no responsive breakpoints |
| Business rules | LOW | 11 frontend BRs, mostly display/UX rules; all trivial to implement |
| Dependencies | LOW | No external PHP libraries used in frontend layer |
| Risk | MEDIUM | Date format parity and auth-prevention require explicit attention |

**React migration footprint:**
- ~5–7 React components
- ~150–200 lines of TypeScript/JSX
- ~1 API client file (`noteApi.ts`)
- CSS: migrate `style.css` 1:1 as `App.css` or CSS Modules

**Recommended stack:**
- React 18 + TypeScript
- Vite (dev server)
- Fetch API or Axios for HTTP
- No state management library needed (useState + props sufficient)
- No React Router needed (single view)

---

## 11. Files Written

| Action | Path | Status |
|--------|------|--------|
| Filesystem write | `E:\Claude\note-list-leg2\output\mkb\frontend\track-a\discovery-001.md` | WRITTEN |
| MKB store — discovery_finding | `module=frontend`, artifact stored via `mkb_store_artifact` | PENDING (see below) |
| MKB store — BR-FRONTEND-001 through BR-FRONTEND-011 | `module=frontend`, 11 BRs stored individually | PENDING (see below) |

---

*Discovery Agent — MWU-NL2-002-FE — 2026-05-20*
