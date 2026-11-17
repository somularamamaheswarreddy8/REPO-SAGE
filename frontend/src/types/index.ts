export interface RepositorySettings {
  id: number;
  repository_id: number;
  optional_ci_enabled: boolean;
  blocking_ci_enabled?: boolean;
  auto_review_prs: boolean;
  min_severity_to_alert: string;
  created_at: string;
  updated_at: string;
}

export interface Repository {
  id: number;
  github_repo_id: number | null;
  full_name: string;
  owner: string;
  name: string;
  default_branch: string;
  is_private: boolean;
  is_demo: boolean;
  organization_id?: number | null;
  indexed_commit_sha: string | null;
  remote_commit_sha?: string | null;
  indexing_status: 'not_indexed' | 'queued' | 'running' | 'completed' | 'failed';
  indexing_progress: number;
  indexing_error: string | null;
  summary: string | null;
  last_indexed_at?: string | null;
  is_stale?: boolean;
  settings?: RepositorySettings;
  created_at: string;
  updated_at: string;
}

export interface ProfileEvidenceCitation {
  file_path: string;
  start_line: number;
  end_line: number;
  snippet?: string | null;
  statement?: string | null;
}

export interface ConciseOverview {
  purpose: string;
  purpose_evidence: ProfileEvidenceCitation[];
  languages: { name: string; files: number; percentage: number }[];
  frameworks: { name: string; file_path?: string; lines?: string; evidence?: string }[];
  entry_points: { file_path: string; symbol?: string; description?: string }[];
  components: { name: string; file_path: string; description: string }[];
  integrations: { name: string; type: string; file_path?: string; lines?: string; details?: string }[];
  commands: { name: string; command: string; file_path?: string; lines?: string }[];
  unconfirmed: string[];
}

export interface DeepAnalysisModule {
  name: string;
  file_path: string;
  explanation: string;
  citations: ProfileEvidenceCitation[];
}

export interface DeepAnalysisFlow {
  name: string;
  description: string;
  steps: { order: number; step: string; file_path?: string; lines?: string }[];
}

export interface DeepAnalysisRisk {
  title: string;
  severity: string;
  description: string;
  evidence: ProfileEvidenceCitation[];
}

export interface DeepAnalysis {
  modules: DeepAnalysisModule[];
  architecture_map: { from: string; to: string; type: string; evidence: string }[];
  key_code_flows: DeepAnalysisFlow[];
  potential_risks: DeepAnalysisRisk[];
}

export interface RepositorySummary {
  repository_id: number;
  full_name: string;
  branch?: string;
  commit_sha: string | null;
  indexing_status?: string;
  indexing_freshness?: string | null;
  summary: string;
  languages: string[];
  total_files: number;
  total_symbols: number;
  overview?: ConciseOverview | null;
  deep_analysis?: DeepAnalysis | null;
  verified_citations_count?: number;
}

export interface IndexingStatus {
  repository_id: number;
  full_name: string;
  status: 'not_indexed' | 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  indexed_commit_sha: string | null;
  total_chunks: number;
  error?: string | null;
  updated_at: string;
}

export interface EvidenceCitation {
  file_path: string;
  start_line: number;
  end_line: number;
  symbol_name: string | null;
  snippet: string;
  commit_sha: string;
  relevance_reason?: string | null;
}

export interface CodeQuestionResponse {
  repository_id: number;
  query: string;
  answer: string;
  supported_by_evidence: boolean;
  commit_sha: string | null;
  citations: EvidenceCitation[];
  clarification_prompt?: string | null;
}

export interface ReviewFinding {
  id: number;
  review_id: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category?: string | null;
  title: string;
  explanation: string;
  file_path: string;
  start_line: number;
  end_line: number;
  diff_line_reference?: string | null;
  why_problem: string;
  suggested_improvement: string;
  suggested_fix_snippet?: string | null;
  suggested_tests?: string | null;
  confidence: number;
  is_confirmed_problem: boolean;
  published_to_github: boolean;
  github_comment_id?: string | null;
  published_at?: string | null;
  created_at: string;
}

export interface PRReview {
  id: number;
  repository_id: number;
  pr_number: number;
  title: string;
  base_commit_sha: string;
  head_commit_sha: string;
  status: 'queued' | 'in_progress' | 'completed' | 'failed';
  summary?: string | null;
  error_message?: string | null;
  model_name?: string | null;
  prompt_version?: string | null;
  eval_version?: string | null;
  ci_check_published: boolean;
  findings: ReviewFinding[];
  created_at: string;
  updated_at: string;
}

export interface Node {
  id: string;
  label: string;
  file_path: string;
  type: string;
}

export interface Edge {
  source: string;
  target: string;
  type: string;
  line_number: number;
  evidence: string;
}

