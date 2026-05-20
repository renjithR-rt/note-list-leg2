# Frontend — Business Requirements Document
**Project:** NOTE-LIST-2
**MWU:** MWU-NL2-002-FE
**Module:** frontend
**Scope:** per_mwu
**Generated:** 2026-05-20
**Version:** 1.0
**Status:** DRAFT

> This document was generated from business rules extracted by the
> migration pipeline. All BR IDs are traceable to the Migration
> Knowledge Base under project NOTE-LIST-2.
> To propose changes: edit this document and re-submit for review.

---

## 1. Module Overview

### 1.1 Purpose
The frontend module provides the user-facing interface for the Note List application. It allows any visitor (no login required) to view existing notes, create a new note via a simple form, and delete an existing note after confirmation. It is a single-page React application that replaces a legacy server-rendered PHP page while preserving every visible behaviour of the original.

### 1.2 Scope
**In scope:**
- A single page displaying all stored notes in newest-first order.
- A textarea form for creating a new note (with a 500-character client-side limit).
- A per-note delete control that requires confirmation before submission.
- Inline success and error banners above the form.
- A static page header (brand "📝 Note List") and footer copyright line.
- Date display in "dd MMM yyyy" format using the `en-GB` locale.
- Error message parsing for FastAPI / Pydantic response payloads.

**Explicitly out of scope:**
- Any authentication, login, logout, session indicator, or protected route.
- Search, filter, sort toggle, pagination, or "load more" controls.
- Edit-in-place, rich-text formatting, attachments, or tagging.
- Live character counters or progress bars.
- Routing beyond the single notes page.
- Carry-over of the legacy "Legacy v1.0" tag or "Legacy PHP Application" footer text.

### 1.3 Key Stakeholders
- **End user (visitor):** anyone with the URL; views, creates and deletes notes without identifying themselves.
- **Product Owner:** owns the parity expectation between the legacy PHP app and the new React app.
- **Business Analyst:** validates this document and confirms ambiguities in Section 5.
- **Frontend Engineer (CodeGen Agent consumer):** implements the React components against the rules listed here.
- **Backend Engineer (MWU-NL2-001):** owns the FastAPI endpoints this UI consumes.

### 1.4 Module Dependencies
- **Backend module (MWU-NL2-001):** the React app consumes `GET /notes`, `POST /notes`, and `DELETE /notes/{id}` from the FastAPI service. Frontend behaviour for note ordering, length limits, empty-content rejection, and 404-on-missing-note is driven by backend rules BR-BACKEND-001, 002, 005, 006, 007.
- **CORS configuration (infrastructure, not a BR):** the React SPA will run on a different origin than the FastAPI service (e.g. `localhost:3000` vs `localhost:8000`). The backend must enable `CORSMiddleware` for the React dev origin. This is flagged here as a runtime dependency; the frontend does not implement it.

---

## 2. Business Rules Catalogue

### BR-FRONTEND-001: Client-side note length limit

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-001 |
| **Priority** | MEDIUM |
| **Source File** | index.php line 94 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
The note-entry textarea must prevent users from typing more than 500 characters at the browser level. This is a usability aid; the authoritative length check is enforced by the backend (BR-BACKEND-002).

**Business Logic:**
1. When the user focuses the textarea and types, the browser stops accepting input once 500 characters have been entered.
2. Pasting longer content is also truncated at 500 characters.
3. If the client-side limit is somehow bypassed, the backend will reject the submission with an error which is then displayed via the error banner.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Note content | Text | The user-typed note body | Max 500 characters at client level |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Input accepted | length ≤ 500 | Character is added to the textarea |
| Input blocked | length = 500 and user types more | Browser silently rejects additional input |

**Validation Rules:**
- The textarea must declare a maximum length of 500 characters.
- The frontend must not add any visible character counter, progress bar, or countdown (see Section 7 — out of scope).

**Edge Cases:**
- Paste of > 500 characters: browser truncates to first 500 characters; no error banner is shown.
- Server still rejects via BR-BACKEND-002: the backend error message is surfaced through BR-FRONTEND-006 (error banner).

