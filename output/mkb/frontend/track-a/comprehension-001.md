# Comprehension Report — MWU-NL2-002-FE Frontend
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** 2026-05-20
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md (3 source files, complexity LOW)
**Rules extracted:** 14 business rules (11 from discovery + 3 supplementary from Leg1)
**MKB artifacts stored:** 14 UUIDs (5 newly stored, 9 existing from Leg1)

---

## 1. Business Rule Catalog

### Primary Rules (from Discovery Section 7)

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-FRONTEND-001 | Client-side textarea enforces maxlength=500 to prevent oversized submissions; mirrors server-side BR-BACKEND-002 | VALIDATION | index.php:94 | MEDIUM | Char vs byte for multi-byte chars (see BR-BACKEND-002) | e187fa65-b69b-4b2e-b7c2-e41c3a071f3b |
| BR-FRONTEND-002 | User must confirm deletion via browser confirm dialog before DELETE request is sent; cancelling prevents the call | CONSTRAINT | index.php:111 | HIGH | Custom modal vs window.confirm for parity? | 209b7e16-28fc-4b51-9499-435f6a0316f6 |
| BR-FRONTEND-003 | Dates displayed as "dd MMM yyyy" (e.g., "20 May 2026") — PHP `date('d M Y')` zero-pads the day | TRANSFORMATION | index.php:108 | MEDIUM | Confirm "01 May" (leading zero) vs "1 May" intent | 9dab357f-c8b3-4b86-b171-da1d69fc9bb3 |
| BR-FRONTEND-004 | On validation error, textarea retains user's typed content for correction without retyping | CONSTRAINT | index.php:96 | MEDIUM | None | 328b2a6f-2409-4883-8bf6-5ba03ef07ea1 |
| BR-FRONTEND-005 | When no notes exist, display "No notes yet. Add one above." — exact copy preserved | CONSTRAINT | index.php:102 | LOW | None | 02234b46-f3d2-4a3c-b4e7-d69980482897 |
| BR-FRONTEND-006 | Inline alert banners: error (red) and success (green), mutually exclusive — clear both before each API call, set only the relevant one on response. Success copy: "Note added." Error copies propagated from backend 422 detail. | CONSTRAINT | index.php:84-89, style.css:9-10 | HIGH | None | b609d7fe-d067-458d-a8b6-7309de7b981f |
| BR-FRONTEND-007 | NO authentication UI whatsoever — no login form, logout button, session indicator, protected routes, auth context, or auth headers. HARD CONSTRAINT. | AUTHORIZATION | index.php (entire file — absence is the rule) | CRITICAL | None | 016592ea-4f0c-40b8-8ab1-f5d5e2b72233 |
| BR-FRONTEND-008 | Note content rendered XSS-safe. React JSX auto-escapes string expressions. NEVER use dangerouslySetInnerHTML for user data. | VALIDATION | index.php:85,88,96,107 | HIGH | None | 4e336242-1df5-44ba-9211-833c3a7d14ac |
| BR-FRONTEND-009 | Notes rendered newest first, in server-returned order. No client-side sorting applied or allowed. | CONSTRAINT | index.php:11, 104-113 | MEDIUM | None | b240d0bc-629a-4638-a493-93ed56f2097e |
| BR-FRONTEND-010 | Page title: "Note List". Navbar brand: "📝 Note List". Remove "Legacy v1.0" tag (legacy artefact). | TRANSFORMATION | index.php:74, 79-80 | LOW | Confirm "Legacy v1.0" removal acceptable | ea0a0633-5d71-4c43-aa8c-f88cfbd166be |
| BR-FRONTEND-011 | Footer displays copyright line. Legacy: "Note List (c) 2026 -- Legacy PHP Application". Update qualifier for modern app. | TRANSFORMATION | index.php:118 | LOW | Exact footer copy needs product owner decision | 1e955235-7a82-4bc5-861f-78c86c525cc8 |

