from sqlalchemy import Column, BigInteger, VARCHAR, DateTime, ForeignKey, Identity
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.db import Base


class Folder(Base):
    __tablename__ = "folders"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    parent_id = Column(
        BigInteger,
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(VARCHAR(120), nullable=False)
    status = Column(VARCHAR(32), nullable=False, server_default="active")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="folders")
    parent = relationship("Folder", remote_side=[id], back_populates="children")
    children = relationship("Folder", back_populates="parent")
