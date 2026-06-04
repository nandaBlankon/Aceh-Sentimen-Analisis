import datetime
from sqlalchemy import ForeignKey, String, Text, DateTime, Float, Boolean, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Issue(Base):
    """
    Issue represents a topic or issue tracked for sentiment analysis.
    """
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nama_isu: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    wilayah: Mapped[str] = mapped_column(String(100), default="Aceh (Keseluruhan)", nullable=False)
    keyword_regional: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Bidirectional relationship with SentimentData (cascading deletes)
    sentiment_records: Mapped[list["SentimentData"]] = relationship(
        "SentimentData", back_populates="issue", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Issue(id={self.id}, nama_isu='{self.nama_isu}', is_active={self.is_active})>"


class SentimentData(Base):
    """
    SentimentData holds the scraped text, platform, and sentiment prediction details.
    """
    __tablename__ = "sentiment_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teks: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    sentimen: Mapped[str] = mapped_column(String(50), nullable=False)  # pos / neg / netral
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    scraped_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Bidirectional relationship with Issue
    issue: Mapped["Issue"] = relationship("Issue", back_populates="sentiment_records")

    __table_args__ = (
        CheckConstraint(
            "sentimen IN ('pos', 'neg', 'netral')",
            name="check_sentiment_value"
        ),
    )

    def __repr__(self) -> str:
        return f"<SentimentData(id={self.id}, issue_id={self.issue_id}, sentimen='{self.sentimen}')>"
