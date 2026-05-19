# Comprehension Report — MWU-NL-002-FE Frontend (React)
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** 2026-05-18
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md (2 source files, complexity LOW)
**Rules extracted:** 11 frontend business rules
**MKB artifacts stored:** 11 UUIDs
**Backend BRs referenced (not re-extracted):** 7 (BR-NL-001 through BR-NL-007, MWU-NL-001)

---

## 1. Business Rule Catalog

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-NL-FE-001 | Client-side content validation — reject empty/whitespace-only content before submission with inline error | VALIDATION | index.php:94, :23-26 | HIGH | None | 942c6e26-9098-4da3-b007-870b6d854361 |
| BR-NL-FE-002 | Client-side content length validation — max 500 chars with visible character counter | VALIDATION | index.php:94, :4, :27-29 | HIGH | None | 621ee415-2649-4bf3-ac2b-0600b128bc53 |
| BR-NL-FE-003 | Output escaping — render note content as text only, never dangerouslySetInnerHTML | CONSTRAINT | index.php:85,88,96,107 | HIGH | None | 9f845da3-955d-4466-857c-b3d766622833 |
| BR-NL-FE-004 | Note display order preserved from API (newest first) — do not re-sort | CONSTRAINT | index.php:11 | MEDIUM | None | ccd0a475-1381-4c24-9afc-45ec91f1af10 |
| BR-NL-FE-005 | Date formatting in frontend — API returns ISO 8601, display as "18 May 2026" | TRANSFORMATION | index.php:108 | MEDIUM | None | fc9dfc5f-b1e8-476f-b1cc-666d21b2eb80 |
| BR-NL-FE-006 | No authentication UI — no login, no auth state, no protected routes [CRITICAL] | AUTHORIZATION | index.php (no auth) | CRITICAL | None | b041ce2d-bde1-47d2-9fcc-31bd29e431ef |
| BR-NL-FE-007 | Delete via HTTP DELETE method, not GET — fix CSRF anti-pattern | WORKFLOW | index.php:48-55 | HIGH | None | e6bb3eac-bce7-443b-9ca8-6736a0ede7ff |
| BR-NL-FE-008 | Inline success/error feedback after add/delete operations | WORKFLOW | index.php:69-120 | MEDIUM | None | b206f5f8-0620-41e7-bb5d-b641a6295e08 |
| BR-NL-FE-009 | Single-page layout — all functionality on one page, no routing needed | CONSTRAINT | index.php:69-120 | MEDIUM | None | aaedf7bc-0108-4cbc-8097-9a379932ab7c |
| BR-NL-FE-010 | Trim whitespace from content before submission (mirrors server-side trim) | TRANSFORMATION | index.php:23 | MEDIUM | None | 25dc2cef-79b3-4eb7-b361-164cb55d22a5 |
| BR-NL-FE-011 | Graceful handling of API errors — 422, 404, 5xx, network failures | WORKFLOW | discovery Section 10 | HIGH | None | 459ae16f-9088-4b84-873f-0e0082a9b5ef |

### Backend BRs Referenced (from MWU-NL-001 — not re-extracted)

| Backend BR | Frontend Relevance | Frontend Mirror |
|------------|-------------------|-----------------|
| BR-NL-001 (content not empty) | Client-side pre-validation | BR-NL-FE-001 |
| BR-NL-002 (max 500 chars) | Client-side length enforcement | BR-NL-FE-002 |
| BR-NL-004 (newest first order) | Display order contract | BR-NL-FE-004 |
| BR-NL-005 (no auth — CRITICAL) | No auth UI | BR-NL-FE-006 |
| BR-NL-006 (trim whitespace) | Pre-submission trim | BR-NL-FE-010 |
| BR-NL-007 (silent delete vs 404) | Error handling for 404 | BR-NL-FE-011 |

---

## 2. Implementation Notes for CodeGen Agent

### RISK-002: RAW-SQL-CONCAT — SQL Injection in add_note
**What to do:** Frontend concern is minimal — the API handles parameterized queries. However, the frontend MUST NOT attempt to sanitize or escape content before sending to the API. Send raw user input (after trim). The API/ORM handles SQL safety.
**Pattern to use:** `fetch('/notes', { method: 'POST', body: JSON.stringify({ content: trimmedContent }) })`
**Do NOT:** Pre-escape HTML entities, SQL characters, or special characters before sending to API. That corrupts the data.

### RISK-003: CSRF — DELETE via GET
**What to do:** Use HTTP DELETE method for delete operations. Use a `<button>` element, never an `<a href>` link. Include proper Content-Type headers.
**Pattern to use:** `fetch(\`/notes/\${id}\`, { method: 'DELETE' })` triggered by button onClick handler.
**Do NOT:** Use anchor tags for destructive actions. Do not use GET requests for state-changing operations. Do not embed delete IDs in URL query parameters.

### RISK-005: Unbounded SELECT — No Pagination
**What to do:** The API currently returns all notes. Frontend should render all notes from the response. If pagination is added to the API later, the frontend structure (list component mapping over an array) will naturally accommodate it.
**Pattern to use:** `notes.map(note => <NoteItem key={note.id} note={note} />)` — works for any array length.
**Do NOT:** Implement client-side pagination or virtual scrolling unless the dataset grows large enough to warrant it. Over-engineering for a simple note list.

