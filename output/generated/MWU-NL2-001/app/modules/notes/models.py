from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Note(Base):
    """ORM model for the notes table.

    Matches DDL exactly:
      BIGINT GENERATED ALWAYS AS IDENTITY → BigInteger + autoincrement=True
      VARCHAR(500)                        → String(500)
      TIMESTAMPTZ                         → DateTime(timezone=True)
      NOT NULL                            → nullable=False on every column
      CHECK TRIM != ''                    → CheckConstraint in __table_args__
    """

    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("TRIM(content) <> ''", name="chk_notes_content_nonempty"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )