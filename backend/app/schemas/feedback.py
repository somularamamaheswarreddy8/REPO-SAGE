from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class FindingFeedbackCreate(BaseModel):
    is_useful: bool = Field(..., description="True if finding was useful, False if incorrect/false positive")
    reason: Optional[str] = Field(default=None, max_length=1000, description="Optional brief developer rationale")


class FindingFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    finding_id: int
    is_useful: bool
    reason: Optional[str]
    model_provider: str
    prompt_version: str
    commit_sha: str
    created_at: datetime


class EvaluationMetricsResponse(BaseModel):
    benchmark_version: str
    total_test_cases: int
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    usefulness_rate: Optional[float] = None
    total_feedbacks_recorded: int
    summary_citation_accuracy: float = 1.0
    summary_unsupported_claims: int = 0
    summary_incorrect_claims: int = 0
    summary_missing_facts: int = 0
    evaluation_timestamp: datetime