### RISK-006: Server-side Date Formatting
**What to do:** API returns ISO 8601 timestamps. Format dates in the React component using browser Intl APIs.
**Pattern to use:** `new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(note.created_at))` → "18 May 2026"
**Do NOT:** Import moment.js or other heavy date libraries. Do not request pre-formatted dates from the API. Do not use Date.toLocaleDateString() without explicit locale (inconsistent across browsers).

### RISK-007: Silent Delete of Non-existent ID
**What to do:** The API may return 404 for a delete of a non-existent note (pending NEEDS_VALIDATION on BR-NL-007). Frontend must handle both cases: (a) 200 success → remove note from list, show "Note deleted"; (b) 404 not found → show "Note not found", refresh the list to sync state.
**Pattern to use:** Check `response.status` after DELETE call. Handle 200 and 404 as distinct UX paths.
**Do NOT:** Assume delete always succeeds. Do not ignore the response status.

---

## 3. Ambiguities Requiring SME Resolution

No ambiguities — all frontend rules are unambiguous from source.

The one backend ambiguity (BR-NL-007: silent delete vs 404) affects frontend error handling (BR-NL-FE-011) but the frontend implementation handles both outcomes. No frontend-specific SME decisions are needed.

---

## 4. Cross-Module Dependencies

| BR ID | Depends on | Module | Status |
|-------|-----------|--------|--------|
| BR-NL-FE-001 | BR-NL-001 (server-side empty validation) | backend | EXTRACTED |
| BR-NL-FE-002 | BR-NL-002 (server-side length validation, MAX_NOTE_LENGTH=500) | backend | EXTRACTED |
| BR-NL-FE-004 | BR-NL-004 (API sort order guarantee) | backend | EXTRACTED |
| BR-NL-FE-006 | BR-NL-005 (no auth — CRITICAL) | backend | EXTRACTED |
| BR-NL-FE-007 | Backend DELETE /notes/{id} endpoint must exist | backend | EXTRACTED |
| BR-NL-FE-010 | BR-NL-006 (server-side trim) | backend | EXTRACTED |
| BR-NL-FE-011 | Backend API error response format (422/404/5xx) | backend | EXTRACTED |

**Dependency direction:** Frontend depends on backend API contract. Backend (MWU-NL-001) should be code-generated first. Frontend can proceed once API endpoint signatures and error response format are defined.

---

## 5. MKB Storage Summary

Total rules stored: 11
MKB project: NOTE-LIST-1
MKB module: .
Status: EXTRACTED (pending HITL validation)

UUIDs:
- BR-NL-FE-001: 942c6e26-9098-4da3-b007-870b6d854361
- BR-NL-FE-002: 621ee415-2649-4bf3-ac2b-0600b128bc53
- BR-NL-FE-003: 9f845da3-955d-4466-857c-b3d766622833
- BR-NL-FE-004: ccd0a475-1381-4c24-9afc-45ec91f1af10
- BR-NL-FE-005: fc9dfc5f-b1e8-476f-b1cc-666d21b2eb80
- BR-NL-FE-006: b041ce2d-bde1-47d2-9fcc-31bd29e431ef
- BR-NL-FE-007: e6bb3eac-bce7-443b-9ca8-6736a0ede7ff
- BR-NL-FE-008: b206f5f8-0620-41e7-bb5d-b641a6295e08
- BR-NL-FE-009: aaedf7bc-0108-4cbc-8097-9a379932ab7c
- BR-NL-FE-010: 25dc2cef-79b3-4eb7-b361-164cb55d22a5
- BR-NL-FE-011: 459ae16f-9088-4b84-873f-0e0082a9b5ef

To retrieve for CodeGen:
  mkb_get_business_rules(module=".", project_id="NOTE-LIST-1", status="VALIDATED")

---

## 6. Reviewer Checklist

- [x] All frontend-relevant BRs from discovery Section 7 are captured (7→6 mirrored as FE rules)
- [x] UI/Controller layer concerns from Section 4 are captured (XSS, CSRF, flash messages, layout)
- [x] Each BR has a clear, implementation-ready description with React-specific patterns
- [x] Risk register items (RISK-002, 003, 005, 006, 007) translated to CodeGen instructions in Section 2
- [x] No ambiguities requiring SME resolution for frontend
- [x] All 11 MKB UUIDs recorded for traceability
- [x] Cross-module dependencies on backend API contract identified
- [x] Backend BRs referenced but not re-extracted (avoiding duplication)
- [x] CRITICAL constraint BR-NL-FE-006 (no auth UI) prominently flagged
- [x] Pipeline lesson applied: verified MKB tools active, all BRs stored (not PENDING_MKB_WRITE)

---

## 7. React Component Architecture (CodeGen Guidance)

Based on BR-NL-FE-009 (single-page layout), the recommended component tree:

```
App
├── Header (app title)
├── FeedbackMessage (BR-NL-FE-008: success/error inline messages)
├── AddNoteForm (BR-NL-FE-001, 002, 010: validation + trim + char counter)
│   ├── textarea (maxLength=500, char counter)
│   └── submit button
├── NoteList (BR-NL-FE-004: render in API order)
│   └── NoteItem[] (BR-NL-FE-003: text-only render, BR-NL-FE-005: formatted date)
│       ├── note content (text, not HTML)
│       ├── formatted created_at date
│       └── delete button (BR-NL-FE-007: HTTP DELETE)
└── Footer

API layer: single api.js/ts module
  - getNotes()     → GET /notes
  - createNote()   → POST /notes
  - deleteNote(id) → DELETE /notes/{id}
  All with error handling per BR-NL-FE-011
```

No React Router. No state management library (useState sufficient). No auth provider.

