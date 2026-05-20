from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.modules.notes.models import Note
from app.modules.notes.schemas import NoteCreate


class NoteService:
    """All business logic for the notes module - stateless, async."""

    @staticmethod
    async def list_notes(db: AsyncSession) -> list[Note]:
        """Return all notes ordered newest-first.

        BR-007: ORDER BY created_at DESC, no user-configurable sort.
        """
        result = await db.execute(
            select(Note).order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_note(db: AsyncSession, data: NoteCreate) -> Note:
        """Persist a new note.

        BR-003/001/002: already enforced by Pydantic before this method is called.
        BR-009: created_at not passed - DB server_default applies.
        RISK-005: flush + refresh to populate auto-generated id and created_at.
        """
        note = Note(content=data.content)
        db.add(note)
        await db.flush()
        await db.refresh(note)  # populates id and server-generated created_at
        return note

    @staticmethod
    async def delete_note(db: AsyncSession, note_id: int) -> None:
        """Delete a note by ID.

        BR-004: note_id must be a positive integer (> 0).
        BR-005: raise 404 when note does not exist (GAP REMEDIATION).
        """
        # BR-004: guard against zero or negative ID before issuing SQL
        if note_id <= 0:
            raise HTTPException(status_code=422, detail="Invalid note ID")

        result = await db.execute(
            delete(Note).where(Note.id == note_id)
        )
        # BR-005: legacy silently returned ok:true - target returns 404
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Note not found")