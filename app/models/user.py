from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DATE,
    DateTime,
    Identity,
    Index,
    Boolean,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.sql import func

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)

    username = Column(CITEXT, nullable=False)
    email = Column(CITEXT, nullable=False)

    password_hash = Column(Text, nullable=False)
    dob = Column(DATE)
    phone_number = Column(Text)

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
        Index(
            "uq_users_email_active",
            email,
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
        Index(
            "uq_users_username_active",
            username,
            unique=True,
            postgresql_where=deleted_at.is_(None),
        ),
    )
