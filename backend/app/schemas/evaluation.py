import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TestedCommitInfo(BaseModel):
    repository_id: int
    full_name: str
    branch: str
    indexed_commit_sha: Optional[str]
    indexing_status: str
    is_stale: bool
    last_indexed_at: Optional[datetime.datetime]


class QualityReportResponse(BaseModel):
    evaluation_date: datetime.datetime
    benchmark_version: str = "v2.0-multi-repo"
    sample_size: int
    correct_repo_selection_pct: float
    cross_repo_leakage_count: int
    answer_correctness_pct: float
    citation_accuracy_pct: float
    indexing_failures_count: int
    stale_indexes_count: int
    tested_commits: List[TestedCommitInfo]
    feedback_breakdown: Dict[str, int]
    failing_cases: List[Dict[str, Any]] = []
    limitations: List[str]
