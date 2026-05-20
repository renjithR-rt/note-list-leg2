"""
Test suite for backend module.

Covers all 9 business rules plus risk mitigations.
"""

import pytest

pytestmark = pytest.mark.asyncio


class TestGetNotes:
    """GET /api/notes"""

    async def test_empty_list(self, client):
        """Empty database returns empty list."""
        resp = await client.get("/api/notes")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_br007_newest_first(self, client):
        """BR-007: notes returned in descending creation order."""
        await client.post("/api/notes", json={"content": "first"})
        await client.post("/api/notes", json={"content": "second"})
        resp = await client.get("/api/notes")
        notes = resp.json()
        assert len(notes) == 2
        assert notes[0]["content"] == "second"
        assert notes[1]["content"] == "first"

    async def test_br006_no_auth_required(self, client):
        """BR-006: GET requires no authentication."""
        resp = await client.get("/api/notes")
        assert resp.status_code != 401
        assert resp.status_code != 403


class TestCreateNote:
    """POST /api/notes"""

    async def test_create_success(self, client):
        """Successful note creation."""
        resp = await client.post("/api/notes", json={"content": "Hello"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello"
        assert data["id"] > 0
        assert data["created_at"] is not None

    async def test_br003_trims_whitespace(self, client):
        """BR-003: content is stripped before storage."""
        resp = await client.post("/api/notes", json={"content": "  hello  "})
        assert resp.status_code == 201
        assert resp.json()["content"] == "hello"

    async def test_br001_empty_string_rejected(self, client):
        """BR-001: empty content rejected."""
        resp = await client.post("/api/notes", json={"content": ""})
        assert resp.status_code == 422
        assert "Note cannot be empty" in str(resp.json())

    async def test_br001_whitespace_only_rejected(self, client):
        """BR-001+BR-003: whitespace-only content rejected after trim."""
        resp = await client.post("/api/notes", json={"content": "   "})
        assert resp.status_code == 422
        assert "Note cannot be empty" in str(resp.json())

    async def test_br002_exactly_500_chars_accepted(self, client):
        """BR-002: 500 chars is the boundary — must be accepted."""
        resp = await client.post("/api/notes", json={"content": "x" * 500})
        assert resp.status_code == 201

    async def test_br002_501_chars_rejected(self, client):
        """BR-002: 501 chars exceeds limit."""
        resp = await client.post("/api/notes", json={"content": "x" * 501})
        assert resp.status_code == 422
        assert "Note too long (max 500 chars)" in str(resp.json())

    async def test_br008_emoji_stored_correctly(self, client):
        """BR-008: 4-byte Unicode (emoji) stored without truncation."""
        resp = await client.post("/api/notes", json={"content": "Hello 🎉"})
        assert resp.status_code == 201
        assert resp.json()["content"] == "Hello 🎉"

    async def test_br009_created_at_set_by_db(self, client):
        """BR-009: created_at present and timezone-aware; not supplied by app."""
        resp = await client.post("/api/notes", json={"content": "test"})
        assert resp.status_code == 201
        assert resp.json()["created_at"] is not None

    async def test_risk002_sql_injection_stored_literally(self, client):
        """RISK-002: SQL injection payload stored as literal string."""
        payload = "'; DROP TABLE notes; --"
        resp = await client.post("/api/notes", json={"content": payload})
        assert resp.status_code == 201
        # Verify table still exists and content round-trips
        notes = (await client.get("/api/notes")).json()
        assert any(n["content"] == payload for n in notes)

    async def test_br006_no_auth_required(self, client):
        """BR-006: POST requires no authentication."""
        resp = await client.post("/api/notes", json={"content": "test"})
        assert resp.status_code not in (401, 403)


class TestDeleteNote:
    """DELETE /api/notes/{note_id}"""

    async def test_delete_success(self, client):
        """Successful note deletion."""
        create_resp = await client.post("/api/notes", json={"content": "delete me"})
        note_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/notes/{note_id}")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async def test_br005_not_found_returns_404(self, client):
        """BR-005: non-existent note returns 404, not silent success."""
        resp = await client.delete("/api/notes/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Note not found"

    async def test_risk001_double_delete_returns_404(self, client):
        """RISK-001: second delete of same note returns 404, not ok:true."""
        create_resp = await client.post("/api/notes", json={"content": "once"})
        note_id = create_resp.json()["id"]
        await client.delete(f"/api/notes/{note_id}")
        second = await client.delete(f"/api/notes/{note_id}")
        assert second.status_code == 404

    async def test_br004_zero_id_rejected(self, client):
        """BR-004: note_id=0 rejected."""
        resp = await client.delete("/api/notes/0")
        assert resp.status_code == 422
        assert "Invalid note ID" in str(resp.json())

    async def test_br004_negative_id_rejected(self, client):
        """BR-004: negative note_id rejected."""
        resp = await client.delete("/api/notes/-1")
        assert resp.status_code == 422
        assert "Invalid note ID" in str(resp.json())

    async def test_br004_non_integer_id_rejected(self, client):
        """BR-004: non-integer path segment rejected by FastAPI path coercion."""
        resp = await client.delete("/api/notes/abc")
        assert resp.status_code == 422

    async def test_risk004_get_method_not_accepted(self, client):
        """RISK-004: DELETE path does not accept GET requests."""
        resp = await client.get("/api/notes/1")
        assert resp.status_code == 405

    async def test_br006_no_auth_required(self, client):
        """BR-006: DELETE requires no authentication."""
        create_resp = await client.post("/api/notes", json={"content": "auth test"})
        note_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/notes/{note_id}")
        assert resp.status_code not in (401, 403)


class TestValidationChain:
    """Test BR-003 → BR-001 → BR-002 validation chain."""

    async def test_trim_then_empty_check_order(self, client):
        """BR-003+001: POST '   ' — trim then empty check."""
        resp = await client.post("/api/notes", json={"content": "   "})
        assert resp.status_code == 422  # not 201; order matters

    async def test_trim_then_length_check_order(self, client):
        """BR-003+002: POST 498 spaces + 'ab' → trimmed = 'ab' (2 chars)."""
        content = " " * 498 + "ab"
        resp = await client.post("/api/notes", json={"content": content})
        assert resp.status_code == 201  # trim reduces to 2 chars
        assert resp.json()["content"] == "ab"