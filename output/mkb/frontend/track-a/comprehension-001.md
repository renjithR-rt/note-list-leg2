# Comprehension Report — MWU-NL2-002-FE Frontend
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** 2026-05-20
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md (3 source files, complexity LOW)
**Rules extracted:** 15 business rules (11 from discovery Section 7 + 4 from Sections 3–5/8)
**MKB artifacts stored:** 15 UUIDs

---

## 1. Business Rule Catalog

### Discovery Section 7 — Primary Business Rules

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-FRONTEND-001 | Client-side textarea enforces `maxlength="500"` to prevent oversized content at browser level. UX aid only — server validation (BR-BACKEND-002) is authoritative. | VALIDATION | index.php:94 | MEDIUM | None | `44cadd44-1b72-48d1-9054-66e9174452c2` |
| BR-FRONTEND-002 | User must confirm deletion via `window.confirm('Delete this note?')` before any DELETE request is sent. Cancelling prevents the call entirely. | CONSTRAINT | index.php:111 | HIGH | Custom modal vs window.confirm — window.confirm acceptable for parity | `b11ab379-d8b7-4cd1-b1bf-f59cab3fd0f0` |
| BR-FRONTEND-003 | Dates displayed as "dd MMM yyyy" (e.g., "20 May 2026"). PHP `date('d M Y')` zero-pads day. Locale must be `en-GB` for correct month names. | TRANSFORMATION | index.php:108 | MEDIUM | Leading zero ("01 May" vs "1 May") — PHP `'d'` zero-pads, confirm intent | `6e1b5fb0-380b-4408-95a7-11b76c267914` |
| BR-FRONTEND-004 | On validation error, textarea retains user content. Content cleared ONLY on successful creation. | CONSTRAINT | index.php:96 | MEDIUM | None | `98180000-a973-4fba-9e56-3206b6fe3573` |
| BR-FRONTEND-005 | When no notes exist, display "No notes yet. Add one above." — exact copy from legacy. | CONSTRAINT | index.php:102 | LOW | None | `00f420bd-4dbe-42e2-9a2b-696054238191` |
| BR-FRONTEND-006 | Inline alert banners (error=red, success=green) above the form. Mutually exclusive — never show both. Success copy: "Note added." Error copies from backend. | CONSTRAINT | index.php:84–89 | HIGH | None | `f0c5a398-51fb-4722-9e6e-763b680c0640` |
| BR-FRONTEND-007 | **CRITICAL** — No authentication UI whatsoever. No login, logout, session indicator, protected routes, auth context, or Authorization headers. All views unconditionally public. | AUTHORIZATION | index.php:1–121 | CRITICAL | None | `653469fe-bbec-4f44-8c3d-27c5ad6803c6` |
| BR-FRONTEND-008 | XSS prevention via JSX auto-escaping. NEVER use `dangerouslySetInnerHTML` for user-supplied content. Security-critical — no exceptions. | VALIDATION | index.php:85,88,96,107 | HIGH | None | `93ea4684-47d5-41b8-ab52-704aa440705a` |
| BR-FRONTEND-009 | Notes rendered in API-returned order (newest first). No client-side sorting. No sort toggle. | CONSTRAINT | index.php:11,104–113 | MEDIUM | None | `08d89b59-4124-4fa8-b6d1-dfe4fb1bf754` |
| BR-FRONTEND-010 | Page title "Note List". Navbar brand "📝 Note List". "Legacy v1.0" tag intentionally removed. | TRANSFORMATION | index.php:74,79–80 | LOW | Confirm "Legacy v1.0" removal | `b95ed4d0-8a1d-46ce-859b-fb9c661b4a93` |
| BR-FRONTEND-011 | Footer with copyright line. Legacy: "Note List © 2026 — Legacy PHP Application". Replace qualifier in migrated app. | TRANSFORMATION | index.php:118 | LOW | Exact footer copy TBD | `11a73515-72f3-44ab-bce2-535b103eb793` |

