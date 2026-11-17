import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class FindingFeedback(Base):
    __tablename__ = "finding_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("review_findings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    is_useful: Mapped[bool] = mapped_column(Boolean, nullable=False)  # True = useful, False = incorrect
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Context required for evaluation without retaining unnecessary sensitive source content
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    finding: Mapped["ReviewFinding"] = relationship("ReviewFinding", back_populates="feedbacks")

    __table_args__ = (
        Index("ix_feedback_model_version", "model_provider", "prompt_version"),
    )


class RepositoryFeedback(Base):
    """
    Stores developer feedback (useful or incorrect with optional reason)
    for both PR review findings and Code Q&A answers.
    Used for evaluation and reporting without silently altering review rules.
    """
    __tablename__ = "repository_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    branch: Mapped[Optional[str]] = mapped_column(String(128), default="main", nullable=True)
    commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'finding' or 'answer'
    target_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="useful", nullable=False)
    is_useful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_repo_feedback_target", "repository_id", "target_type", "target_id"),
        Index("ix_repo_feedback_commit", "repository_id", "commit_sha"),
    )