export interface RelationshipGraph {
  repository_id: number;
  commit_sha: string | null;
  nodes: Node[];
  edges: Edge[];
}

export interface AuditLogEntry {
  id: number;
  action_type: string;
  user_id: string;
  repo_full_name: string;
  pr_number: number | null;
  target_file: string | null;
  target_lines: string | null;
  payload_summary: string;
  status: string;
  previous_hash?: string | null;
  entry_hash?: string | null;
  model_name?: string | null;
  prompt_version?: string | null;
  index_commit_sha?: string | null;
  eval_version?: string | null;
  error_message: string | null;
  created_at: string;
}

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  github_id?: string | null;
  avatar_url?: string | null;
  organization_id: number;
  organization_name: string;
  organization_slug: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface HealthFileItem {
  file_path: string;
  filename: string;
  status: string;
  analysis_mode: string;
  category: string;
  exclusion_reason: string | null;
  is_secret: boolean;
  is_binary: boolean;
  is_safe_to_view_in_explorer: boolean;
  language_display: string;
  file_size_bytes: number;
}

export interface RepositoryHealthDashboard {
  repository_id: number;
  full_name: string;
  branch: string;
  indexed_commit_sha: string | null;
  remote_commit_sha: string | null;
  is_stale: boolean;
  indexing_status: string;
  indexing_progress: number;
  last_indexed_at: string | null;
  total_discovered_files: number;
  indexed_files_count: number;
  parser_aware_count: number;
  text_fallback_count: number;
  excluded_secrets_count: number;
  excluded_binaries_count: number;
  excluded_vendors_count: number;
  unsupported_or_failed_count: number;
  database_mode: string;
  database_vector_capabilities: string;
  files_summary: HealthFileItem[];
}

export interface AuditVerificationResult {
  is_valid: boolean;
  total_entries: number;
  tampered_entry_id: number | null;
  message: string;
}

export interface EvaluationMetrics {
  benchmark_version: string;
  total_test_cases: number;
  precision: number;
  recall: number;
  f1_score: number;
  false_positive_rate: number;
  usefulness_rate: number | null;
  total_feedbacks_recorded: number;
  summary_citation_accuracy?: number;
  summary_unsupported_claims?: number;
  summary_incorrect_claims?: number;
  summary_missing_facts?: number;
  evaluation_timestamp: string;
}

export interface RepositoryFileItem {
  id: number;
  file_path: string;
  filename: string;
  file_size: number;
  language: string;
  language_display: string;
  status: 'indexed' | 'fallback' | 'excluded' | 'pending' | 'failed';
  analysis_mode: 'parser_aware' | 'text_fallback' | 'excluded' | 'pending' | 'failed';
  exclusion_reason?: string | null;
  is_secret: boolean;
  is_binary: boolean;
  chunks_count: number;
}

export interface RepositoryTreeCoverage {
  total_files: number;
  parser_aware: number;
  fallback: number;
  excluded: number;
  pending: number;
  failed: number;
}

