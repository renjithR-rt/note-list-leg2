from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Note(Base):
    """ORM model for the notes table - owned by MWU-NL2-001.
    
    BR-008: UTF-8 storage with PostgreSQL 4-byte UTF-8 upgrade from MySQL 3-byte.
    """

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(String(500), nullable=False)  # BR-002: 500 char limit
    # BR-009: DB sets this via server_default; never use init=False on DeclarativeBase
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # BR-008: TIMESTAMPTZ upgrade from MySQL DATETIME
        server_default=func.now(),
        nullable=False,
    )