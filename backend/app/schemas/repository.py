from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class RepositorySettingsBase(BaseModel):
    optional_ci_enabled: bool = Field(
        default=False,
        description="Enable advisory GitHub Check summary for pull requests. Disabled by default."
    )
    blocking_ci_enabled: bool = Field(
        default=False,
        description="Require clean findings before allowing merges. Requires Administrator approval."
    )
    auto_review_prs: bool = Field(
        default=False,
        description="Whether to automatically queue reviews for incoming PR webhooks."
    )
    min_severity_to_alert: str = Field(
        default="medium",
        description="Minimum severity level (low, medium, high, critical) to include in alerts."
    )


class RepositorySettingsUpdate(RepositorySettingsBase):
    pass


class RepositorySettingsResponse(RepositorySettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    created_at: datetime
    updated_at: datetime


class RepositoryCreate(BaseModel):
    full_name: str = Field(..., description="Repository full name, e.g. 'owner/repo'")
    is_demo: bool = Field(default=False, description="Whether to create as a mock demo repository")
    default_branch: Optional[str] = "main"


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    github_repo_id: Optional[int]
    full_name: str
    owner: str
    name: str
    default_branch: str
    is_private: bool
    is_demo: bool
    organization_id: Optional[int] = None
    indexed_commit_sha: Optional[str]
    indexing_status: str
    indexing_progress: float
    indexing_error: Optional[str] = None
    summary: Optional[str] = None
    deep_analysis: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    is_stale: bool = False
    remote_commit_sha: Optional[str] = None
    settings: Optional[RepositorySettingsResponse] = None
    created_at: datetime
    updated_at: datetime


from typing import Optional, List, Dict, Any


class ProfileEvidenceCitation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    snippet: Optional[str] = None
    statement: Optional[str] = None


class ConciseOverview(BaseModel):
    purpose: str
    purpose_evidence: List[ProfileEvidenceCitation] = []
    languages: List[Dict[str, Any]] = []
    frameworks: List[Dict[str, Any]] = []
    entry_points: List[Dict[str, Any]] = []
    components: List[Dict[str, Any]] = []
    integrations: List[Dict[str, Any]] = []
    commands: List[Dict[str, Any]] = []
    unconfirmed: List[str] = []


class DeepAnalysisModule(BaseModel):
    name: str
    file_path: str
    explanation: str
    citations: List[ProfileEvidenceCitation] = []


class DeepAnalysisFlow(BaseModel):
    name: str
    description: str
    steps: List[Dict[str, Any]] = []


class DeepAnalysisRisk(BaseModel):
    title: str
    severity: str
    description: str
    evidence: List[ProfileEvidenceCitation] = []


class DeepAnalysis(BaseModel):
    modules: List[DeepAnalysisModule] = []
    architecture_map: List[Dict[str, Any]] = []
    key_code_flows: List[DeepAnalysisFlow] = []
    potential_risks: List[DeepAnalysisRisk] = []


class RepositorySummaryResponse(BaseModel):
    repository_id: int
    full_name: str
    branch: str
    commit_sha: Optional[str]
    indexing_status: str
    indexing_freshness: Optional[str] = None
    total_files: int
    total_symbols: int
    languages: List[str]
    summary: str
    overview: Optional[ConciseOverview] = None
    deep_analysis: Optional[DeepAnalysis] = None
    verified_citations_count: int = 0


class RepositoryFileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    filename: str
    file_size: int
    language: str
    language_display: str
    status: str
    analysis_mode: str
    exclusion_reason: Optional[str] = None
    is_secret: bool = False
    is_binary: bool = False
    chunks_count: int = 0


class RepositoryTreeCoverage(BaseModel):
    total_files: int
    parser_aware: int
    fallback: int
    excluded: int
    pending: int
    failed: int


class RepositoryTreeResponse(BaseModel):
    repository_id: int
    full_name: str
    branch: str
    commit_sha: Optional[str] = None
    indexing_status: str
    indexing_progress: float
    coverage: RepositoryTreeCoverage
    files: List[RepositoryFileItem]
    total_count: int
    limit: int
    offset: int


class FileContentResponse(BaseModel):
    repository_id: int
    file_path: str
    allowed: bool
    language: Optional[str] = None
    language_display: Optional[str] = None
    analysis_mode: Optional[str] = None
    exclusion_reason: Optional[str] = None
    is_secret: bool = False
    is_binary: bool = False
    content: Optional[str] = None
    lines_count: Optional[int] = None
    size_bytes: Optional[int] = None


class HealthFileItem(BaseModel):
    file_path: str
    filename: str
    status: str
    analysis_mode: str
    category: str
    exclusion_reason: Optional[str] = None
    is_secret: bool = False
    is_binary: bool = False
    is_safe_to_view_in_explorer: bool = True
    language_display: str
    file_size_bytes: int


class RepositoryHealthDashboardResponse(BaseModel):
    repository_id: int
    full_name: str
    branch: str
    indexed_commit_sha: Optional[str] = None
    remote_commit_sha: Optional[str] = None
    is_stale: bool = False
    indexing_status: str
    indexing_progress: float
    last_indexed_at: Optional[datetime] = None
    total_discovered_files: int
    indexed_files_count: int
    parser_aware_count: int
    text_fallback_count: int
    excluded_secrets_count: int
    excluded_binaries_count: int
    excluded_vendors_count: int
    unsupported_or_failed_count: int
    database_mode: str
    database_vector_capabilities: str
    files_summary: List[HealthFileItem]


class RepositoryOnboardingResponse(BaseModel):
    repository_id: int
    full_name: str
    branch: str
    commit_sha: Optional[str] = None
    indexing_status: str
    overview_summary: str
    entry_points: List[Dict[str, Any]] = []
    modules: List[Dict[str, Any]] = []
    module_connections: List[Dict[str, Any]] = []
    module_tests: List[Dict[str, Any]] = []
    total_modules: int = 0
    total_entry_points: int = 0
    unconfirmed_note: str


class CommitCompareResponse(BaseModel):
    repository_id: int
    full_name: str
    base: Dict[str, Any]
    head: Dict[str, Any]
    summary: Dict[str, Any]
    files_changed: List[Dict[str, Any]] = []
    architecture_diff: Dict[str, Any]
    findings_diff: Dict[str, Any]
    status_notice: str


class DependencyInventoryResponse(BaseModel):
    repository_id: int
    full_name: str
    commit_sha: Optional[str] = None
    scan_timestamp: str
    manifest_files: List[str] = []
    summary: Dict[str, Any]
    dependencies: List[Dict[str, Any]] = []
    vulnerability_notice: str
    verification_source: str
    checked_at: str


class RepositoryFeedbackCreate(BaseModel):
    commit_sha: str
    target_type: str  # 'finding' or 'answer'
    target_id: str
    is_useful: bool
    branch: Optional[str] = "main"
    category: Optional[str] = "useful"  # 'useful', 'wrong_repository', 'wrong_citation', 'irrelevant', 'outdated'
    reason: Optional[str] = None


class RepositoryFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    branch: Optional[str] = "main"
    commit_sha: str
    target_type: str
    target_id: str
    category: Optional[str] = "useful"
    is_useful: bool
    reason: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime


