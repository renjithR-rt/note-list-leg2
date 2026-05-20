from __future__ import annotations

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notes.models import Note
from app.modules.notes.schemas import NoteCreate, NoteRead
from app.modules.notes.service import NoteService


class TestNoteSchemas:
    """Unit tests for Pydantic schemas — BR validation."""

    def test_note_create_valid(self):
        """BR-BACKEND-002: 500-char content accepted."""
        note = NoteCreate(content="a" * 500)
        assert note.content == "a" * 500

    def test_note_create_too_long(self):
        """BR-BACKEND-002: 501-char content rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NoteCreate(content="a" * 501)
        assert "String should have at most 500 characters" in str(exc_info.value)

    def test_note_create_empty_content(self):
        """BR-BACKEND-001: Empty content rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NoteCreate(content="")
        assert "Note cannot be empty" in str(exc_info.value)

    def test_note_create_whitespace_only(self):
        """BR-BACKEND-001: Whitespace-only content rejected after strip."""
        with pytest.raises(ValidationError) as exc_info:
            NoteCreate(content="   ")
        assert "Note cannot be empty" in str(exc_info.value)

    def test_note_create_strip_whitespace(self):
        """BR-BACKEND-006: Leading/trailing whitespace stripped."""
        note = NoteCreate(content="  hello  ")
        assert note.content == "hello"

    def test_note_create_strip_tabs_newlines(self):
        """BR-BACKEND-006: Tabs and newlines stripped."""
        note = NoteCreate(content="\thello\n")
        assert note.content == "hello"

    def test_note_create_strip_within_limit(self):
        """BR-BACKEND-006: max_length check on stripped value."""
        # 502 chars before strip, 500 chars after strip
        content = "  " + "a" * 500 + "  "
        note = NoteCreate(content=content)
        assert note.content == "a" * 500


class TestNoteService:
    """Service layer tests — business logic and database operations."""

    @pytest.mark.asyncio
    async def test_list_notes_empty(self, db_session: AsyncSession):
        """BR-BACKEND-008: Empty list when no notes exist."""
        service = NoteService(db_session)
        notes = await service.list_notes()
        assert notes == []

    @pytest.mark.asyncio
    async def test_create_note(self, db_session: AsyncSession):
        """Happy path: create note and verify all fields populated."""
        service = NoteService(db_session)
        note = await service.create_note("Test note")
        
        assert note.id is not None
        assert note.content == "Test note"
        assert note.created_at is not None

    @pytest.mark.asyncio
    async def test_list_notes_ordering(self, db_session: AsyncSession):
        """BR-BACKEND-005: Notes returned newest-first."""
        service = NoteService(db_session)
        
        note1 = await service.create_note("First note")
        note2 = await service.create_note("Second note")
        note3 = await service.create_note("Third note")
        
        notes = await service.list_notes()
        assert len(notes) == 3
        assert notes[0].id == note3.id  # newest first
        assert notes[1].id == note2.id
        assert notes[2].id == note1.id  # oldest last

    @pytest.mark.asyncio
    async def test_delete_note_existing(self, db_session: AsyncSession):
        """Happy path: delete existing note succeeds."""
        service = NoteService(db_session)
        note = await service.create_note("To delete")
        
        await service.delete_note(note.id)
        
        # Verify note is gone
        notes = await service.list_notes()
        assert len(notes) == 0

    @pytest.mark.asyncio
    async def test_delete_note_not_found(self, db_session: AsyncSession):
        """BR-BACKEND-007: 404 when deleting non-existent note."""
        service = NoteService(db_session)
        
        with pytest.raises(Exception) as exc_info:
            await service.delete_note(99999)
        assert exc_info.value.status_code == 404
        assert "Note not found" in exc_info.value.detail


