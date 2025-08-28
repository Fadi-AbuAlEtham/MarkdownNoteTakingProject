from sqlalchemy import (
    Column,
    BigInteger,
    Identity,
    ForeignKey,
    DateTime,
    Integer,
    Text,
    CheckConstraint,
    UniqueConstraint,
    Index,
    Boolean,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.db import Base


class NoteRevision(Base):
    __tablename__ = "note_revisions"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)

    note_id = Column(
        BigInteger,
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    version = Column(Integer, nullable=False)

    title = Column(CITEXT, nullable=False)

    content_md = Column(Text, nullable=False)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active = Column(Boolean, server_default="true", nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("version > 0", name="ck_note_revisions_version_gt_0"),
        UniqueConstraint("note_id", "version", name="uq_note_revisions_note_version"),
        Index("ix_note_revisions_note", "note_id"),
        Index(
            "ix_note_revisions_note_active",
            "note_id",
            postgresql_where=(deleted_at.is_(None)),
        ),
    )

    note = relationship("Note", back_populates="revisions", lazy="selectin")
    author = relationship("User", lazy="joined")
