from sqlalchemy import Table, Column, BigInteger, ForeignKey

from app.core.db import Base

note_tags = Table(
    "note_tags",
    Base.metadata,
    Column(
        "note_id",
        BigInteger,
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "tag_id",
        BigInteger,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)