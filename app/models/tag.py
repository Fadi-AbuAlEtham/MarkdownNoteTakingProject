from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    Identity,
    UniqueConstraint,
)

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

    title = Column(String(64), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("user_id", "title", name="uq_tags_user_title"),)

    user = relationship("User", back_populates="tags", lazy="selectin")