**Dependencies:**
- BR-BACKEND-002 (Note Length Limit 500): the authoritative server-side check.

---

### BR-FRONTEND-002: Delete confirmation required

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-002 |
| **Priority** | HIGH |
| **Source File** | index.php line 111 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
Before any delete request is sent to the backend, the user must confirm the action via a native browser confirmation dialog showing the text "Delete this note?". Cancelling the dialog must abort the operation; no HTTP request is sent.

**Business Logic:**
1. The user clicks the delete control on a note.
2. The browser shows a confirmation dialog with the text "Delete this note?".
3. If the user confirms, a DELETE request is sent to the backend.
4. If the user cancels, nothing happens — no request, no state change, no banner.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| User click | Event | Click on delete control of a specific note | Must originate from delete control |
| User dialog response | Boolean | Result of the confirm dialog | true (OK) or false (Cancel) |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Delete proceeds | User clicks OK | DELETE request is sent for that note |
| Delete cancelled | User clicks Cancel | No request is sent, list is unchanged |

**Validation Rules:**
- The confirmation prompt text must be exactly "Delete this note?".
- The dialog must be invoked synchronously on the click event so the OS-level confirm can be presented before any network call.

**Edge Cases:**
- Embedded browser or kiosk environment where confirm dialogs are blocked: known limitation; not in scope to build a custom modal (see RISK-FE-005 in source comprehension).
- Rapid double-click: the second click should also show a confirmation dialog (no auto-confirm).

**Dependencies:**
- BR-FRONTEND-013 (Delete uses HTTP DELETE method): confirmation precedes the actual DELETE call.

---

### BR-FRONTEND-003: Date display format "dd MMM yyyy" in en-GB locale

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-003 |
| **Priority** | MEDIUM |
| **Source File** | index.php line 108 |
| **Confidence** | MEDIUM |
| **Status** | NEEDS_VALIDATION |

**Description:**
Each note's `created_at` timestamp is displayed using the format "day month-abbrev year" with a zero-padded day (e.g. "20 May 2026", "05 Jan 2026"). The locale must be pinned to `en-GB` so the month abbreviation is always English.

**Business Logic:**
1. The frontend receives an ISO timestamp from the backend (e.g. "2026-05-20T10:15:00Z").
2. The frontend formats the date using the `en-GB` locale with two-digit day, short month, and four-digit year.
3. The formatted string is displayed next to the note body.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| created_at | ISO timestamp string | Timestamp returned by the backend | Valid ISO 8601 string |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Formatted date | Always | A string in the form "dd MMM yyyy", e.g. "20 May 2026" |

**Validation Rules:**
- Locale must be pinned to `en-GB`; the user's system locale must not affect output.
- Day must be zero-padded to two digits (matching legacy PHP `date('d M Y')`).
- A regression test must assert that the ISO string `2026-01-05T00:00:00Z` formats to exactly `"05 Jan 2026"`.

**Edge Cases:**
- Missing or invalid `created_at`: out of scope; backend guarantees a valid timestamp (BR-BACKEND-009).
- Time-zone display: only the date is shown, no time. The default device time zone is used to determine the calendar date.

**Dependencies:**
- BR-BACKEND-009 (created_at Auto-Set): the backend always populates created_at.

**Open Question:** see Section 5 — confirm whether the zero-padded day ("05 May") is the intended business behaviour or whether the unpadded day ("5 May") was expected.

---

### BR-FRONTEND-004: Preserve form content on validation error

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-004 |
| **Priority** | MEDIUM |
| **Source File** | index.php line 96 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
When the backend rejects a create-note submission (e.g. empty content or length violation), the textarea must retain the user's typed content so they can correct it without retyping. The textarea is cleared only after a successful create.

