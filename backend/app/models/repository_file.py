import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class RepositoryFile(Base):
    """
    Tracks every file in the repository at a specific commit SHA,
    including indexed files, fallback indexed files, and excluded files
    (secrets, binaries, oversized, vendor files).
    Exclusion reasons are stored, but excluded/secret/binary contents
    are NEVER stored in this model or exposed to AI providers.
    """
    __tablename__ = "repository_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    language_display: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Status: indexed, fallback, excluded, pending, failed
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    # Analysis mode: parser_aware, text_fallback, excluded, pending, failed
    analysis_mode: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    
    exclusion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_binary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chunks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="files")

    __table_args__ = (
        Index("ix_repo_files_repo_commit", "repository_id", "commit_sha"),
        Index("ix_repo_files_repo_path", "repository_id", "file_path"),
        Index("ix_repo_files_status", "status"),
        Index("ix_repo_files_mode", "analysis_mode"),
    )
