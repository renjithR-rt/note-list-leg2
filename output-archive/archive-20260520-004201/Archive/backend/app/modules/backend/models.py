from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, String, func
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped, mapped_column

if TYPE_CHECKING:
    pass

class Base(MappedAsDataclass, DeclarativeBase):
    pass

class Note(Base):
    """ORM model for the notes table.
    
    Maps to PostgreSQL notes table with content validation constraints.
    Implements schema from planning document §1.
    """
    
    __tablename__ = "notes"
    
    __table_args__ = (
        # BR-BACKEND-001: DB-level constraint for empty content after trim
        CheckConstraint(
            "length(trim(content)) > 0",
            name="chk_notes_content_not_empty",
        ),
        # BR-BACKEND-004: Index for efficient newest-first ordering
        Index("idx_notes_created_at_desc", "created_at", postgresql_ops={"created_at": "DESC"}),
    )
    
    # GENERATED ALWAYS AS IDENTITY → init=False, no default
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    
    # BR-BACKEND-002: VARCHAR(500) with NOT NULL constraint
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # server_default so ORM doesn't send value; PostgreSQL NOW() fills it
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        init=False,
    )
    
    def __repr__(self) -> str:
        return f"Note(id={self.id!r}, content={self.content!r}, created_at={self.created_at!r})"