**Business Logic:**
1. User types content and clicks submit.
2. If the backend returns an error, the textarea keeps the typed content and an error banner is shown (BR-FRONTEND-006).
3. If the backend returns success, the textarea is cleared and a success banner is shown.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Submission outcome | Success/Error | The result returned by the backend | Either 2xx or error response |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Textarea cleared | Backend returned success | Field is reset to empty |
| Textarea preserved | Backend returned error | Field still holds the user's text |

**Validation Rules:**
- The textarea must not be cleared in any error path.
- The textarea must always be cleared on a successful create.

**Edge Cases:**
- Network error before the backend responds: treat as an error path; preserve content.
- User edits the textarea while a request is in flight: see BR-FRONTEND-014 (double-submit prevention).

**Dependencies:**
- BR-BACKEND-001 (Empty Note Guard) and BR-BACKEND-002 (Length Limit): the error sources this rule responds to.

---

### BR-FRONTEND-005: Empty-state message when no notes exist

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-005 |
| **Priority** | LOW |
| **Source File** | index.php line 102 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
When the notes list is empty, the application must display the exact text "No notes yet. Add one above." in the area where notes would normally appear.

**Business Logic:**
1. The frontend retrieves notes from the backend.
2. If the returned list contains zero notes, the empty-state message is rendered in place of the list.
3. If at least one note is returned, the empty-state message is hidden and the list is rendered.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Notes list | Array | The list returned by GET /notes | May be empty |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Empty-state shown | List length = 0 | Text "No notes yet. Add one above." is displayed |
| List shown | List length > 0 | All notes are rendered, empty-state is hidden |

**Validation Rules:**
- The copy must match the legacy text exactly, including punctuation and capitalisation.

**Edge Cases:**
- Initial load before the fetch completes: out of scope here; loading indicator is governed by BR-FRONTEND-014.
- Fetch error: an error banner is shown (BR-FRONTEND-006); the empty-state message is not used as an error fallback.

**Dependencies:**
- BR-BACKEND-007 (Newest First Order): the backend may legitimately return an empty list.

---

### BR-FRONTEND-006: Mutually exclusive inline alert banners

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-006 |
| **Priority** | HIGH |
| **Source File** | index.php lines 84–89 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
Above the create-note form, the application shows at most one inline banner at a time: a red error banner or a green success banner. Both banners are never visible simultaneously. On a successful create the banner reads "Note added."; error banner content is taken from the backend response.

**Business Logic:**
1. On a successful create, hide any error banner and show a green success banner with the text "Note added.".
2. On a failed create or delete, hide any success banner and show a red error banner with the message extracted from the backend response.
3. A subsequent action (success or error) replaces the currently visible banner.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| API response | Success/Error | Result of POST /notes or DELETE /notes/{id} | HTTP status + body |
| Backend error message | String | Extracted via BR-FRONTEND-015 | Plain text, never raw JSON |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Success banner | Create succeeded | Green banner with "Note added." |
| Error banner | Any failed mutation | Red banner with the extracted message |
| No banner | After initial load with no actions | Neither banner is shown |

**Validation Rules:**
- The success copy must be exactly "Note added.".
- Error banner text must be a human-readable string, never a raw JSON object.
- Success and error banners must be mutually exclusive — never visible at the same time.

**Edge Cases:**
- Successive errors: the error banner updates to the latest message.
- A successful action immediately after an error: the error banner is replaced by the success banner.
- Banner dismissal: not required; banners are replaced by the next action's banner.

**Dependencies:**
- BR-BACKEND-001, BR-BACKEND-002, BR-BACKEND-005 (error messages originate from these backend rules).
- BR-FRONTEND-008 (XSS prevention) — banner text must be safely escaped.
- BR-FRONTEND-015 (Error message parsing).

---

### BR-FRONTEND-007: No authentication UI whatsoever

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-007 |
| **Priority** | HIGH (CRITICAL constraint) |
| **Source File** | index.php lines 1–121 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
The application must contain no authentication user-interface or behaviour of any kind. No login form, no logout button, no signed-in indicator, no protected routes, no auth context, no user profile menu, and no `Authorization` header on any HTTP request. Every view is unconditionally public, mirroring the legacy PHP application.

