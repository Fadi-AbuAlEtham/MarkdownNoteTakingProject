from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    Identity,
    Text,
    Boolean,
    func,
    text,
    Index,
    Table,
)
from sqlalchemy.orm import relationship
from app.core.db import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    folder_id = Column(
        BigInteger,
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(String(200), nullable=False)
    content_md = Column(Text, nullable=False)

    is_public = Column(Boolean, nullable=False, server_default=text("false"))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="notes", lazy="selectin")
    folder = relationship("Folder", back_populates="notes", lazy="joined")
    revisions = relationship(
        "NoteRevision",
        back_populates="note",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    issues = relationship(
        "Issue", back_populates="note", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("notes_user_idx", "user_id"),
        Index("notes_folder_idx", "folder_id"),
    )
