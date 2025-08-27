from sqlalchemy import (
    Column,
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Boolean,
    Index,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.db import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(CITEXT, nullable=False)

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

    user = relationship("User", back_populates="tags", lazy="selectin")

    __table_args__ = (
        # Unique per user among *active* (not soft-deleted) tags
        Index(
            "uq_tags_user_title_active",
            user_id,
            title,
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        # Helpful for lookups by owner (active only)
        Index(
            "ix_tags_user_active",
            user_id,
            postgresql_where=deleted_at.is_(None),
        ),
    )