**Business Logic:**
1. Any visitor with the URL can view the notes list, create a note, and delete a note.
2. No identity check is performed in the UI.
3. All API calls go out without any auth credentials.
4. Any boilerplate authentication scaffolding produced by templates or starters must be removed before the code is shipped.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Visitor | Anonymous | Any user reaching the page | None |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Full access | Always | All UI elements are accessible to every visitor |
| No auth headers | Always | API requests carry no Authorization header |

**Validation Rules:**
- No `AuthProvider`, `ProtectedRoute`, `useAuth`, or equivalent abstraction may exist in the codebase.
- No token storage (localStorage, sessionStorage, cookies) related to authentication may exist.
- No `Authorization` header may be attached to any `fetch` or HTTP client call.
- No login or logout route or component may exist.

**Edge Cases:**
- Template starter ships with auth scaffolding: it must be stripped completely before commit.
- Future requirement for auth: out of scope for this MWU — would require a new BR.

**Dependencies:**
- BR-BACKEND-006 (No Authentication on API): the backend mirrors this stance.

---

### BR-FRONTEND-008: XSS prevention via framework auto-escaping

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-008 |
| **Priority** | HIGH |
| **Source File** | index.php lines 85, 88, 96, 107 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
All user-supplied content (note bodies, backend error messages) must be rendered through the framework's default auto-escaping behaviour. Mechanisms that bypass escaping for user content are forbidden.

**Business Logic:**
1. Note body text from the backend is rendered as plain text via the framework's default text node insertion, ensuring any HTML or script in the content is displayed literally rather than executed.
2. Backend error messages displayed in the error banner are likewise rendered as escaped text.
3. The "no notes yet" empty-state and other static literal copy can be rendered as normal markup.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Note body | String | User-supplied text from the backend | May contain any printable characters |
| Error message | String | Extracted from backend response | Plain text |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Escaped rendering | Always for user content | Any HTML metacharacters in the text appear as literal characters in the DOM |

**Validation Rules:**
- Any mechanism that injects raw HTML for user-supplied content is prohibited (no exceptions).
- This is a security-critical rule; reviewers must reject any change that bypasses escaping for user data.

**Edge Cases:**
- Notes containing what looks like HTML tags: rendered as literal text.
- Notes containing URLs: rendered as plain text (no auto-link conversion is required).

**Dependencies:**
- None (security-foundational rule).

---

### BR-FRONTEND-009: Notes rendered in API-returned order; no client-side sort

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-009 |
| **Priority** | MEDIUM |
| **Source File** | index.php lines 11, 104–113 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
The frontend must display notes in the exact order they are returned by the backend `GET /notes` endpoint. The backend guarantees newest-first ordering (BR-BACKEND-007). The frontend must not re-sort, reverse, or otherwise reorder the list, and must not provide a sort toggle.

**Business Logic:**
1. The frontend issues `GET /notes` and receives an ordered array.
2. The frontend renders each note in array order, top to bottom.
3. After a create or delete, the list is refreshed from the backend; the refreshed order is again rendered as-is.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Notes array | Array | Result of GET /notes | Server-defined order |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| List rendered in order | Always | Each element of the array is rendered in array order |

**Validation Rules:**
- No client-side sort, reverse, or other reorder operation may be applied to the notes array before rendering.
- No UI control for changing order may exist.

**Edge Cases:**
- Backend changes its ordering: the frontend automatically reflects whatever the backend returns.

**Dependencies:**
- BR-BACKEND-007 (Newest First Order).

---

### BR-FRONTEND-010: Page title and navbar branding

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-010 |
| **Priority** | LOW |
| **Source File** | index.php lines 74, 79–80 |
| **Confidence** | HIGH |
| **Status** | NEEDS_VALIDATION |

**Description:**
The page title (browser tab title) must be "Note List". The navbar brand text must be "📝 Note List". The legacy "Legacy v1.0" tag is intentionally removed in the migrated app.

