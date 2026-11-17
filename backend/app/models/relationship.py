import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class CodeRelationship(Base):
    __tablename__ = "code_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    
    source_file: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    target_file: Mapped[Optional[str]] = mapped_column(String(512), index=True, nullable=True)
    
    relationship_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # imports, calls, defines, inherits
    source_symbol: Mapped[str] = mapped_column(String(256), nullable=False)
    target_symbol: Mapped[str] = mapped_column(String(256), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_snippet: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="relationships")

    __table_args__ = (
        Index("ix_rel_repo_source", "repository_id", "source_file"),
        Index("ix_rel_repo_type", "repository_id", "relationship_type"),
    )
