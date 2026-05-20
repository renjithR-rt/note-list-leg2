from __future__ import annotations

import pytest


class TestNoteAPI:
    """Test suite covering all business rules for the notes API."""

    @pytest.mark.asyncio
    async def test_list_notes_empty(self, client):
        """BR-007: Empty table returns {"notes": []} with 200."""
        response = await client.get("/api/notes")
        assert response.status_code == 200
        assert response.json() == {"notes": []}

    @pytest.mark.asyncio
    async def test_create_note(self, client):
        """Happy path: create note and verify response structure."""
        r = await client.post("/api/notes", json={"content": "hello world"})
        assert r.status_code == 201
        data = r.json()
        assert data["content"] == "hello world"
        assert isinstance(data["id"], int)
        assert data["id"] > 0
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_list_notes_after_create(self, client):
        """BR-007: Notes returned in newest-first order."""
        await client.post("/api/notes", json={"content": "first"})
        await client.post("/api/notes", json={"content": "second"})
        
        r = await client.get("/api/notes")
        assert r.status_code == 200
        notes = r.json()["notes"]
        assert len(notes) == 2
        assert notes[0]["content"] == "second"  # newest first
        assert notes[1]["content"] == "first"

    @pytest.mark.asyncio
    async def test_delete_note(self, client, seed_notes):
        """BR-005: Successful delete returns 204."""
        note_id = seed_notes[0].id
        r = await client.delete(f"/api/notes/{note_id}")
        assert r.status_code == 204
        
        # Verify note was actually deleted
        r2 = await client.get("/api/notes")
        ids = [n["id"] for n in r2.json()["notes"]]
        assert note_id not in ids

    # BR-001 tests
    @pytest.mark.asyncio
    async def test_empty_content_rejected(self, client):
        """BR-001: Empty content must be rejected."""
        r = await client.post("/api/notes", json={"content": ""})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_whitespace_only_rejected(self, client):
        """BR-001: Whitespace-only content trimmed to empty must be rejected."""
        r = await client.post("/api/notes", json={"content": "   "})
        assert r.status_code == 422

    # BR-002 tests
    @pytest.mark.asyncio
    async def test_too_long_content_rejected(self, client):
        """BR-002: Content > 500 characters must be rejected."""
        r = await client.post("/api/notes", json={"content": "a" * 501})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_exactly_500_chars_accepted(self, client):
        """BR-002: Exactly 500 characters should be accepted."""
        r = await client.post("/api/notes", json={"content": "x" * 500})
        assert r.status_code == 201

    # BR-003 tests
    @pytest.mark.asyncio
    async def test_trim_is_stored_not_display_only(self, client):
        """BR-003: trimmed value persisted, confirmed by round-trip."""
        r = await client.post("/api/notes", json={"content": "  padded  "})
        assert r.status_code == 201
        assert r.json()["content"] == "padded"
        
        note_id = r.json()["id"]
        r2 = await client.get("/api/notes")
        note = next(n for n in r2.json()["notes"] if n["id"] == note_id)
        assert note["content"] == "padded"

    # BR-004 tests
    @pytest.mark.asyncio
    async def test_delete_zero_id(self, client):
        """BR-004: Delete with ID=0 must be rejected."""
        r = await client.delete("/api/notes/0")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_negative_id(self, client):
        """BR-004: Delete with negative ID must be rejected."""
        r = await client.delete("/api/notes/-1")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_invalid_id_string(self, client):
        """BR-004: Delete with non-integer ID rejected by FastAPI."""
        r = await client.delete("/api/notes/abc")
        assert r.status_code == 422

    # BR-005 tests
    @pytest.mark.asyncio
    async def test_delete_nonexistent_note(self, client):
        """BR-005: Delete of valid but non-existent ID returns 404."""
        r = await client.delete("/api/notes/999999")
        assert r.status_code == 404
        assert r.json()["detail"] == "Note not found"

    # BR-006 tests
    @pytest.mark.asyncio
    async def test_no_auth_required_on_all_endpoints(self, client):
        """BR-006: CRITICAL - no auth on any endpoint."""
        # No Authorization header needed for any endpoint
        r = await client.get("/api/notes")
        assert r.status_code == 200
        
        r = await client.post("/api/notes", json={"content": "auth test"})
        assert r.status_code == 201
        note_id = r.json()["id"]
        
        r = await client.delete(f"/api/notes/{note_id}")
        assert r.status_code == 204

    # BR-008 tests
    @pytest.mark.asyncio
    async def test_unicode_4byte_content(self, client):
        """BR-008: 4-byte UTF-8 (emoji) must round-trip correctly."""
        r = await client.post("/api/notes", json={"content": "Hello 🌍"})
        assert r.status_code == 201
        assert r.json()["content"] == "Hello 🌍"

    @pytest.mark.asyncio
    async def test_multibyte_character_count_not_byte_count(self, client):
        """BR-002/RISK-006: 500 two-byte characters accepted (character semantics)."""
        content = "é" * 500  # each 'é' is 2 bytes in UTF-8 - 1000 bytes total
        r = await client.post("/api/notes", json={"content": content})
        assert r.status_code == 201

    # BR-009 tests
    @pytest.mark.asyncio
    async def test_created_at_timezone_aware(self, client):
        """BR-009/RISK-008: created_at must include timezone offset."""
        r = await client.post("/api/notes", json={"content": "tz check"})
        created_at = r.json()["created_at"]
        # Should have timezone info (+ or Z suffix)
        assert ("+" in created_at or created_at.endswith("Z"))

    @pytest.mark.asyncio
    async def test_sql_injection_payload_stored_as_literal(self, client):
        """RISK-003: injection payload must be stored as text, not executed."""
        payload = "'; DROP TABLE notes; --"
        r = await client.post("/api/notes", json={"content": payload})
        assert r.status_code == 201
        assert r.json()["content"] == payload
        
        # Verify table still exists by making another request
        r2 = await client.get("/api/notes")
        assert r2.status_code == 200

    def test_mapper_init_no_error(self):
        """RISK-010/BR-009: DeclarativeBase ORM model must not raise InvalidRequestError."""
        from app.modules.notes.models import Note  # import triggers mapper configuration
        note = Note(content="mapper check")
        assert note.content == "mapper check"