class TestNoteEndpoints:
    """Integration tests — full HTTP request/response cycle."""

    @pytest.mark.asyncio
    async def test_get_notes_empty(self, client: AsyncClient):
        """BR-BACKEND-008: GET /notes returns empty array when no notes."""
        response = await client.get("/notes")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_post_note_valid(self, client: AsyncClient):
        """Happy path: POST /notes with valid content."""
        response = await client.post(
            "/notes",
            json={"content": "My test note"}
        )
        assert response.status_code == 201
        
        data = response.json()
        assert data["id"] is not None
        assert data["content"] == "My test note"
        assert data["created_at"] is not None

    @pytest.mark.asyncio
    async def test_post_note_empty_content(self, client: AsyncClient):
        """BR-BACKEND-001: POST /notes with empty content rejected."""
        response = await client.post(
            "/notes",
            json={"content": ""}
        )
        assert response.status_code == 422
        assert "Note cannot be empty" in response.text

    @pytest.mark.asyncio
    async def test_post_note_whitespace_only(self, client: AsyncClient):
        """BR-BACKEND-001: POST /notes with whitespace-only content rejected."""
        response = await client.post(
            "/notes",
            json={"content": "   "}
        )
        assert response.status_code == 422
        assert "Note cannot be empty" in response.text

    @pytest.mark.asyncio
    async def test_post_note_too_long(self, client: AsyncClient):
        """BR-BACKEND-002: POST /notes with >500 chars rejected."""
        response = await client.post(
            "/notes",
            json={"content": "a" * 501}
        )
        assert response.status_code == 422
        assert "String should have at most 500 characters" in response.text

    @pytest.mark.asyncio
    async def test_delete_note_valid(self, client: AsyncClient):
        """Happy path: DELETE /notes/{id} for existing note."""
        # Create a note first
        create_response = await client.post(
            "/notes",
            json={"content": "To delete"}
        )
        note_id = create_response.json()["id"]
        
        # Delete it
        delete_response = await client.delete(f"/notes/{note_id}")
        assert delete_response.status_code == 204
        
        # Verify it's gone
        list_response = await client.get("/notes")
        assert list_response.json() == []

    @pytest.mark.asyncio
    async def test_delete_note_not_found(self, client: AsyncClient):
        """BR-BACKEND-007: DELETE /notes/{id} for non-existent note returns 404."""
        response = await client.delete("/notes/99999")
        assert response.status_code == 404
        assert "Note not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_note_invalid_id(self, client: AsyncClient):
        """BR-BACKEND-003: DELETE /notes with invalid ID rejected."""
        # Test zero
        response = await client.delete("/notes/0")
        assert response.status_code == 422
        
        # Test negative
        response = await client.delete("/notes/-1")
        assert response.status_code == 422
        
        # Test non-integer
        response = await client.delete("/notes/abc")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_full_workflow(self, client: AsyncClient):
        """Integration test: create, list, delete workflow."""
        # Start with empty list
        response = await client.get("/notes")
        assert response.json() == []
        
        # Create three notes
        note1 = await client.post("/notes", json={"content": "First note"})
        note2 = await client.post("/notes", json={"content": "Second note"})
        note3 = await client.post("/notes", json={"content": "Third note"})
        
        # List notes — should be newest-first
        response = await client.get("/notes")
        notes = response.json()
        assert len(notes) == 3
        assert notes[0]["content"] == "Third note"   # newest first
        assert notes[1]["content"] == "Second note"
        assert notes[2]["content"] == "First note"   # oldest last
        
        # Delete middle note
        middle_id = note2.json()["id"]
        await client.delete(f"/notes/{middle_id}")
        
        # List again — should have 2 notes, still ordered
        response = await client.get("/notes")
        notes = response.json()
        assert len(notes) == 2
        assert notes[0]["content"] == "Third note"
        assert notes[1]["content"] == "First note"

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, client: AsyncClient):
        """Security test: SQL injection in content field."""
        malicious_content = "'); DROP TABLE notes; --"
        
        response = await client.post(
            "/notes",
            json={"content": malicious_content}
        )
        assert response.status_code == 201
        
        # Verify note stored as literal string
        created_note = response.json()
        assert created_note["content"] == malicious_content
        
        # Verify table still exists by listing notes
        list_response = await client.get("/notes")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

    @pytest.mark.asyncio
    async def test_multibyte_content(self, client: AsyncClient):
        """BR-BACKEND-002: Character-length semantics with emoji."""
        # 500 emoji characters = 500 chars but 2000+ bytes
        emoji_content = "😀" * 500
        
        response = await client.post(
            "/notes",
            json={"content": emoji_content}
        )
        assert response.status_code == 201
        assert response.json()["content"] == emoji_content