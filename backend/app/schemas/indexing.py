from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class IndexingTriggerRequest(BaseModel):
    branch: Optional[str] = Field(default=None, description="Branch to index, defaults to repository default branch")
    force_full_reindex: bool = Field(default=False, description="Force re-indexing all files instead of incremental")


class IndexingStatusResponse(BaseModel):
    repository_id: int
    full_name: str
    status: str  # not_indexed, queued, running, completed, failed
    progress: float
    indexed_commit_sha: Optional[str]
    total_chunks: int
    error: Optional[str] = None
    updated_at: datetime
