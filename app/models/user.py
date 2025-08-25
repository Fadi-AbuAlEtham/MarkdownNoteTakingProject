from sqlalchemy import Column, BigInteger, VARCHAR, Text, DATE, DateTime, Identity
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.sql import func

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)
    username = Column(CITEXT, nullable=False, unique=True)
    email = Column(CITEXT, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    dob = Column(DATE)
    phone_number = Column(VARCHAR(25))
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
