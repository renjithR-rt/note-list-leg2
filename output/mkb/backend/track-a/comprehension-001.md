# Comprehension Report — MWU-NL2-001 Backend Module
**Phase:** Comprehension — Track A (LLM Direct)
**Date:** 2026-05-20
**Analyst model:** claude-opus-4-6
**Source:** discovery-001.md (3 source files, complexity LOW)
**Rules extracted:** 9 business rules
**MKB artifacts stored:** 9 UUIDs

---

## 1. Business Rule Catalog

| ID | Description | Type | Source | Priority | Ambiguity | MKB UUID |
|----|-------------|------|--------|----------|-----------|----------|
| BR-BACKEND-001 | Note content must not be empty after whitespace trimming; reject with "Note cannot be empty" | VALIDATION | index.php:24-26 (add_note) | HIGH | None | 5dc47a89-e526-4e8a-8cff-da007e8414f3 |
| BR-BACKEND-002 | Note content limited to 500 characters; reject with "Note too long (max 500 chars)"; enforced at app + DB layer | VALIDATION | index.php:27-29 (add_note), schema.sql:6 | HIGH | None | ed30de4a-afb7-46db-9c4d-9fe57d89eb16 |
| BR-BACKEND-003 | Content whitespace trimmed BEFORE empty check and length check; trimmed value is what gets stored | TRANSFORMATION | index.php:23 (add_note) | MEDIUM | None | bdf7e274-1908-4c6e-837e-44b5d5ef6c0b |
| BR-BACKEND-004 | Delete rejects non-positive integer IDs with "Invalid note ID"; cast-to-int then check > 0 | VALIDATION | index.php:37-40 (delete_note) | HIGH | None | 7c57efb3-3598-4f35-a48f-9172c2b8c0d7 |
| BR-BACKEND-005 | Delete on valid but non-existent note ID must return 404 (GAP: legacy returns ok:true silently) | CONSTRAINT | index.php:35-43 (delete_note) | HIGH | **GAP REMEDIATION** — behaviour absent in legacy; required by stated business requirements | 4a307adb-489c-4995-9cfb-ae78aa51cefc |
| BR-BACKEND-006 | All endpoints are public — NO authentication, authorization, sessions, or API keys | AUTHORIZATION | index.php (global) | CRITICAL | None — HARD CONSTRAINT: adding any auth violates source design | aaa8ab29-3087-4a03-abdb-762df15d52ce |
| BR-BACKEND-007 | Notes always returned in descending creation order (newest first); no user-configurable sort | CONSTRAINT | index.php:11 (get_notes) | MEDIUM | None | e9e59b8a-f2f5-4951-95d6-0927ea85519d |
| BR-BACKEND-008 | Content stored as UTF-8; PostgreSQL 4-byte UTF-8 upgrades MySQL 3-byte utf8 (emoji now supported) | CONSTRAINT | db.php:10, schema.sql:1 | LOW | None | 6dd458b9-3ff5-4be9-a05d-04e6755aac46 |
| BR-BACKEND-009 | created_at set by DB via DEFAULT CURRENT_TIMESTAMP; app layer never supplies this value | CONSTRAINT | schema.sql:7 | LOW | None | 2af1953d-1ba6-4d63-b060-37111f3fe0d4 |

### Validation Chain (BR-003 → BR-001 → BR-002)

The three validation BRs execute in strict order during note creation:
1. **BR-003** — `strip()` whitespace from content
2. **BR-001** — Reject if stripped content is empty
3. **BR-002** — Reject if stripped content exceeds 500 chars

This order MUST be preserved in the Pydantic validator. Reversing BR-001 and BR-003 would allow whitespace-only notes through.

---

## 2. Implementation Notes for CodeGen Agent

### RISK-001: HIGH — Delete Silent No-Op on Missing Note
**What to do:** After executing `DELETE FROM notes WHERE id = :note_id`, check `result.rowcount`. If `rowcount == 0`, raise `HTTPException(status_code=404, detail="Note not found")`.
**Pattern to use:**
```python
result = await db.execute(delete(Note).where(Note.id == note_id))
await db.commit()
if result.rowcount == 0:
    raise HTTPException(status_code=404, detail="Note not found")
```
**Do NOT:** Return a success response when no rows were deleted (as PHP does).

### RISK-002: HIGH — SQL Injection via String Interpolation
**What to do:** Use SQLAlchemy ORM methods or parameterized `select()`/`insert()`/`delete()` for all queries. Never concatenate user input into SQL strings.
**Pattern to use:** `session.execute(insert(Note).values(content=content))` or equivalent ORM pattern.
**Do NOT:** Use `text()` with f-strings or string formatting. No `f"SELECT ... WHERE id = {id}"`.

### RISK-003: MEDIUM — Deprecated mysql_* API
**What to do:** Already resolved by migration to SQLAlchemy 2.x async. No action needed beyond using the standard async session pattern.

### RISK-004: MEDIUM — DELETE via HTTP GET
**What to do:** Use `@router.delete("/api/notes/{note_id}")` — proper HTTP DELETE method.
**Do NOT:** Accept GET requests for delete operations. No query parameter deletion (`?delete=id`).

