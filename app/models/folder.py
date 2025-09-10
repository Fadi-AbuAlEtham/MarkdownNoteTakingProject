from sqlalchemy import (
    Column,
    BigInteger,
    VARCHAR,
    DateTime,
    ForeignKey,
    Identity,
    Boolean,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import CITEXT
from app.core.db import Base


class Folder(Base):
    __tablename__ = "folders"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)

    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_id = Column(
        BigInteger, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True
    )

    title = Column(CITEXT, nullable=False)

    status = Column(VARCHAR(32), nullable=False, server_default="active")
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

    user = relationship(
        "User",
        backref=backref("folders", cascade="all, delete-orphan", lazy="raise"),
        lazy="raise",
    )
    parent = relationship(
        "Folder", remote_side=[id], back_populates="children", lazy="raise"
    )
    children = relationship("Folder", back_populates="parent", lazy="raise")

    __table_args__ = (
        # Unique per user + parent + title, only for active (not soft-deleted) folders
        Index(
            "uq_folders_user_parent_title_active",
            user_id,
            parent_id,
            title,
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        # helper index to speed common lookups
        Index(
            "ix_folders_user_parent_active",
            user_id,
            parent_id,
            postgresql_where=deleted_at.is_(None),
        ),
    )
