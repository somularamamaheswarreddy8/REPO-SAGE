import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Action type: publish_review_comments, apply_code_patch, enable_ci_check, disable_ci_check,
    # repository_connect, repository_disconnect, data_deletion, role_changed
    action_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), default="local_user", nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    target_file: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    target_lines: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload_summary: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Cryptographic tamper-evident chaining
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Model & Version metadata
    model_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    index_commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    eval_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, index=True, nullable=False
    )

    __table_args__ = (
        Index("ix_audit_action_repo", "action_type", "repo_full_name"),
    )
