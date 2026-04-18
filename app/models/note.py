from sqlalchemy import (
    Column,
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Text,
    Boolean,
    Integer,
    func,
    text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import CITEXT
from app.core.db import Base
from app.models.note_tag import note_tags


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

    title = Column(CITEXT, nullable=False)

    content_md = Column(Text, nullable=False)

    version = Column(Integer, nullable=False, server_default=text("0"))

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
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notes", lazy="selectin")
    folder = relationship("Folder", back_populates="notes", lazy="selectin")
    revisions = relationship(
        "NoteRevision",
        back_populates="note",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    issues = relationship(
        "Issue", back_populates="note", lazy="selectin", cascade="all, delete-orphan"
    )
    tags = relationship(
        "Tag", secondary=note_tags, back_populates="notes", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_notes_user", "user_id"),
        Index("ix_notes_folder", "folder_id"),
        Index(
            "ix_notes_user_active",
            "user_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_notes_public_active",
            "is_public",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        UniqueConstraint(
            "user_id",
            "folder_id",
            "title",
            name="uq_notes_user_folder_title_active",
            deferrable=False,
        ),
        Index(
            "uq_notes_user_folder_title_active",
            "user_id",
            func.coalesce(folder_id, 0),
            title,
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