### RISK-005: MEDIUM — No PRG Pattern (Duplicate on Refresh)
**What to do:** REST API + SPA frontend eliminates this. POST /api/notes returns JSON (201); frontend handles redirect/state update.
**Do NOT:** Implement server-side redirects or PRG pattern — the SPA architecture makes it unnecessary.

### RISK-006: MEDIUM — DATETIME to TIMESTAMP WITH TIME ZONE
**What to do:** Use `DateTime(timezone=True)` in SQLAlchemy model with `server_default=func.now()`. All timestamps are timezone-aware in PostgreSQL.
**Pattern to use:** `mapped_column(DateTime(timezone=True), server_default=func.now())`
**Assumption:** Legacy data without timezone info is treated as UTC. Document this assumption in migration scripts.

### RISK-007: LOW — MySQL utf8 3-byte Limitation
**What to do:** No action needed. PostgreSQL UTF-8 is 4-byte natively. Emoji and supplementary Unicode characters now work automatically.

### RISK-008: LOW — Hardcoded DB Credential Fallbacks
**What to do:** Require `DATABASE_URL` environment variable. Fail hard with clear error if missing.
**Do NOT:** Add hardcoded fallback credentials like `noteuser`/`notepass`. No default connection strings.
**Pattern to use:**
```python
DATABASE_URL = os.environ["DATABASE_URL"]  # KeyError if missing = fail-fast
```

---

## 3. Ambiguities Requiring SME Resolution

| ID | Question | Discovery Source | Impact if Wrong |
|----|----------|-----------------|-----------------|
| BR-BACKEND-005 | Should delete of non-existent note return 404 or 204? Discovery recommends 404 (gap remediation), but legacy silently succeeds. | index.php:35-43, RISK-001 | If 404: frontend must handle error state for stale delete buttons. If 204: simpler but hides bugs where frontend references deleted notes. |

All other rules are unambiguous from source code inspection. BR-BACKEND-005 is flagged as MEDIUM confidence because the 404 behaviour is NEW — not observed in legacy, only recommended by discovery analysis.

---

## 4. Cross-Module Dependencies

| BR ID | Depends on | Module | Status |
|-------|-----------|--------|--------|
| — | — | — | — |

No cross-module dependencies. The backend module is entirely self-contained. MWU-NL2-002-FE (frontend) **consumes** this module's 3 REST endpoints but the backend has no upstream dependencies.

**Downstream consumers:**
- MWU-NL2-002-FE depends on: `GET /api/notes`, `POST /api/notes`, `DELETE /api/notes/{id}`

---

## 5. MKB Storage Summary

Total rules stored: 9
MKB project: NOTE-LIST-LEG2
MKB module: backend
MKB namespace: business-rules
Status: EXTRACTED (pending HITL validation)

| Rule ID | MKB UUID |
|---------|----------|
| BR-BACKEND-001 | 5dc47a89-e526-4e8a-8cff-da007e8414f3 |
| BR-BACKEND-002 | ed30de4a-afb7-46db-9c4d-9fe57d89eb16 |
| BR-BACKEND-003 | bdf7e274-1908-4c6e-837e-44b5d5ef6c0b |
| BR-BACKEND-004 | 7c57efb3-3598-4f35-a48f-9172c2b8c0d7 |
| BR-BACKEND-005 | 4a307adb-489c-4995-9cfb-ae78aa51cefc |
| BR-BACKEND-006 | aaa8ab29-3087-4a03-abdb-762df15d52ce |
| BR-BACKEND-007 | e9e59b8a-f2f5-4951-95d6-0927ea85519d |
| BR-BACKEND-008 | 6dd458b9-3ff5-4be9-a05d-04e6755aac46 |
| BR-BACKEND-009 | 2af1953d-1ba6-4d63-b060-37111f3fe0d4 |

To retrieve for CodeGen:
```
mkb_get_business_rules(module="backend", status="VALIDATED", project_id="NOTE-LIST-LEG2")
```

---

## 6. Reviewer Checklist

- [ ] All 9 BRs from discovery Section 7 are captured (001–009)
- [ ] Each BR has a clear, implementation-ready description with Pydantic/SQLAlchemy patterns
- [ ] All 8 risk register items (RISK-001 through RISK-008) are translated to CodeGen instructions in Section 2
- [ ] BR-BACKEND-005 flagged as MEDIUM confidence (gap remediation, not observed in legacy)
- [ ] BR-BACKEND-006 flagged as CRITICAL hard constraint (no auth)
- [ ] All 9 MKB UUIDs recorded in Section 5 for traceability
- [ ] Validation chain order documented (BR-003 → BR-001 → BR-002)
- [ ] Cross-module dependency: none upstream; downstream consumer MWU-NL2-002-FE identified
- [ ] Pipeline lesson applied: verified all 9 BRs actually stored to MKB (no PENDING_MKB_WRITE)

---

## 7. Pipeline Lessons Applied

| Lesson | Similarity | Action Taken |
|--------|-----------|--------------|
| Comprehension agent must have --allowedTools active to store BRs | 0.37 | Verified: all 9 mkb_store_artifact calls returned valid UUIDs — no PENDING_MKB_WRITE entries |
