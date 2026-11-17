import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_repo_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(64), default="main", nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    indexed_commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    indexing_status: Mapped[str] = mapped_column(
        String(32), default="not_indexed", nullable=False
    )  # not_indexed, queued, running, completed, failed
    indexing_progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    indexing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deep_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_indexed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False
    )

    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="repositories")
    settings: Mapped["RepositorySettings"] = relationship(
        "RepositorySettings", back_populates="repository", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
    chunks: Mapped[List["CodeChunk"]] = relationship(
        "CodeChunk", back_populates="repository", cascade="all, delete-orphan"
    )
    files: Mapped[List["RepositoryFile"]] = relationship(
        "RepositoryFile", back_populates="repository", cascade="all, delete-orphan"
    )
    relationships: Mapped[List["CodeRelationship"]] = relationship(
        "CodeRelationship", back_populates="repository", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["PRReview"]] = relationship(
        "PRReview", back_populates="repository", cascade="all, delete-orphan"
    )


class RepositorySettings(Base):
    __tablename__ = "repository_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # The optional CI summary may run only after a repository owner enables it in settings.
    # It must not block merges by default.
    optional_ci_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocking_ci_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_review_prs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_severity_to_alert: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="settings")