### Additional Rules — Extracted from Discovery Sections 3–5 and Risk Register

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-FRONTEND-012 | No search, filter, sort toggle, or pagination. Flat list of all notes. Exact replication of legacy. | CONSTRAINT | index.php:101–115; Section 5 | HIGH | None | `29e6c0e3-0695-42a0-bcc7-e8170f465658` |
| BR-FRONTEND-013 | Delete uses HTTP DELETE method, not GET. Legacy `?delete={id}` was a PHP limitation. Protocol upgrade, not behaviour change. | TRANSFORMATION | index.php:109–111; RISK-FE-002 | MEDIUM | None | `c3182f5a-8788-4977-8748-fb98f23d59bc` |
| BR-FRONTEND-014 | Async API calls must prevent double-submit. Disable submit button during fetch. New migration requirement — no legacy equivalent. | CONSTRAINT | Migration-required; RISK-FE-003 | MEDIUM | Spinner vs button-disable-only TBD | `cc5235ee-8f86-4b92-b33b-791e69d408c9` |
| BR-FRONTEND-015 | Parse FastAPI 422/404 error responses to extract user-facing messages. Map `HTTPException.detail` → AlertBanner message. Handle Pydantic validation errors gracefully. | TRANSFORMATION | RISK-FE-006; Section 4 | HIGH | None | `3f1b6b9a-003f-455d-9777-4c89f36ef998` |

---

## 2. Implementation Notes for CodeGen Agent

### RISK-FE-001: DATE-INTERPOLATION — Date Format Locale Mismatch (HIGH)
**What to do:** Pin `Intl.DateTimeFormat` locale to `'en-GB'` with options `{ day: '2-digit', month: 'short', year: 'numeric' }`. Add a regression test that formats `new Date('2026-01-05T00:00:00Z')` and asserts the output is `"05 Jan 2026"`.
**Pattern to use:**
```typescript
const formatDate = (iso: string): string =>
  new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric'
  }).format(new Date(iso));
```
**Do NOT:** Use `toLocaleDateString()` without explicit locale — it defaults to user's system locale, producing inconsistent output.

