from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notes.models import Note


class NoteService:
    """Business logic layer for note operations.

    Receives a pre-configured AsyncSession from the DI layer.
    Never constructs its own session or engine.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # list_notes
    # BRs: BR-BACKEND-005 (ORDER BY created_at DESC), BR-BACKEND-008 (no LIMIT)
    # Transaction: read-only — no commit needed
    # ------------------------------------------------------------------
    async def list_notes(self) -> list[Note]:
        """Return all notes ordered newest-first.

        BR-BACKEND-005: ORDER BY created_at DESC — only supported sort.
        BR-BACKEND-008: No LIMIT / OFFSET — all rows returned.
        """
        result = await self._db.execute(
            select(Note).order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # create_note
    # BRs: BR-BACKEND-001, BR-BACKEND-002, BR-BACKEND-006 enforced upstream
    #      by NoteCreate schema before this method is called.
    # Transaction: single INSERT + commit
    # ------------------------------------------------------------------
    async def create_note(self, content: str) -> Note:
        """Persist a new note and return the persisted ORM instance.

        Precondition: content has already been stripped and validated
        by NoteCreate (BR-001 empty check, BR-002 length check, BR-006 strip).
        This method does NOT re-validate — it trusts the schema layer.

        Uses flush() + refresh() to populate DB-assigned id and created_at
        before commit, so the returned Note is fully hydrated.
        """
        note = Note(content=content)
        self._db.add(note)
        await self._db.flush()     # assigns id and created_at via DB defaults
        await self._db.refresh(note)
        await self._db.commit()
        return note

    # ------------------------------------------------------------------
    # delete_note
    # BRs: BR-BACKEND-003 (gt=0 enforced at router layer before this call)
    #      BR-BACKEND-007 (404 when rowcount == 0)
    # Transaction: single DELETE + commit (only if row found)
    # ------------------------------------------------------------------
    async def delete_note(self, note_id: int) -> None:
        """Delete a note by primary key.

        BR-BACKEND-003: note_id is guaranteed > 0 by the router Path(..., gt=0).
        BR-BACKEND-007: raises HTTP 404 if no row was deleted (legacy changed to
          correct REST behaviour — pending SME confirmation per comprehension doc).
        """
        result = await self._db.execute(
            delete(Note).where(Note.id == note_id)
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found",
            )
        await self._db.commit()