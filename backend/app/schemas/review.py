from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


class ReviewFindingBase(BaseModel):
    severity: str = Field(..., description="Severity level: critical, high, medium, or low")
    category: str = Field(default="security", description="Finding category: security, correctness, reliability, performance")
    title: str = Field(..., max_length=256, description="Concise summary title of the finding")
    explanation: str = Field(..., description="Detailed explanation of the issue")
    file_path: str = Field(..., description="Target file path in repository")
    start_line: int = Field(..., ge=1, description="Starting line number")
    end_line: int = Field(..., ge=1, description="Ending line number")
    diff_line_reference: Optional[str] = Field(default=None, description="Connected changed line reference in diff")
    why_problem: str = Field(..., description="Why this is a problem or potential risk")
    suggested_improvement: str = Field(..., description="Concrete code or architecture improvement")
    suggested_tests: Optional[str] = Field(default=None, description="Suggested test cases to verify fix")
    suggested_fix_snippet: Optional[str] = Field(default=None, description="Suggested replacement code snippet")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    is_confirmed_problem: bool = Field(default=True, description="True if confirmed bug/vulnerability, False if possible risk")

    @field_validator("severity")
    def validate_severity(cls, v: str) -> str:
        valid = {"critical", "high", "medium", "low"}
        if v.lower() not in valid:
            raise ValueError(f"Severity must be one of {valid}, got {v}")
        return v.lower()


class ReviewFindingResponse(ReviewFindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    published_to_github: bool
    github_comment_id: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime


class PRReviewCreateRequest(BaseModel):
    pr_number: int = Field(..., ge=1, description="Pull request number")
    title: Optional[str] = Field(default=None, description="PR Title")
    head_commit_sha: Optional[str] = Field(default=None, description="Head commit SHA")
    base_commit_sha: Optional[str] = Field(default=None, description="Base commit SHA")
    custom_diff: Optional[str] = Field(default=None, description="Optional custom unified diff content for manual or offline review")


class PRReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    repository_id: int
    pr_number: int
    title: str
    base_commit_sha: str
    head_commit_sha: str
    status: str  # queued, in_progress, completed, failed
    summary: Optional[str]
    error_message: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    eval_version: Optional[str] = None
    ci_check_published: bool
    findings: List[ReviewFindingResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PublishCommentsRequest(BaseModel):
    finding_ids: List[int] = Field(..., min_length=1, description="IDs of findings user selected to publish")
    explicit_user_approval: bool = Field(
        ...,
        description="Explicit confirmation flag: must be True to authorize posting comments to GitHub"
    )
    user_identifier: str = Field(default="developer", description="Identifier of the approving developer")

    @field_validator("explicit_user_approval")
    def must_be_true(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Explicit developer approval is required to publish review comments.")
        return v


class PublishCommentsResponse(BaseModel):
    published_count: int
    published_findings: List[int]
    audit_log_id: int
    message: str


class PRImpactResponse(BaseModel):
    pr_number: int
    repository_id: int
    commit_sha: Optional[str] = None
    changed_files_count: int = 0
    changed_files: List[Dict[str, Any]] = []
    downstream_impacts: List[Dict[str, Any]] = []
    affected_tests: List[Dict[str, Any]] = []
    untraced_areas: List[Dict[str, Any]] = []
    test_gaps: List[Dict[str, Any]] = []
    execution_policy: str
    coverage_notice: str

