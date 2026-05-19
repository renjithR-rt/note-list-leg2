"""Tests for backend module business rules."""

import pytest
from httpx import AsyncClient

# ──────────────────────────────────────────────
# BR-BACKEND-006: content trimmed before storage
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_note_trims_whitespace(client: AsyncClient):
    """Content should be trimmed of leading/trailing whitespace."""
    resp = await client.post("/notes/", json={"content": "  hello world  "})
    assert resp.status_code == 201
    assert resp.json()["content"] == "hello world"  # trimmed

@pytest.mark.asyncio
async def test_create_note_trims_tabs_and_newlines(client: AsyncClient):
    """Should trim tabs, newlines, and mixed whitespace."""
    resp = await client.post("/notes/", json={"content": "\t\n  padded content  \n\t"})
    assert resp.status_code == 201
    assert resp.json()["content"] == "padded content"

# ──────────────────────────────────────────────
# BR-BACKEND-001: empty content rejected
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_note_rejects_empty_string(client: AsyncClient):
    """Empty string should be rejected with 422."""
    resp = await client.post("/notes/", json={"content": ""})
    assert resp.status_code == 422
    body = resp.json()
    assert any("empty" in str(e).lower() for e in body["detail"])

@pytest.mark.asyncio
async def test_create_note_rejects_whitespace_only(client: AsyncClient):
    """Whitespace-only content should be rejected after trim."""
    resp = await client.post("/notes/", json={"content": "   "})
    assert resp.status_code == 422
    body = resp.json()
    assert any("empty" in str(e).lower() for e in body["detail"])

@pytest.mark.asyncio
async def test_create_note_rejects_tab_only(client: AsyncClient):
    """Tab/newline-only content should be rejected after trim."""
    resp = await client.post("/notes/", json={"content": "\t\n\r"})
    assert resp.status_code == 422

# ──────────────────────────────────────────────
# BR-BACKEND-002: content max 500 characters
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_note_accepts_exactly_500_chars(client: AsyncClient):
    """Exactly 500 characters should be accepted."""
    resp = await client.post("/notes/", json={"content": "x" * 500})
    assert resp.status_code == 201
    assert len(resp.json()["content"]) == 500

@pytest.mark.asyncio
async def test_create_note_rejects_501_chars(client: AsyncClient):
    """501 characters should be rejected with 422."""
    resp = await client.post("/notes/", json={"content": "x" * 501})
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_create_note_trims_then_checks_length(client: AsyncClient):
    """Length check happens after trimming whitespace."""
    # 498 spaces + 2 chars = "ab" after trim (2 chars, valid)
    resp = await client.post("/notes/", json={"content": " " * 498 + "ab"})
    assert resp.status_code == 201
    assert resp.json()["content"] == "ab"

# ──────────────────────────────────────────────
# BR-BACKEND-003: note_id must be positive integer
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_rejects_zero_id(client: AsyncClient):
    """note_id = 0 should be rejected with 422."""
    resp = await client.delete("/notes/0")
    assert resp.status_code == 422  # Path(gt=0) validation

@pytest.mark.asyncio
async def test_delete_rejects_negative_id(client: AsyncClient):
    """Negative note_id should be rejected with 422."""
    resp = await client.delete("/notes/-1")
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_delete_rejects_non_integer_id(client: AsyncClient):
    """Non-integer note_id should be rejected with 422."""
    resp = await client.delete("/notes/abc")
    assert resp.status_code == 422

# ──────────────────────────────────────────────
# BR-BACKEND-004: notes ordered by created_at DESC
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_notes_ordered_newest_first(client: AsyncClient):
    """Notes should be returned in newest-first order."""
    # Create three notes in known order
    r1 = await client.post("/notes/", json={"content": "first note"})
    r2 = await client.post("/notes/", json={"content": "second note"})  
    r3 = await client.post("/notes/", json={"content": "third note"})
    assert all(r.status_code == 201 for r in [r1, r2, r3])
    
    resp = await client.get("/notes/")
    assert resp.status_code == 200
    notes = resp.json()
    contents = [n["content"] for n in notes]
    
    # newest first: "third note" must appear before "first note"
    assert contents.index("third note") < contents.index("first note")