### Supplementary Rules (from Leg1 Comprehension, validated as still applicable)

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-FRONTEND-012 | No search, filter, sort toggle, or pagination in UI — flat list renders all notes. Exact replication of legacy. | CONSTRAINT | index.php:101-115 | HIGH | None | ab9d2cb5-48ce-40bf-86c3-4a30a911393b |
| BR-FRONTEND-013 | Delete uses HTTP DELETE method, not legacy GET ?delete=N — REST semantics upgrade. | TRANSFORMATION | index.php:109-111 | MEDIUM | Confirm backend DELETE /notes/{id} endpoint exists | 503b7c48-7a37-494a-ab86-d36b3bb186da |
| BR-FRONTEND-014 | Loading state: disable submit button during async API calls to prevent double-submit. Set loading=true before fetch, false in finally. | CONSTRAINT | index.php (new: sync-to-async migration requirement) | LOW | Spinner vs button-disable-only? | 4dd052d3-377d-4f9d-98ec-4d0c6f275021 |

---

## 2. Implementation Notes for CodeGen Agent

### RISK-FE-001: DATE-INTERPOLATION — Date format parity (HIGH)
**What to do:** Use `Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })` to format dates. Pin locale to `en-GB` explicitly — do NOT rely on browser default locale.
**Pattern to use:**
```typescript
const formatDate = (isoDate: string): string =>
  new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric'
  }).format(new Date(isoDate));
// "20 May 2026"
```
**Do NOT:** Use `toLocaleDateString()` without explicit locale. Do NOT use US locale — it produces "May 20, 2026" instead of "20 May 2026".