### RISK-FE-002: DELETE-METHOD-CHANGE — GET→DELETE Protocol Upgrade (MEDIUM)
**What to do:** All delete operations must use `fetch(url, { method: 'DELETE' })`. Never use GET for state-mutating operations.
**Pattern to use:**
```typescript
const deleteNote = async (id: number): Promise<void> => {
  const res = await fetch(`${BASE_URL}/notes/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await extractErrorMessage(res));
};
```
**Do NOT:** Use `<a href="?delete={id}">` or any GET-based delete pattern from the legacy app.

### RISK-FE-003: DIRECT-OUTPUT — SPA Replaces Full-Page Reload (MEDIUM)
**What to do:** After create or delete, update the notes list without full page reload. Use optimistic UI update or refetch after mutation. Preserve form content on error (BR-FRONTEND-004).
**Pattern to use:** After successful POST, refetch notes list via `GET /notes` and clear form. After successful DELETE, refetch notes list. On error, show AlertBanner and preserve state.
**Do NOT:** Navigate away from the page or force a reload on error. The user must be able to correct and retry.

### RISK-FE-004: UX-GAP — No Character Counter (LOW)
**What to do:** Do NOT add a live character counter. The legacy app only uses HTML `maxlength`. This is a parity migration — out of scope.
**Do NOT:** Add countdown text, progress bars, or any visible character-counting UI. Mark as enhancement candidate only.

### RISK-FE-005: CONFIRM-DIALOG — window.confirm Limitations (LOW)
**What to do:** Use `window.confirm('Delete this note?')` for delete confirmation. Accept this is synchronous and may be blocked in embedded browsers — known limitation for this simple app.
**Do NOT:** Build a complex custom modal for this simple confirmation unless explicitly requested.

### RISK-FE-006: API-ERROR-CONTRACT — FastAPI Error Parsing (MEDIUM)
**What to do:** Extract error messages from FastAPI responses. For `HTTPException` (400/404/422): read `response.json().detail` as a string. For Pydantic 422 errors: the `detail` field is an array — extract `detail[0].msg` or use fallback.
**Pattern to use:**
```typescript
const extractErrorMessage = async (res: Response): Promise<string> => {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) return body.detail[0]?.msg ?? 'Validation error';
    return 'An error occurred';
  } catch {
    return 'An error occurred';
  }
};
```
**Do NOT:** Display raw JSON error objects to the user. Always extract a human-readable string.

### RISK-FE-007: ANY_AUTH_PATTERN — Prevent Auth Scaffolding (HIGH)
**What to do:** If using a React template or boilerplate, strip ALL auth-related code before committing. No `AuthProvider`, no `ProtectedRoute`, no `useAuth` hook, no `Authorization` header, no login/logout UI.
**Pattern to use:** Every component renders unconditionally. No auth guards. No token storage.
**Do NOT:** Use `create-react-app` or Vite templates that include auth scaffolding without stripping it completely.

### RISK-FE-008: BRAND-COPY — Remove Legacy Tag (LOW)
**What to do:** Remove "Legacy v1.0" tag from navbar. Keep "📝 Note List" brand text.
**Do NOT:** Carry over any "Legacy" branding into the React app.

---

## 3. Ambiguities Requiring SME Resolution

| ID | Question | Discovery Source | Impact if Wrong |
|----|----------|-----------------|-----------------|
| BR-FRONTEND-003 | Is the leading zero on day intentional? PHP `'d'` produces "01 May" but `'j'` would produce "1 May". Which is the business expectation? | index.php:108 — `date('d M Y')` | Visual inconsistency; users may notice single-digit dates displayed differently |
| BR-FRONTEND-011 | What should the footer copyright line say in the React app? Keep "Legacy PHP Application", change to "Modern React Application", or remove the qualifier? | index.php:118 | Minor branding inconsistency |
| BR-FRONTEND-014 | Is a visible loading spinner/indicator required during async operations, or is button-disable-only sufficient? | Migration requirement (no legacy equivalent) | UX difference — disabled button with no indicator may confuse users |
| BR-FRONTEND-010 | Confirm removal of "Legacy v1.0" navbar tag — should any version indicator replace it? | index.php:80 | Minor branding decision |

---

## 4. Cross-Module Dependencies

| BR ID | Depends on | Module | Status |
|-------|-----------|--------|--------|
| BR-FRONTEND-001 | BR-BACKEND-002 (Note Length Limit 500) | backend | EXTRACTED |
| BR-FRONTEND-004 | BR-BACKEND-001 (Empty Note Guard), BR-BACKEND-002 | backend | EXTRACTED |
| BR-FRONTEND-006 | BR-BACKEND-001, BR-BACKEND-002, BR-BACKEND-005 (error messages) | backend | EXTRACTED |
| BR-FRONTEND-007 | BR-BACKEND-006 (No Authentication on API) | backend | EXTRACTED |
| BR-FRONTEND-009 | BR-BACKEND-007 (Newest First Order) | backend | EXTRACTED |
| BR-FRONTEND-012 | BR-BACKEND-007 (returns all notes, no pagination) | backend | EXTRACTED |
| BR-FRONTEND-013 | Backend DELETE /notes/{id} endpoint implementation | backend | EXTRACTED |
| BR-FRONTEND-015 | FastAPI HTTPException / Pydantic error response format | backend | EXTRACTED |

**CORS dependency (not a BR, infrastructure):** React SPA will call FastAPI from a different origin (e.g., `localhost:3000` → `localhost:8000`). FastAPI must be configured with `CORSMiddleware` allowing the React dev origin. This is a backend concern flagged by discovery.

---

## 5. MKB Storage Summary

**Total rules stored:** 15
**MKB module:** frontend
**MKB project_id:** NOTE-LIST-LEG2
**Status:** EXTRACTED (pending HITL validation)

| BR ID | MKB UUID | Confidence |
|-------|----------|------------|
| BR-FRONTEND-001 | `44cadd44-1b72-48d1-9054-66e9174452c2` | HIGH |
| BR-FRONTEND-002 | `b11ab379-d8b7-4cd1-b1bf-f59cab3fd0f0` | HIGH |
| BR-FRONTEND-003 | `6e1b5fb0-380b-4408-95a7-11b76c267914` | MEDIUM |
| BR-FRONTEND-004 | `98180000-a973-4fba-9e56-3206b6fe3573` | HIGH |
| BR-FRONTEND-005 | `00f420bd-4dbe-42e2-9a2b-696054238191` | HIGH |
| BR-FRONTEND-006 | `f0c5a398-51fb-4722-9e6e-763b680c0640` | HIGH |
| BR-FRONTEND-007 | `653469fe-bbec-4f44-8c3d-27c5ad6803c6` | HIGH |
| BR-FRONTEND-008 | `93ea4684-47d5-41b8-ab52-704aa440705a` | HIGH |
| BR-FRONTEND-009 | `08d89b59-4124-4fa8-b6d1-dfe4fb1bf754` | HIGH |
| BR-FRONTEND-010 | `b95ed4d0-8a1d-46ce-859b-fb9c661b4a93` | HIGH |
| BR-FRONTEND-011 | `11a73515-72f3-44ab-bce2-535b103eb793` | MEDIUM |
| BR-FRONTEND-012 | `29e6c0e3-0695-42a0-bcc7-e8170f465658` | HIGH |
| BR-FRONTEND-013 | `c3182f5a-8788-4977-8748-fb98f23d59bc` | HIGH |
| BR-FRONTEND-014 | `cc5235ee-8f86-4b92-b33b-791e69d408c9` | MEDIUM |
| BR-FRONTEND-015 | `3f1b6b9a-003f-455d-9777-4c89f36ef998` | MEDIUM |

**Prior Leg1 MKB artifacts (11 rules, EXTRACTED):** These exist in MKB from a previous comprehension run with different numbering. The Leg2 UUIDs above supersede them for codegen purposes.

To retrieve for CodeGen:
```
mkb_get_business_rules(module="frontend", status="VALIDATED")
```

---

## 6. Reviewer Checklist

- [x] All 11 BRs from discovery Section 7 are captured (BR-FRONTEND-001 through 011)
- [x] 4 additional BRs extracted from Sections 3–5 and risk register (BR-FRONTEND-012 through 015)
- [x] Each BR has a clear, implementation-ready description with React code patterns
- [x] All 8 risk register items translated to CodeGen instructions (Section 2)
- [x] 4 ambiguities flagged for SME resolution (Section 3)
- [x] All 15 MKB UUIDs recorded for traceability (Section 5)
- [x] 8 cross-module dependencies identified (Section 4)
- [x] CORS infrastructure gap flagged
- [x] No authentication patterns — CRITICAL constraint documented (BR-FRONTEND-007)
- [x] Date format locale pinned to en-GB with regression test instruction

---

## Appendix: Backend BRs Consumed (Not Re-Extracted)

These backend rules are referenced by frontend BRs but owned by MWU-NL2-001. They are NOT re-extracted here — query MKB for authoritative versions:

| Backend BR | Frontend Implication |
|------------|---------------------|
| BR-BACKEND-001: Empty Note Guard | Display "Note cannot be empty" from API 422 response |
| BR-BACKEND-002: Note Length Limit 500 | Mirror with `maxLength={500}` on textarea; display API error if bypassed |
| BR-BACKEND-003: Content Trimming | Transparent to frontend; API strips whitespace |
| BR-BACKEND-004: Invalid ID Guard | DELETE must use valid numeric IDs; NoteCard receives id:number from list |
| BR-BACKEND-005: Missing Note → 404 | Frontend must handle 404 on delete gracefully |
| BR-BACKEND-006: No Authentication | CRITICAL — React must add NO auth UI whatsoever |
| BR-BACKEND-007: Newest First Order | Frontend relies on API order; no client-side sort |
| BR-BACKEND-008: UTF-8 Storage | JS strings are UTF-16; display renders correctly |
| BR-BACKEND-009: created_at Auto-Set | NoteCreate form omits created_at; only NoteRead shows it |

---

*Comprehension Agent — MWU-NL2-002-FE — 2026-05-20*