**Business Logic:**
1. On load, the document title is set to "Note List".
2. The navbar at the top of the page shows the brand text "📝 Note List" (note-pad emoji followed by a space and the words "Note List").
3. No version tag or "Legacy" qualifier appears anywhere in the navbar.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Page load | Event | Initial render of the page | Always applies |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Tab title | Always | "Note List" |
| Navbar brand | Always | "📝 Note List" |

**Validation Rules:**
- The strings must match exactly (including the emoji and single space).
- The "Legacy v1.0" tag must not appear.

**Edge Cases:**
- Emoji not rendered in some browsers: accept native fallback; do not substitute with an SVG.

**Dependencies:**
- None.

**Open Question:** see Section 5 — confirm whether a version indicator should replace "Legacy v1.0" (e.g. "v2.0") or whether the navbar should remain version-free.

---

### BR-FRONTEND-011: Footer copyright line

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-011 |
| **Priority** | LOW |
| **Source File** | index.php line 118 |
| **Confidence** | MEDIUM |
| **Status** | NEEDS_VALIDATION |

**Description:**
The page must display a footer copyright line. The legacy text was "Note List © 2026 — Legacy PHP Application". The qualifier "Legacy PHP Application" must be replaced in the migrated app; the exact replacement copy is pending SME confirmation.

**Business Logic:**
1. The footer is rendered at the bottom of the page on every view.
2. The footer copy includes the product name ("Note List"), a copyright symbol, the year, and an application qualifier.
3. The "Legacy PHP Application" qualifier from the legacy version must not be carried over.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Page load | Event | Initial render of the page | Always applies |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Footer line | Always | A single line of copyright text below the main content |

**Validation Rules:**
- Must not contain the words "Legacy PHP Application".
- Must include the product name "Note List", a copyright symbol, and the year 2026.

**Edge Cases:**
- Year rollover: not in scope for this MWU; hard-coded year is acceptable.

**Dependencies:**
- None.

**Open Question:** see Section 5 — confirm the exact replacement footer copy (e.g. "Modern React Application", "React Edition", or no qualifier at all).

---

### BR-FRONTEND-012: No search, filter, sort or pagination

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-012 |
| **Priority** | HIGH |
| **Source File** | index.php lines 101–115; Discovery Section 5 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
The notes list is a flat, unfiltered, unsorted, unpaginated display of every note returned by the backend. The frontend must not provide any search box, filter control, sort toggle, "load more" button, or pagination control. This is a strict parity replication of the legacy app.

**Business Logic:**
1. The frontend fetches all notes via a single `GET /notes` call.
2. All returned notes are rendered.
3. No UI affordance exists for filtering, searching, sorting, or paging through the list.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Notes array | Array | Full result of GET /notes | All notes, single page |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Flat list | Always | Every note rendered once, no controls around the list |

**Validation Rules:**
- No search input, filter dropdown, sort button, or pagination control may exist.

**Edge Cases:**
- Very large note count (e.g. thousands): out of scope; backend currently returns all notes (BR-BACKEND-007).

**Dependencies:**
- BR-BACKEND-007 (Newest First Order, returns all notes, no pagination).

---

### BR-FRONTEND-013: Delete uses HTTP DELETE method

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-013 |
| **Priority** | MEDIUM |
| **Source File** | index.php lines 109–111; RISK-FE-002 |
| **Confidence** | HIGH |
| **Status** | EXTRACTED |

**Description:**
Delete operations must use the HTTP DELETE method against `/notes/{id}`. The legacy app used a GET request with a `?delete={id}` query string as a PHP-era convenience. The migrated app must use the proper HTTP verb. This is a protocol upgrade only — the user-visible behaviour is identical.

**Business Logic:**
1. After confirmation (BR-FRONTEND-002), the frontend sends an HTTP DELETE request to `/notes/{id}` where `{id}` is the numeric id of the note being deleted.
2. On a 2xx response, the list is refreshed (BR-FRONTEND-009).
3. On any error, the error banner is shown (BR-FRONTEND-006).

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Note id | Integer | Numeric id of the note to delete | Positive integer, taken from the rendered note data |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Note removed | Backend returned 2xx | List refresh shows the note no longer present |
| Delete failed | Backend returned 4xx/5xx | Error banner is shown, note remains in list |

