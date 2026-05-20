"""
Business logic layer for notes.

Each method is annotated with the BRs it implements.
Database access uses SQLAlchemy 2.x core-style expressions (parameterized —
RISK-002: no string interpolation or f-string SQL anywhere).
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.backend.models import Note


class NoteService:
    """
    Handles all business logic for note CRUD operations.

    Constructed per-request with the FastAPI-injected AsyncSession.
    No shared state between requests.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # get_notes
    # ------------------------------------------------------------------

    async def get_notes(self) -> list[Note]:
        """
        Return all notes ordered by created_at DESC.

        BR-007: sort order is newest-first and is NOT configurable by
                the caller. The ORDER BY is hardcoded here — no sort
                parameter is accepted.

        RISK-002: uses parameterized SQLAlchemy select(), not raw SQL.
        """
        result = await self._db.execute(
            select(Note).order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # create_note
    # ------------------------------------------------------------------

    async def create_note(self, content: str) -> Note:
        """
        Persist a new note and return the full record.

        BR-003: content has already been stripped by the Pydantic schema;
                this method receives only the trimmed value.
        BR-001, BR-002: enforced upstream by NoteCreate schema;
                not re-validated here (single source of truth).
        BR-009: created_at is set by DB server_default; the INSERT
                statement never includes a value for that column.
        RISK-002: uses parameterized ORM add() — no f-string SQL.
        RISK-005: returns the ORM Note object; no server-side redirect.
        """
        note = Note(content=content)
        self._db.add(note)
        await self._db.commit()
        await self._db.refresh(note)  # Populates id and created_at from DB
        return note

    # ------------------------------------------------------------------
    # delete_note
    # ------------------------------------------------------------------

    async def delete_note(self, note_id: int) -> None:
        """
        Delete a note by primary key. Raises 404 if no row was deleted.

        BR-004: note_id > 0 is enforced at the router layer before this
                method is called; this method trusts a positive integer.
        BR-005: checks result.rowcount after DELETE. If 0 rows were
                affected the note did not exist → raise 404. This is a
                GAP REMEDIATION — legacy PHP silently returned ok:true
                even when no row was deleted. The target behaviour is
                explicit 404 as specified in the comprehension doc.
        RISK-002: uses parameterized delete() expression — no f-string SQL.
        """
        result = await self._db.execute(
            delete(Note).where(Note.id == note_id)
        )
        await self._db.commit()

        # BR-005 gap remediation: rowcount == 0 means note did not exist
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Note not found")