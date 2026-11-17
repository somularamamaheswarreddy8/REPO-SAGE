import datetime
import json
from typing import Optional, List
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index, TypeDecorator
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.config import settings

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class PortableVector(TypeDecorator):
    """
    Portable Vector type: uses pgvector.sqlalchemy.Vector when on PostgreSQL,
    and falls back to JSON (list of floats) on SQLite or when pgvector is missing.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return dialect.type_descriptor(Vector(settings.EMBEDDING_DIMENSION))
        return dialect.type_descriptor(JSON)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            if dialect.name == "postgresql" and HAS_PGVECTOR:
                return value
            return value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_mode: Mapped[str] = mapped_column(String(32), default="text_fallback", nullable=False)
    
    symbol_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    symbol_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # function, class, method, module
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # SHA-256
    
    embedding: Mapped[Optional[List[float]]] = mapped_column(PortableVector, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_repo_commit", "repository_id", "commit_sha"),
        Index("ix_chunks_repo_file", "repository_id", "file_path"),
    )
