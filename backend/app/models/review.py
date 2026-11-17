import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PRReview(Base):
    __tablename__ = "pr_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pr_number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    base_commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    head_commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    
    status: Mapped[str] = mapped_column(
        String(32), default="in_progress", nullable=False
    )  # queued, in_progress, completed, failed
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Audit & Observability metadata
    model_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(32), default="v1.0", nullable=True)
    eval_version: Mapped[Optional[str]] = mapped_column(String(32), default="v1.0", nullable=True)
    
    # Optional advisory check summary run
    ci_check_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ci_check_run_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="reviews")
    findings: Mapped[List["ReviewFinding"]] = relationship(
        "ReviewFinding", back_populates="review", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_reviews_repo_pr", "repository_id", "pr_number"),
    )


class ReviewFinding(Base):
    __tablename__ = "review_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pr_reviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Severity: critical, high, medium, or low
    severity: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    # Category: security, correctness, reliability, performance, maintainability
    category: Mapped[str] = mapped_column(String(64), default="security", nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Evidence: file path and line range
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    diff_line_reference: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    why_problem: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_improvement: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_tests: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_fix_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    confidence: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    # Distinguish confirmed problems from possible risks
    is_confirmed_problem: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Publishing state: requires explicit approval before publishing
    published_to_github: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    github_comment_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    published_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    review: Mapped["PRReview"] = relationship("PRReview", back_populates="findings")
    feedbacks: Mapped[List["FindingFeedback"]] = relationship(
        "FindingFeedback", back_populates="finding", cascade="all, delete-orphan"
    )
