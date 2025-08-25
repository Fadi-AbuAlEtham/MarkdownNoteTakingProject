from sqlalchemy import (
    Column,
    BigInteger,
    Identity,
    ForeignKey,
    DateTime,
    Integer,
    String,
    Text,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
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
    title = Column(String(200), nullable=False)
    content_md = Column(Text, nullable=False)

    created_by = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("version > 0", name="ck_note_revisions_version_gt_0"),
        UniqueConstraint("note_id", "version", name="uq_note_revisions_note_version"),
        Index("note_revisions_note_idx", "note_id"),
    )

    note = relationship("Note", back_populates="revisions", lazy="selectin")
    author = relationship("User", lazy="joined")
