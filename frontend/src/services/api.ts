import {
  Repository,
  RepositorySettings,
  RepositorySummary,
  IndexingStatus,
  CodeQuestionResponse,
  PRReview,
  RelationshipGraph,
  AuditLogEntry,
  EvaluationMetrics,
  RepositoryTreeResponse,
  FileContentResponse,
  UserProfile,
  LoginResponse,
  RepositoryHealthDashboard,
  AuditVerificationResult,
  RepositoryOnboarding,
  PRImpactAnalysis,
  CommitCompareData,
  DependencyInventoryData,
  RepositoryFeedbackItem,
  QualityReportData,
} from '../types';

const API_BASE = '/api/v1';

let authToken: string | null = localStorage.getItem('reposage_token');

export function getStoredToken(): string | null {
  return authToken;
}

export function setStoredToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('reposage_token', token);
  } else {
    localStorage.removeItem('reposage_token');
  }
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMessage = `HTTP error ${res.status}`;
    try {
      const errData = await res.json();
      errMessage = errData.detail || errMessage;
    } catch {
      // ignore
    }
    throw new Error(errMessage);
  }
  return res.json();
}

export const api = {
  // Authentication & Roles
  async login(username: string, password: string): Promise<LoginResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await handleResponse<LoginResponse>(res);
    setStoredToken(data.access_token);
    return data;
  },

  async getCurrentUser(): Promise<UserProfile> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<UserProfile>(res);
  },

  // Repositories
  async getRepositories(): Promise<Repository[]> {
    const res = await fetch(`${API_BASE}/repositories`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<Repository[]>(res);
  },

  async connectRepository(fullName: string, isDemo: boolean = false): Promise<Repository> {
    const res = await fetch(`${API_BASE}/repositories`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ full_name: fullName, is_demo: isDemo }),
    });
    return handleResponse<Repository>(res);
  },

  async getRepository(id: number): Promise<Repository> {
    const res = await fetch(`${API_BASE}/repositories/${id}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<Repository>(res);
  },

  async disconnectRepository(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/repositories/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to disconnect repository');
  },

  async getRepositorySummary(id: number): Promise<RepositorySummary> {
    const res = await fetch(`${API_BASE}/repositories/${id}/summary`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<RepositorySummary>(res);
  },

  async getRepositoryTree(
    id: number,
    params?: { search?: string; language?: string; status?: string; limit?: number; offset?: number }
  ): Promise<RepositoryTreeResponse> {
    const query = new URLSearchParams();
    if (params?.search) query.append('search', params.search);
    if (params?.language) query.append('language', params.language);
    if (params?.status) query.append('status', params.status);
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));

    const res = await fetch(`${API_BASE}/repositories/${id}/tree?${query.toString()}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<RepositoryTreeResponse>(res);
  },

  async getFileContent(id: number, filePath: string): Promise<FileContentResponse> {
    const query = new URLSearchParams({ path: filePath });
    const res = await fetch(`${API_BASE}/repositories/${id}/files/content?${query.toString()}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<FileContentResponse>(res);
  },

  async getHealthDashboard(id: number): Promise<RepositoryHealthDashboard> {
    const res = await fetch(`${API_BASE}/repositories/${id}/health-dashboard`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<RepositoryHealthDashboard>(res);
  },

  async getRepositorySettings(id: number): Promise<RepositorySettings> {
    const res = await fetch(`${API_BASE}/repositories/${id}/settings`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<RepositorySettings>(res);
  },

  async updateRepositorySettings(
    id: number,
    settings: Partial<RepositorySettings>
  ): Promise<RepositorySettings> {
    const res = await fetch(`${API_BASE}/repositories/${id}/settings`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(settings),
    });
    return handleResponse<RepositorySettings>(res);
  },

  // Indexing
  async triggerIndexing(id: number, force: boolean = false): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/repositories/${id}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_full_reindex: force }),
    });
    return handleResponse<{ message: string }>(res);
  },

  async getIndexingStatus(id: number): Promise<IndexingStatus> {
    const res = await fetch(`${API_BASE}/repositories/${id}/index/status`);
    return handleResponse<IndexingStatus>(res);
  },

  // Code Q&A
  async askQuestion(id: number, query: string, maxCitations: number = 5): Promise<CodeQuestionResponse> {
    const res = await fetch(`${API_BASE}/repositories/${id}/qa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, max_citations: maxCitations }),
    });
    return handleResponse<CodeQuestionResponse>(res);
  },

  // Code Relationships
  async getRelationshipGraph(id: number): Promise<RelationshipGraph> {
    const res = await fetch(`${API_BASE}/repositories/${id}/relationships/graph`);
    return handleResponse<RelationshipGraph>(res);
  },

  // PR Reviews
  async listReviews(id: number): Promise<PRReview[]> {
    const res = await fetch(`${API_BASE}/repositories/${id}/reviews`);
    return handleResponse<PRReview[]>(res);
  },

  async createReview(
    id: number,
    prNumber: number,
    title?: string,
    customDiff?: string
  ): Promise<PRReview> {
    const res = await fetch(`${API_BASE}/repositories/${id}/reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pr_number: prNumber,
        title,
        custom_diff: customDiff,
      }),
    });
    return handleResponse<PRReview>(res);
  },

  async getReview(id: number, reviewId: number): Promise<PRReview> {
    const res = await fetch(`${API_BASE}/repositories/${id}/reviews/${reviewId}`);
    return handleResponse<PRReview>(res);
  },

  async publishComments(
    id: number,
    reviewId: number,
    findingIds: number[],
    userIdentifier: string = 'local_developer'
  ): Promise<{ published_count: number; message: string }> {
    const res = await fetch(`${API_BASE}/repositories/${id}/reviews/${reviewId}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        finding_ids: findingIds,
        explicit_user_approval: true,
        user_identifier: userIdentifier,
      }),
    });
    return handleResponse<{ published_count: number; message: string }>(res);
  },

  async publishCICheck(id: number, reviewId: number): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/repositories/${id}/reviews/${reviewId}/ci-check`, {
      method: 'POST',
    });
    return handleResponse<{ message: string }>(res);
  },

  // Feedback
  async submitFeedback(findingId: number, isUseful: boolean, reason?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/findings/${findingId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_useful: isUseful, reason }),
    });
    await handleResponse(res);
  },

  async getEvaluationMetrics(): Promise<EvaluationMetrics> {
    const res = await fetch(`${API_BASE}/evaluation/metrics`);
    return handleResponse<EvaluationMetrics>(res);
  },

  async exportReview(
    id: number,
    reviewId: number,
    format: 'markdown' | 'json' | 'sarif' = 'markdown'
  ): Promise<string> {
    const res = await fetch(`${API_BASE}/repositories/${id}/reviews/${reviewId}/export?format=${format}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error(`Export failed with status ${res.status}`);
    return res.text();
  },

  // Audit Log
  async getAuditLogs(): Promise<AuditLogEntry[]> {
    const res = await fetch(`${API_BASE}/audit`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<AuditLogEntry[]>(res);
  },

  async verifyAuditTrail(): Promise<AuditVerificationResult> {
    const res = await fetch(`${API_BASE}/audit/verify`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<AuditVerificationResult>(res);
  },

  // Onboarding Guide ("Start here" view)
  async getOnboardingGuide(repoId: number): Promise<RepositoryOnboarding> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/onboarding`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<RepositoryOnboarding>(res);
  },

  // PR Change Impact Analysis & Test-Gap Advisor
  async getPRImpact(repoId: number, reviewId: number): Promise<PRImpactAnalysis> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/reviews/${reviewId}/impact`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<PRImpactAnalysis>(res);
  },

  // Commit and Branch Comparison
  async compareCommits(repoId: number, base: string, head: string): Promise<CommitCompareData> {
    const res = await fetch(
      `${API_BASE}/repositories/${repoId}/compare?base=${encodeURIComponent(base)}&head=${encodeURIComponent(head)}`,
      { headers: getAuthHeaders() }
    );
    return handleResponse<CommitCompareData>(res);
  },

  // Dependency Inventory
  async getDependencies(repoId: number): Promise<DependencyInventoryData> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/dependencies`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<DependencyInventoryData>(res);
  },

  // Repository Feedback Controls
  async submitRepositoryFeedback(
    repoId: number,
    payload: {
      branch?: string;
      commit_sha: string;
      target_type: 'finding' | 'answer';
      target_id: string;
      category?: string;
      is_useful: boolean;
      reason?: string;
    }
  ): Promise<RepositoryFeedbackItem> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/feedback`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    return handleResponse<RepositoryFeedbackItem>(res);
  },

  async getRepositoryFeedback(repoId: number): Promise<RepositoryFeedbackItem[]> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/feedback`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<RepositoryFeedbackItem[]>(res);
  },

  // Accuracy & Quality Dashboard Evaluation
  async getQualityReport(): Promise<QualityReportData> {
    const res = await fetch(`${API_BASE}/evaluation/quality-report`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<QualityReportData>(res);
  },

  async runQABenchmark(): Promise<QualityReportData> {
    const res = await fetch(`${API_BASE}/evaluation/qa-benchmark/run`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse<QualityReportData>(res);
  },
};
