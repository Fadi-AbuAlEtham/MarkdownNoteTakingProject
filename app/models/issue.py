from sqlalchemy import (
    Column,
    BigInteger,
    Identity,
    ForeignKey,
    DateTime,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.db import Base


class Issue(Base):
    __tablename__ = "issues"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)

    note_id = Column(
        BigInteger,
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    revision_id = Column(
        BigInteger,
        ForeignKey("note_revisions.id", ondelete="CASCADE"),
        nullable=True,
    )

    rule = Column(String(100))
    description = Column(Text)
    suggestion = Column(Text)
    start_offset = Column(Integer)
    end_offset = Column(Integer)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("issues_note_rev_idx", "note_id", "revision_id"),)

    note = relationship("Note", back_populates="issues", lazy="selectin")
    revision = relationship("NoteRevision", lazy="selectin")