**Validation Rules:**
- No GET-based delete pattern (`?delete=` or link-based delete) is permitted.
- Request URL must be `/notes/{id}` with a numeric id.

**Edge Cases:**
- Note already deleted (backend returns 404): error banner shown (BR-FRONTEND-015 parses 404 detail).

**Dependencies:**
- BR-FRONTEND-002 (Delete confirmation), BR-BACKEND-005 (Missing Note → 404).

---

### BR-FRONTEND-014: Prevent double-submit during async API calls

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-014 |
| **Priority** | MEDIUM |
| **Source File** | Migration requirement (RISK-FE-003) |
| **Confidence** | MEDIUM |
| **Status** | NEEDS_VALIDATION |

**Description:**
While an asynchronous API call (create or delete) is in flight, the user must not be able to trigger a second submission of the same action. Minimum behaviour is to disable the submit button while a request is pending. Whether a visible loading indicator (spinner) is additionally required is an open question for the product owner.

**Business Logic:**
1. When the user submits the create form, the submit button becomes disabled until the response is received.
2. While disabled, additional clicks have no effect.
3. On response (success or error), the button is re-enabled.
4. Equivalent behaviour applies to delete: the specific delete control of an in-flight delete is disabled until the response.

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| Submit click | Event | A user click on submit or delete | Triggers an API call |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Button disabled | Request in flight | Button is non-interactive |
| Button re-enabled | Response received | Button is interactive again |

**Validation Rules:**
- Submit button must be disabled while the corresponding request is pending.
- Re-enable must happen for both success and error responses.

**Edge Cases:**
- Network never responds: button remains disabled until a configurable timeout or the user reloads (timeout policy is not part of this MWU).
- User opens dev tools and forces a click: out of scope.

**Dependencies:**
- None (new in migration).

**Open Question:** see Section 5 — confirm whether a visible spinner is required alongside button-disabling, or whether button-disable alone is sufficient.

---

### BR-FRONTEND-015: Parse FastAPI / Pydantic error responses into user-facing text

| Field | Value |
|---|---|
| **Requirement ID** | BR-FRONTEND-015 |
| **Priority** | HIGH |
| **Source File** | RISK-FE-006; Discovery Section 4 |
| **Confidence** | MEDIUM |
| **Status** | EXTRACTED |

**Description:**
The frontend must parse error responses from the FastAPI backend and extract a human-readable message for display in the error banner. The backend uses two response shapes for the `detail` field: a string (for `HTTPException` cases like 400/404) and an array of validation objects (for Pydantic 422 validation errors).

**Business Logic:**
1. When an API call returns a non-success response, the frontend reads the JSON body.
2. If `detail` is a string, that string is the user-facing message.
3. If `detail` is an array, the message is the first validation entry's `msg` field; if that is missing, a fallback such as "Validation error" is used.
4. If the body cannot be parsed as JSON, a generic fallback such as "An error occurred" is used.
5. The resulting string is shown in the error banner (BR-FRONTEND-006).

**Inputs:**
| Input | Type | Description | Constraints |
|---|---|---|---|
| HTTP response | Response object | Result of POST /notes or DELETE /notes/{id} | Non-2xx status |

**Outputs / Outcomes:**
| Outcome | Condition | Description |
|---|---|---|
| Extracted message | detail is string | Display the string directly |
| Extracted first validation message | detail is array | Display first entry's msg or "Validation error" |
| Generic fallback | Body unparseable or no detail | Display "An error occurred" |

**Validation Rules:**
- Never display raw JSON, stack traces, or error objects in the UI.
- The extraction logic must safely handle missing or malformed `detail` fields.

**Edge Cases:**
- HTTP 5xx with no JSON body: fall back to "An error occurred".
- Network error before any HTTP response: fall back to "An error occurred" (or a network-specific message).
- Pydantic 422 with multiple errors: only the first is shown.