export interface RepositoryTreeResponse {
  repository_id: number;
  full_name: string;
  branch: string;
  commit_sha: string | null;
  indexing_status: string;
  indexing_progress: number;
  coverage: RepositoryTreeCoverage;
  files: RepositoryFileItem[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface FileContentResponse {
  repository_id: number;
  file_path: string;
  allowed: boolean;
  language?: string | null;
  language_display?: string | null;
  analysis_mode?: string | null;
  exclusion_reason?: string | null;
  is_secret: boolean;
  is_binary: boolean;
  content?: string | null;
  lines_count?: number | null;
  size_bytes?: number | null;
}

export interface OnboardingEntryPoint {
  file_path: string;
  symbol?: string | null;
  start_line: number;
  end_line: number;
  citation: string;
  language: string;
  reason: string;
  confirmed: boolean;
  status_label: string;
}

export interface OnboardingModule {
  module_name: string;
  file_path: string;
  language: string;
  start_line: number;
  end_line: number;
  citation: string;
  responsibility: string;
  symbols: string[];
  confirmed: boolean;
  status_label: string;
}

export interface OnboardingConnection {
  source_module: string;
  target_module: string;
  relationship_type: string;
  source_symbol: string;
  target_symbol: string;
  file_path: string;
  line_number: number;
  citation: string;
  evidence_snippet: string;
  confirmed: boolean;
  status_label: string;
}

export interface OnboardingModuleTest {
  module_path: string;
  has_tests: boolean;
  test_file?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  citation: string;
  test_cases: string[];
  status_label: string;
}

export interface RepositoryOnboarding {
  repository_id: number;
  full_name: string;
  branch: string;
  commit_sha?: string | null;
  indexing_status: string;
  overview_summary: string;
  entry_points: OnboardingEntryPoint[];
  modules: OnboardingModule[];
  module_connections: OnboardingConnection[];
  module_tests: OnboardingModuleTest[];
  total_modules: number;
  total_entry_points: number;
  unconfirmed_note: string;
}

export interface ChangedFileItem {
  file_path: string;
  old_path?: string | null;
  change_type: string;
  additions: number;
  deletions: number;
  symbols: {
    file_path: string;
    symbol_name: string;
    start_line: number;
    end_line: number;
    citation: string;
    language: string;
    analysis_mode: string;
    snippet: string;
  }[];
}

export interface DownstreamImpact {
  dependent_file: string;
  line_number: number;
  citation: string;
  relationship_type: string;
  caller_symbol: string;
  target_symbol: string;
  reason: string;
  evidence_snippet: string;
  status: string;
}

export interface AffectedTest {
  test_file: string;
  test_name: string;
  start_line: number;
  end_line: number;
  citation: string;
  relationship: string;
  confidence: string;
}

export interface UntracedArea {
  file_path: string;
  line_range: string;
  citation: string;
  indicator: string;
  uncertainty_reason: string;
  status: string;
}

export interface TestGapItem {
  file_path: string;
  symbol_name: string;
  citation: string;
  gap_category: string;
  gap_status: string;
  explanation: string;
  suggested_test: string;
  why_it_matters: string;
}

export interface PRImpactAnalysis {
  pr_number: number;
  repository_id: number;
  commit_sha?: string | null;
  changed_files_count: number;
  changed_files: ChangedFileItem[];
  downstream_impacts: DownstreamImpact[];
  affected_tests: AffectedTest[];
  untraced_areas: UntracedArea[];
  test_gaps: TestGapItem[];
  execution_policy: string;
  coverage_notice: string;
}

export interface FileDiffItem {
  path: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  old_path?: string | null;
  size_bytes: number;
  citation: string;
}

export interface CommitCompareData {
  repository_id: number;
  full_name: string;
  base: {
    ref_name: string;
    commit_sha: string;
    is_indexed: boolean;
    is_stale: boolean;
    indexed_chunks: number;
  };
  head: {
    ref_name: string;
    commit_sha: string;
    is_indexed: boolean;
    is_stale: boolean;
    indexed_chunks: number;
  };
  summary: {
    total_changed_files: number;
    added_count: number;
    modified_count: number;
    deleted_count: number;
    renamed_count: number;
  };
  files_changed: FileDiffItem[];
  architecture_diff: {
    added_modules: string[];
    removed_modules: string[];
    dependency_changes: { module: string; change: string; citation: string; status: string }[];
    architecture_shift_summary: string;
  };
  findings_diff: {
    has_comparable_reviews: boolean;
    head_review_id?: number | null;
    base_review_id?: number | null;
    new_findings: any[];
    resolved_findings: any[];
    existing_findings: any[];
    status_label: string;
  };
  status_notice: string;
}

export interface DependencyItem {
  name: string;
  declared_version: string;
  manifest_file: string;
  is_transitive: boolean | null;
  dependency_type: string;
  vulnerability_status: string;
  source: string;
  checked_at: string;
}

export interface DependencyInventoryData {
  repository_id: number;
  full_name: string;
  commit_sha?: string | null;
  scan_timestamp: string;
  manifest_files: string[];
  summary: {
    total_dependencies: number;
    direct_dependencies: number;
    transitive_dependencies: number;
    unconfirmed_dependencies: number;
  };
  dependencies: DependencyItem[];
  vulnerability_notice: string;
  verification_source: string;
  checked_at: string;
}

export interface RepositoryFeedbackItem {
  id: number;
  repository_id: number;
  branch?: string | null;
  commit_sha: string;
  target_type: 'finding' | 'answer';
  target_id: string;
  category?: string | null;
  is_useful: boolean;
  reason?: string | null;
  user_id?: string | null;
  created_at: string;
}

export interface TestedCommitInfo {
  repository_id: number;
  full_name: string;
  branch: string;
  indexed_commit_sha: string | null;
  indexing_status: string;
  is_stale: boolean;
  last_indexed_at: string | null;
}

export interface QualityReportData {
  evaluation_date: string;
  benchmark_version: string;
  sample_size: number;
  correct_repo_selection_pct: number;
  cross_repo_leakage_count: number;
  answer_correctness_pct: number;
  citation_accuracy_pct: number;
  indexing_failures_count: number;
  stale_indexes_count: number;
  tested_commits: TestedCommitInfo[];
  feedback_breakdown: Record<string, number>;
  failing_cases: any[];
  limitations: string[];
}



