"""
SQLAlchemy 2.x ORM model for the notes module.

Maps exactly to the DDL in §1. Zero drift rule: any DDL change
must be reflected here and vice versa.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all models in this service."""
    pass


class Note(Base):
    """
    Persistent note record.

    BR-002: content VARCHAR(500) — enforced at Pydantic layer first,
            DB layer second.
    BR-008: PostgreSQL UTF-8 is natively 4-byte; no charset declaration needed.
    BR-009: created_at is server-default only; never set by application code.
    RISK-006: DateTime(timezone=True) → TIMESTAMPTZ in PostgreSQL;
              all timestamps are timezone-aware.
    """

    __tablename__ = "notes"

    # Primary key — auto-incremented by the DB sequence (SERIAL).
    # The application never supplies `id` on INSERT.
    # FIXED: removed init=False since this is not a dataclass mapper
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # BR-002: max 500 chars enforced here (String(500)) and in Pydantic schema.
    # BR-003: the trimmed value is what gets stored — trimming happens in the
    #         Pydantic validator before this column ever receives the value.
    content: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # BR-009: server_default means the DB sets this; app layer never touches it.
    # RISK-006: timezone=True → TIMESTAMPTZ; stores and returns UTC-aware datetimes.
    # FIXED: removed init=False since this is not a dataclass mapper
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"Note(id={self.id!r}, content={self.content[:30]!r}, created_at={self.created_at!r})"