**Dependencies:**
- BR-FRONTEND-006 (Banner display).
- Backend error contract from MWU-NL2-001 (FastAPI HTTPException, Pydantic validation).

---

## 3. Data Requirements

### 3.1 Database Tables Used
| Table | Operation | Key Fields | Purpose |
|---|---|---|---|
| (none — frontend module) | N/A | N/A | The frontend does not access any database directly. All data is fetched from the backend API. The underlying `notes` table is owned by MWU-NL2-001. |

### 3.2 Data Constraints
The frontend mirrors and depends on the following data constraints owned by the backend:
- Note content is a string of 1–500 characters (BR-BACKEND-001, BR-BACKEND-002). The textarea enforces the upper bound (BR-FRONTEND-001); the backend is authoritative for both bounds.
- Each note has a numeric `id` (positive integer) — used as the path parameter for DELETE (BR-FRONTEND-013).
- Each note has a `created_at` ISO timestamp set by the backend (BR-BACKEND-009) — formatted via BR-FRONTEND-003.
- Notes are returned by the backend in newest-first order (BR-BACKEND-007) and consumed as-is (BR-FRONTEND-009).
- Note content is UTF-8 in storage (BR-BACKEND-008); JavaScript strings render it correctly (BR-FRONTEND-008 escaping applies).

### 3.3 Data Flows
- **Read flow:** On initial page load, and again after any successful create or delete, the frontend calls `GET /notes` and receives an ordered array. The array is rendered as a flat list (BR-FRONTEND-009, BR-FRONTEND-012); an empty array triggers the empty-state copy (BR-FRONTEND-005).
- **Create flow:** The user types into a 500-character-capped textarea (BR-FRONTEND-001), clicks submit, and the frontend disables the button (BR-FRONTEND-014) and posts to `/notes`. On success the textarea is cleared (BR-FRONTEND-004), the success banner is shown (BR-FRONTEND-006), and the list is refreshed. On error the textarea is preserved and the error banner is shown.
- **Delete flow:** The user clicks delete on a note, confirms via the native dialog (BR-FRONTEND-002), and the frontend issues `DELETE /notes/{id}` (BR-FRONTEND-013). On success the list is refreshed; on error the banner is shown.

---

## 4. Integration Points

### 4.1 Modules Called
| Module | Function | Purpose |
|---|---|---|
| Backend (MWU-NL2-001) | GET /notes | List all notes in newest-first order |
| Backend (MWU-NL2-001) | POST /notes | Create a new note from the textarea content |
| Backend (MWU-NL2-001) | DELETE /notes/{id} | Delete a single note after user confirmation |

### 4.2 External Systems
| System | Integration Type | Purpose |
|---|---|---|
| FastAPI service (MWU-NL2-001) | REST (JSON over HTTP) | The sole external dependency; provides note data and persistence |

### 4.3 Shared Data Structures
- **Note (read shape):** `{ id: number, content: string, created_at: ISO 8601 string }` — produced by the backend, consumed by the frontend's list and date-formatter.
- **NoteCreate (write shape):** `{ content: string }` — produced by the frontend form, consumed by the backend's POST handler. The frontend must not send `id` or `created_at`.
- **HTTPException error shape:** `{ detail: string }` — used by 400/404 responses; parsed by BR-FRONTEND-015.
- **Pydantic validation error shape:** `{ detail: Array<{ loc, msg, type, ... }> }` — used by 422 responses; parsed by BR-FRONTEND-015.

---

## 5. Open Questions

The following BRs have confidence below HIGH or status NEEDS_VALIDATION and require SME confirmation before sign-off.

