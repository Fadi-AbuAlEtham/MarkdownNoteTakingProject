from sqlalchemy import (
    Column,
    BigInteger,
    Identity,
    ForeignKey,
    DateTime,
    Text,
    Integer,
    String,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.db import Base


class GrammarAudit(Base):
    __tablename__ = "grammar_audits"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)
    revision_id = Column(
        BigInteger,
        ForeignKey("note_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(64), nullable=False)
    language = Column(String(16), nullable=False, default="en")
    issue_count = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    revision = relationship(
        "NoteRevision", lazy="joined", back_populates="grammar_audits"
    )
    issues = relationship(
        "GrammarIssue",
        lazy="selectin",
        cascade="all,delete-orphan",
        back_populates="audit",
    )


class GrammarIssue(Base):
    __tablename__ = "grammar_issues"

    id = Column(BigInteger, Identity(always=True), primary_key=True, index=True)
    audit_id = Column(
        BigInteger,
        ForeignKey("grammar_audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_id = Column(
        BigInteger,
        ForeignKey("note_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    start = Column(Integer, nullable=False)
    length = Column(Integer, nullable=False)

    message = Column(Text, nullable=False)
    rule_id = Column(String(128), nullable=True)
    category = Column(String(128), nullable=True)
    severity = Column(String(16), nullable=False, default="info")

    original = Column(Text, nullable=False)
    replacements = Column(JSONB, nullable=False, default=list)

    is_applied = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    audit = relationship("GrammarAudit", lazy="joined", back_populates="issues")