### RISK-FE-002: DELETE-METHOD-CHANGE — GET to DELETE upgrade (MEDIUM)
**What to do:** Use `fetch(url, { method: 'DELETE' })` for note deletion. The legacy `GET ?delete=N` pattern is a PHP limitation, not intentional design.
**Pattern to use:**
```typescript
const deleteNote = async (id: number): Promise<void> => {
  const res = await fetch(`${API_BASE}/notes/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await res.text());
};
```
**Do NOT:** Use GET for delete operations. Do NOT embed delete IDs in query strings.

### RISK-FE-003: DIRECT-OUTPUT — SPA replaces full-page reload (MEDIUM)
**What to do:** After successful create or delete, refresh the notes list optimistically or re-fetch. On error, preserve form content (BR-FRONTEND-004) and show inline alert (BR-FRONTEND-006).
**Pattern to use:** Controlled form state with `useState`. Clear form only on success. Error state triggers `AlertBanner`.
**Do NOT:** Navigate away or reload the page on error. Do NOT clear the textarea before confirming API success.

### RISK-FE-004: UX-GAP — No live character counter (LOW)
**What to do:** Do NOT add a live character counter. The legacy app only uses HTML `maxlength` to stop typing at 500. A character counter is an enhancement and is out of scope for this parity migration MWU.
**Do NOT:** Add `{content.length}/500` display or any character counting UI.

### RISK-FE-005: CONFIRM-DIALOG — window.confirm may be blocked (LOW)
**What to do:** Use `window.confirm('Delete this note?')` for parity with legacy. This is acceptable for this simple application.
**Do NOT:** Build a custom modal component for this MWU — document as known limitation if `window.confirm` is blocked in embedded contexts.

### RISK-FE-006: API-ERROR-CONTRACT — Parse FastAPI 422 errors (MEDIUM)
**What to do:** Map FastAPI `HTTPException.detail` string directly to the `AlertBanner` error message. The backend returns user-facing error strings in `detail`.
**Pattern to use:**
```typescript
try {
  const res = await fetch(`${API_BASE}/notes`, { method: 'POST', ... });
  if (!res.ok) {
    const body = await res.json();
    setError(body.detail || 'An error occurred');
    return;
  }
  setSuccess('Note added.');
} catch {
  setError('Network error. Please try again.');
}
```
**Do NOT:** Parse `detail` as an array (FastAPI validation errors use array format, but our backend raises `HTTPException` with string `detail`). Test both empty-content and over-length validation paths.

### RISK-FE-007: ANY_AUTH_PATTERN — Prevent auth scaffolding (HIGH)
**What to do:** When generating the React app, actively verify that NO auth-related code exists: no `AuthContext`, no `PrivateRoute`, no `useAuth` hook, no `Authorization` headers, no login/logout components, no JWT/session/cookie handling.
**Pattern to use:** All components render unconditionally. All fetch calls omit auth headers. No auth imports.
**Do NOT:** Use React boilerplate templates that scaffold auth by default. If using a template, strip auth before committing.

### RISK-FE-008: BRAND-COPY — Remove "Legacy v1.0" tag (LOW)
**What to do:** Omit the `<span class="legacy-tag">Legacy v1.0</span>` element entirely from the Navbar component.
**Do NOT:** Replace it with "Modern v2.0" or any version tag unless product owner specifies one.

---

## 3. Ambiguities Requiring SME Resolution

| ID | Question | Discovery Source | Impact if Wrong |
|----|----------|-----------------|-----------------|
| BR-FRONTEND-003 | Is the day zero-padded ("01 May") or not ("1 May")? PHP `date('d')` zero-pads, but was this intentional? | index.php:108 | Visual inconsistency with legacy output for single-digit days |
| BR-FRONTEND-002 | Is `window.confirm()` acceptable or must a custom React modal be used? | index.php:111 | UX difference: native confirm is synchronous, modal is async |
| BR-FRONTEND-011 | What should the footer copy be? Remove "Legacy PHP Application"? Replace with what? | index.php:118 | Minor brand inconsistency |
| BR-FRONTEND-010 | Confirm removal of "Legacy v1.0" navbar tag is acceptable | index.php:79-80 | Minor brand inconsistency |
| BR-FRONTEND-014 | Is button-disable sufficient for loading state, or is a visible spinner required? | New requirement (async migration) | UX gap if loading takes longer than expected |

---

## 4. Cross-Module Dependencies

| BR ID | Depends On | Module | Status |
|-------|-----------|--------|--------|
| BR-FRONTEND-001 | BR-BACKEND-002 (Note Length Limit 500) | backend | EXTRACTED |
| BR-FRONTEND-004 | BR-BACKEND-001 (Empty Note Guard), BR-BACKEND-002 | backend | EXTRACTED |
| BR-FRONTEND-006 | Backend 422 error detail format | backend | EXTRACTED |
| BR-FRONTEND-007 | BR-BACKEND-006 (No Authentication on API) | backend | EXTRACTED |
| BR-FRONTEND-009 | BR-BACKEND-007 (Newest First Order) | backend | EXTRACTED |
| BR-FRONTEND-012 | BR-BACKEND-008 (No Pagination on API) | backend | EXTRACTED |
| BR-FRONTEND-013 | Backend DELETE /notes/{id} endpoint | backend | EXTRACTED |
| ALL | FastAPI CORS middleware configured for React dev origin | backend | NOT VERIFIED |

**CORS Note:** Legacy PHP is server-rendered (no cross-origin). React SPA (e.g., localhost:3000) calling FastAPI (e.g., localhost:8000) requires `CORSMiddleware`. This is a backend configuration concern but blocks frontend development if missing.

---

## 5. MKB Storage Summary

**Total rules in catalog:** 14
**Newly stored (this session):** 5 (UUIDs: 02234b46, b609d7fe, b240d0bc, ea0a0633, 1e955235)
**Existing from Leg1:** 9 (UUIDs: e187fa65, 209b7e16, 9dab357f, 328b2a6f, 016592ea, 4e336242, ab9d2cb5, 503b7c48, 4dd052d3)
**Superseded Leg1 BRs:** 2 (a88047d9 subsumed by BR-FRONTEND-006; 8df35fbb subsumed by BR-FRONTEND-010)
**MKB module:** frontend
**Status:** EXTRACTED (pending HITL validation)

To retrieve for CodeGen:
```
mkb_get_business_rules(module="frontend", status="VALIDATED")
```

**Pipeline lesson applied:** Verified MKB store tool is available before writing (lesson sim 0.37 — comprehension must have mkb_store_artifact access to avoid PENDING_MKB_WRITE failures).

---

## 6. Reviewer Checklist

- [x] All 11 BRs from discovery Section 7 are captured (BR-FRONTEND-001 through 011)
- [x] 3 supplementary BRs from Leg1 added (012-014: no search/filter, HTTP DELETE upgrade, loading state)
- [x] Each BR has a clear, implementation-ready description with React code patterns
- [x] All 8 risk register items translated to CodeGen instructions in Section 2
- [x] 5 ambiguities flagged for SME resolution (not silently assumed)
- [x] MKB UUIDs recorded for all 14 rules — full traceability
- [x] Cross-module dependencies identified (8 backend dependencies + CORS gap)
- [x] No authentication patterns added (BR-FRONTEND-007 / RISK-FE-007 verified)
- [x] PHP-to-React type mappings provided for date format, error handling, XSS prevention
- [x] Leg1 superseded BRs noted (2 subsumed into richer Leg2 equivalents)

---

*Comprehension Agent — MWU-NL2-002-FE — 2026-05-20*