# ──────────────────────────────────────────────
# BR-BACKEND-005: no auth — all endpoints public
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_notes_requires_no_auth(client: AsyncClient):
    """GET /notes/ should succeed without Authorization header."""
    resp = await client.get("/notes/")
    assert resp.status_code == 200  # not 401 or 403

@pytest.mark.asyncio
async def test_create_note_requires_no_auth(client: AsyncClient):
    """POST /notes/ should succeed without Authorization header."""
    resp = await client.post("/notes/", json={"content": "no auth test"})
    assert resp.status_code == 201  # not 401 or 403

@pytest.mark.asyncio
async def test_delete_note_requires_no_auth(client: AsyncClient):
    """DELETE /notes/{id} should succeed without Authorization header."""
    create_resp = await client.post("/notes/", json={"content": "to delete"})
    note_id = create_resp.json()["id"]
    resp = await client.delete(f"/notes/{note_id}")
    assert resp.status_code == 200  # not 401 or 403

# ──────────────────────────────────────────────
# BR-BACKEND-007: HITL GATE — delete missing note
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_nonexistent_note_returns_404(client: AsyncClient):
    """BR-BACKEND-007 HITL recommended path: 404 on missing note.
    
    If stakeholder chooses legacy silent-success, change expected to 200
    and update the assertion to check ok=True.
    """
    resp = await client.delete("/notes/999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

@pytest.mark.asyncio
async def test_delete_existing_note_succeeds(client: AsyncClient):
    """DELETE should succeed and return ok=True for existing note."""
    create_resp = await client.post("/notes/", json={"content": "delete me"})
    note_id = create_resp.json()["id"]
    
    delete_resp = await client.delete(f"/notes/{note_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["ok"] is True
    
    # Confirm note is gone
    list_resp = await client.get("/notes/")
    ids = [n["id"] for n in list_resp.json()]
    assert note_id not in ids

# ──────────────────────────────────────────────
# RISK-001: DELETE via GET never accepted
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_delete_query_param_not_accepted(client: AsyncClient):
    """Legacy PHP accepted GET /?delete=1 — must not be replicated."""
    create_resp = await client.post("/notes/", json={"content": "should survive"})
    note_id = create_resp.json()["id"]
    
    # GET with delete query param should NOT delete the note
    resp = await client.get(f"/notes/?delete={note_id}")
    # The note must survive the GET request
    list_resp = await client.get("/notes/")
    ids = [n["id"] for n in list_resp.json()]
    assert note_id in ids  # note survived the GET request

# ──────────────────────────────────────────────
# RISK-006: created_at returned as ISO 8601
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_created_at_is_iso8601(client: AsyncClient):
    """created_at should be valid ISO 8601 datetime string."""
    from datetime import datetime
    resp = await client.post("/notes/", json={"content": "timestamp test"})
    assert resp.status_code == 201
    created_at = resp.json()["created_at"]
    # Must parse as a valid ISO 8601 datetime without raising
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    assert dt.year >= 2026

# ──────────────────────────────────────────────
# Edge case: validation order
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validation_order_trim_then_empty_then_length(client: AsyncClient):
    """Validation order: trim first, then empty check, then length check."""
    # Test that a string of exactly 500 spaces becomes empty after trim
    # and gets rejected for emptiness (not length)
    resp = await client.post("/notes/", json={"content": " " * 500})
    assert resp.status_code == 422
    body = resp.json()
    # Should get "empty" error, not "too long" error
    error_msg = str(body["detail"]).lower()
    assert "empty" in error_msg
    assert "long" not in error_msg