| # | Question | Related BR | Impact | Owner |
|---|---|---|---|---|
| 1 | Is the leading-zero day in date display intentional ("05 May 2026" vs "5 May 2026")? Legacy PHP `date('d M Y')` produces the zero-padded form. | BR-FRONTEND-003 | MEDIUM | Product Owner |
| 2 | What exact copy should replace "Legacy PHP Application" in the footer (e.g. "Modern React Application", "React Edition", remove the qualifier)? | BR-FRONTEND-011 | LOW | Product Owner |
| 3 | Is a visible loading indicator (spinner) required during async create/delete calls, or is disabling the submit button sufficient? | BR-FRONTEND-014 | MEDIUM | Product Owner / UX |
| 4 | Confirm removal of the legacy "Legacy v1.0" navbar tag. Should any version indicator (e.g. "v2.0") replace it, or should the navbar remain version-free? | BR-FRONTEND-010 | LOW | Product Owner |

---

## 6. Assumptions

1. The backend API (MWU-NL2-001) implements the endpoints `GET /notes`, `POST /notes`, and `DELETE /notes/{id}` with the response shapes described in Section 4.3.
2. The backend will be configured with permissive CORS for the React dev origin (e.g. `http://localhost:3000`), enabling the SPA to call the API from a different origin. This is an infrastructure concern flagged to the backend team.
3. React (or an equivalent JSX-based framework) is used and its default escaping behaviour is in effect for all user-supplied content (BR-FRONTEND-008).
4. The browser's native confirmation dialog is acceptable for delete confirmation in all target environments (per the comprehension risk register RISK-FE-005).
5. The migrated application is intentionally public, mirroring the legacy app. There is no authentication requirement now or in scope of this MWU.
6. The migrated application targets parity with the legacy app: no new features, no character counters, no live previews, no edit-in-place.
7. The current legacy app does not need to remain reachable at the same URL once the React app is deployed; URL migration is handled outside this BRD.
8. Date display uses the device's local time zone for calendar-day calculation; only the date (not the time) is shown.

---

## 7. Out of Scope

The following items are explicitly excluded from MWU-NL2-002-FE and must not be implemented as part of this work:

1. **Authentication and authorisation of any kind** — no login, logout, signed-in indicator, protected route, role check, token storage, or Authorization header (BR-FRONTEND-007).
2. **Search, filter, sort toggle, "load more", or pagination controls** (BR-FRONTEND-012).
3. **Edit-in-place, rich-text formatting, attachments, tags, categories, or note ownership.**
4. **Visible live character counter, progress bar, or character countdown** (RISK-FE-004).
5. **Custom modal for delete confirmation** — the native browser confirm is the only required mechanism (RISK-FE-005).
6. **Client-side note sorting or reordering** — display follows backend order verbatim (BR-FRONTEND-009).
7. **Client-side data caching beyond a simple refresh-after-mutation** — no offline mode, no service worker, no IndexedDB sync.
8. **Multi-page routing or sub-views** — the application is a single page.
9. **Carry-over of legacy branding** — "Legacy v1.0" tag and "Legacy PHP Application" footer qualifier are removed (BR-FRONTEND-010, BR-FRONTEND-011).
10. **Internationalisation beyond pinning the date locale to `en-GB`** — all other copy is English only.
11. **Analytics, telemetry, error reporting, or feature flags.**

---

## 8. Approval

**Instructions for approvers:**
- Review each Business Rule in Section 2
- Add your name, date, and signature when satisfied
- For corrections: edit this document and return to the pipeline for processing
- Partial approval: mark individual BRs as APPROVED / REJECTED / NEEDS_CLARIFICATION

| Role | Name | Date | Decision | Comments |
|---|---|---|---|---|
| Business Analyst | | | | |
| Product Owner | | | | |
| Tech Lead | | | | |

**Overall Approval Status:** ⏳ PENDING_REVIEW

---

## 9. Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-20 | br-doc-agent | Initial generation from comprehension-001.md; 15 BRs catalogued (BR-FRONTEND-001 through BR-FRONTEND-015), 4 open questions flagged for SME resolution. |

---
*Generated by br-doc-agent · NOTE-LIST-2 · MWU-NL2-002-FE*
*BR IDs traceable to MKB: POST http://localhost:8765/artifacts/search*
*{"project_id": "NOTE-LIST-2", "namespace": "requirements"}*
