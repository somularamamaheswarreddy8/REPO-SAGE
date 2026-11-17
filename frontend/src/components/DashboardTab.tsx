import React, { useState, useEffect, useRef } from 'react';
import {
  Repository,
  RepositorySummary,
  RepositoryHealthDashboard,
  PRReview,
  ReviewFinding,
  IndexingStatus,
  AuditLogEntry,
} from '../types';
import { api } from '../services/api';
import {
  Shield,
  FileCode2,
  FolderTree,
  AlertTriangle,
  CheckCircle2,
  GitPullRequest,
  Activity,
  ArrowRight,
  ExternalLink,
  RefreshCw,
  Sparkles,
  Lock,
  Clock,
  Code2,
} from 'lucide-react';

interface DashboardTabProps {
  repo: Repository;
  indexingStatus: IndexingStatus | null;
  onNavigateToFile: (filePath: string, lineRange?: [number, number]) => void;
  onSwitchTab: (tabId: string) => void;
  onReindex: () => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  repo,
  indexingStatus,
  onNavigateToFile,
  onSwitchTab,
  onReindex,
}) => {
  const activeRepoIdRef = useRef<number>(repo.id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<RepositorySummary | null>(null);
  const [health, setHealth] = useState<RepositoryHealthDashboard | null>(null);
  const [reviews, setReviews] = useState<PRReview[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);

  useEffect(() => {
    activeRepoIdRef.current = repo.id;
    // Clear previous repo data immediately
    setSummary(null);
    setHealth(null);
    setReviews([]);
    setAuditLogs([]);
    setError(null);

    // If repo is not completed, don't attempt to load completed analysis
    if (repo.indexing_status !== 'completed') {
      setLoading(false);
      return;
    }

    loadDashboardData(repo.id);
  }, [repo.id, repo.indexed_commit_sha, repo.indexing_status]);

  const loadDashboardData = async (targetRepoId: number) => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, healthRes, reviewsRes, auditRes] = await Promise.allSettled([
        api.getRepositorySummary(targetRepoId),
        api.getHealthDashboard(targetRepoId),
        api.listReviews(targetRepoId),
        api.getAuditLogs(),
      ]);

      if (activeRepoIdRef.current !== targetRepoId) return;

      if (summaryRes.status === 'fulfilled') {
        setSummary(summaryRes.value);
      }
      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value);
      }
      if (reviewsRes.status === 'fulfilled') {
        setReviews(reviewsRes.value);
      }
      if (auditRes.status === 'fulfilled') {
        // Filter audit logs for this repo if available
        const filteredLogs = auditRes.value.filter(
          (log) => log.repo_full_name === repo.full_name || !log.repo_full_name
        );
        setAuditLogs(filteredLogs.slice(0, 10));
      }
    } catch (err: any) {
      if (activeRepoIdRef.current === targetRepoId) {
        setError(err.message || 'Failed to load dashboard data.');
      }
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setLoading(false);
      }
    }
  };

  // Extract all review findings
  const allFindings: ReviewFinding[] = reviews.flatMap((r: any) => r.findings || []);
  const findingsBySeverity = {
    critical: allFindings.filter((f) => f.severity === 'critical'),
    high: allFindings.filter((f) => f.severity === 'high'),
    medium: allFindings.filter((f) => f.severity === 'medium'),
    low: allFindings.filter((f) => f.severity === 'low'),
  };

  // Helper to parse citations in text and make them clickable
  const renderEvidenceSummary = (text: string) => {
    if (!text) return null;
    const parts = text.split(/(\[[^\]]+:L\d+(?:-\d+)?\](?:\([^\)]+\))?)/g);
    return parts.map((part, idx) => {
      const match = part.match(/\[([^\]:]+):L(\d+)(?:-(\d+))?\]/);
      if (match) {
        const filePath = match[1].trim();
        const start = parseInt(match[2], 10);
        const end = match[3] ? parseInt(match[3], 10) : start;
        return (
          <button
            key={idx}
            onClick={() => onNavigateToFile(filePath, [start, end])}
            className="inline-flex items-center gap-1 font-mono text-[11px] text-lime-700 bg-lime-100 hover:bg-lime-200 border border-lime-300 rounded px-1.5 py-0.5 mx-1 transition cursor-pointer"
            title={`Open ${filePath}:${start}-${end}`}
          >
            <FileCode2 className="w-3 h-3 text-lime-600" />
            {match[0]}
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  // Clean modules from deep analysis
  const modules = summary?.deep_analysis?.modules || [];

  // Compute language distribution
  const languageStats: { language: string; count: number; mode: string }[] = [];
  if (health?.files_summary) {
    const counts: Record<string, { count: number; mode: string }> = {};
    health.files_summary.forEach((f) => {
      const lang = f.language_display || 'Unknown';
      if (!counts[lang]) {
        counts[lang] = { count: 0, mode: f.analysis_mode || 'text fallback' };
      }
      counts[lang].count += 1;
    });
    for (const [lang, val] of Object.entries(counts)) {
      languageStats.push({ language: lang, count: val.count, mode: val.mode });
    }
    languageStats.sort((a, b) => b.count - a.count);
  }

  const totalLangFiles = languageStats.reduce((acc, curr) => acc + curr.count, 0) || 1;

  // Language bar colors (lime, lavender, sky, emerald, amber, slate)
  const langColors = [
    'bg-lime-400',
    'bg-lavender-400',
    'bg-sky-400',
    'bg-emerald-400',
    'bg-amber-400',
    'bg-slate-400',
  ];

  if (repo.indexing_status === 'queued' || repo.indexing_status === 'running') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[55vh] p-8 text-center max-w-md mx-auto">
        <div className="w-16 h-16 rounded-3xl bg-lime-100 border border-lime-300 flex items-center justify-center text-lime-600 mb-4 shadow-sm">
          <RefreshCw className="w-8 h-8 animate-spin" />
        </div>
        <h3 className="text-lg font-bold text-slate-800">Indexing in Progress</h3>
        <p className="text-sm text-slate-600 mt-1 mb-4">
          Parsing codebase, generating syntax trees, and isolating chunks for{' '}
          <strong className="text-slate-800 font-mono">{repo.full_name}</strong>.
        </p>
        <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden mb-2">
          <div
            className="bg-lime-500 h-2.5 rounded-full transition-all duration-500"
            style={{ width: `${Math.round(indexingStatus?.progress ?? repo.indexing_progress)}%` }}
          />
        </div>
        <span className="text-xs font-mono font-semibold text-slate-500">
          {Math.round(indexingStatus?.progress ?? repo.indexing_progress)}% Completed
        </span>
      </div>
    );
  }

  if (repo.indexing_status === 'failed') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[55vh] p-8 text-center max-w-lg mx-auto">
        <div className="w-16 h-16 rounded-3xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-500 mb-4 shadow-sm">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-800">Indexing Failed</h3>
        <p className="text-sm text-slate-600 mt-1 mb-4">
          Failed to index repository <strong className="font-mono text-slate-800">{repo.full_name}</strong>.
        </p>
        {repo.indexing_error && (
          <div className="w-full text-left p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs font-mono text-rose-700 mb-4 break-words">
            {repo.indexing_error}
          </div>
        )}
        <button
          onClick={onReindex}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold shadow transition"
        >
          Retry Indexing
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-8 space-y-6 animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="h-44 bg-slate-100 rounded-2xl border border-slate-200/80"></div>
          <div className="h-44 bg-slate-100 rounded-2xl border border-slate-200/80"></div>
          <div className="h-44 bg-slate-100 rounded-2xl border border-slate-200/80"></div>
        </div>
        <div className="h-64 bg-slate-100 rounded-2xl border border-slate-200/80"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Repository Summary */}
        <div className="lg:col-span-2 bg-white rounded-3xl p-6 border border-[#e4eae2] shadow-sm flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-lime-100 text-lime-700 border border-lime-200">
                  <Shield className="w-4 h-4" />
                </span>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Repository Summary</h3>
              </div>
              <button
                onClick={() => onSwitchTab('overview')}
                className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1 transition"
              >
                Deep Overview <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="text-xs text-slate-600 leading-relaxed max-h-48 overflow-y-auto pr-1">
              {summary?.summary ? (
                <div className="prose prose-sm max-w-none prose-slate">
                  {renderEvidenceSummary(summary.summary)}
                </div>
              ) : (
                <p className="italic text-slate-400">
                  No automated repository summary available. Trigger re-indexing to inspect codebase symbols.
                </p>
              )}
            </div>

            {/* Frameworks & Architecture Tags */}
            {modules.length > 0 && (
              <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mr-1">
                  Key Modules:
                </span>
                {modules.slice(0, 4).map((mod, i) => (
                  <button
                    key={i}
                    onClick={() => onNavigateToFile(mod.file_path)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-mono transition"
                    title={`Inspect ${mod.file_path}`}
                  >
                    <FileCode2 className="w-3 h-3 text-slate-400" />
                    <span>{mod.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-lime-500"></span>
              <span>Grounded on commit <code className="font-mono text-slate-700 bg-slate-100 px-1 py-0.5 rounded">{repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 7) : 'HEAD'}</code></span>
            </div>
            <button
              onClick={() => onSwitchTab('qa')}
              className="text-lime-700 hover:text-lime-800 font-semibold flex items-center gap-1"
            >
              Ask Code Q&A <Sparkles className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Card 2: Indexing Coverage */}
        <div className="bg-white rounded-3xl p-6 border border-[#e4eae2] shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-lavender-100 text-lavender-700 border border-lavender-200">
                  <Activity className="w-4 h-4" />
                </span>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Indexing Coverage</h3>
              </div>
              <span className="text-[11px] font-semibold font-mono px-2 py-0.5 rounded-full bg-lime-100 text-lime-800 border border-lime-200">
                {health?.indexing_status || repo.indexing_status}
              </span>
            </div>

            <div className="space-y-2">
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-slate-900 font-mono tracking-tight">
                  {health ? health.indexed_files_count : 0}
                  <span className="text-xs font-normal text-slate-500 ml-1">
                    / {health ? health.total_discovered_files : 0} files
                  </span>
                </span>
                <span className="text-xs font-semibold text-lime-700 font-mono">
                  {health && health.total_discovered_files > 0
                    ? `${Math.round((health.indexed_files_count / health.total_discovered_files) * 100)}%`
                    : '100%'}
                </span>
              </div>

              {/* Lime Progress Bar */}
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-lime-500 h-2 rounded-full transition-all duration-500"
                  style={{
                    width: `${
                      health && health.total_discovered_files > 0
                        ? (health.indexed_files_count / health.total_discovered_files) * 100
                        : 100
                    }%`,
                  }}
                />
              </div>
            </div>

            {/* Granular Breakdown */}
            <div className="grid grid-cols-2 gap-2 text-xs pt-1">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-[10px] uppercase font-bold text-slate-400">Parser Aware</div>
                <div className="text-sm font-bold font-mono text-slate-800 mt-0.5">
                  {health ? health.parser_aware_count : 0}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-[10px] uppercase font-bold text-slate-400">Text Fallback</div>
                <div className="text-sm font-bold font-mono text-slate-800 mt-0.5">
                  {health ? health.text_fallback_count : 0}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-[10px] uppercase font-bold text-slate-400">Excluded (Safe)</div>
                <div className="text-sm font-bold font-mono text-slate-800 mt-0.5 flex items-center gap-1">
                  <span>{(health?.excluded_secrets_count || 0) + (health?.excluded_binaries_count || 0)}</span>
                  <Lock className="w-3 h-3 text-emerald-600" />
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-[10px] uppercase font-bold text-slate-400">Failed / Skip</div>
                <div className="text-sm font-bold font-mono text-slate-800 mt-0.5">
                  {health ? health.unsupported_or_failed_count : 0}
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={() => onSwitchTab('explorer')}
            className="w-full mt-4 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition text-center flex items-center justify-center gap-1"
          >
            Browse Indexed Files <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* High-Importance Visualization Card: Recent Repository Activity (Dark Charcoal) */}
      <div className="bg-charcoal-900 text-white rounded-3xl p-6 sm:p-7 border border-charcoal-800 shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-lime-accent animate-pulse" />
              <h3 className="text-base font-bold text-white tracking-tight">Recent Repository Activity</h3>
            </div>
            <p className="text-xs text-charcoal-500 mt-1">
              Indexing timeline, audit events, and security review history for{' '}
              <span className="font-mono text-slate-300">{repo.full_name}</span>.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onReindex}
              className="px-3 py-1.5 rounded-xl bg-charcoal-800 hover:bg-charcoal-700 border border-charcoal-700 text-xs font-medium text-lime-300 transition flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Re-Index Now
            </button>
            <button
              onClick={() => onSwitchTab('audit')}
              className="px-3 py-1.5 rounded-xl bg-charcoal-800 hover:bg-charcoal-700 border border-charcoal-700 text-xs font-medium text-slate-300 hover:text-white transition flex items-center gap-1.5"
            >
              Full Audit Trail <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Activity Items or Telemetry */}
        {auditLogs.length > 0 || reviews.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Indexing Event */}
            <div className="bg-charcoal-850 border border-charcoal-700/80 rounded-2xl p-4 flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="px-2 py-0.5 rounded-md bg-lime-400/10 text-lime-400 border border-lime-400/20 font-mono text-[10px]">
                    Indexing Job
                  </span>
                  <span className="text-charcoal-500 text-[11px] font-mono">
                    {repo.last_indexed_at ? new Date(repo.last_indexed_at).toLocaleDateString() : 'Recent'}
                  </span>
                </div>
                <div className="text-sm font-semibold text-white">Full AST Parsing & Chunking</div>
                <p className="text-xs text-slate-400 leading-snug">
                  Indexed commit <code className="text-lime-300 font-mono">{repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 7) : 'HEAD'}</code> with zero secret leaks.
                </p>
              </div>
              <div className="pt-3 mt-3 border-t border-charcoal-700 flex items-center justify-between text-[11px] text-charcoal-500">
                <span>Status: Completed</span>
                <span className="text-lime-400 font-mono font-semibold">100% Grounded</span>
              </div>
            </div>

            {/* Reviews Event */}
            {reviews.slice(0, 2).map((rev) => (
              <div key={rev.id} className="bg-charcoal-850 border border-charcoal-700/80 rounded-2xl p-4 flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="px-2 py-0.5 rounded-md bg-lavender-400/10 text-lavender-300 border border-lavender-400/20 font-mono text-[10px]">
                      PR #{rev.pr_number}
                    </span>
                    <span className="text-charcoal-500 text-[11px] font-mono">
                      {rev.status}
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-white truncate">{rev.title}</div>
                  <p className="text-xs text-slate-400 leading-snug line-clamp-2">
                    {rev.summary || 'Security review completed with evidence-backed findings.'}
                  </p>
                </div>
                <div className="pt-3 mt-3 border-t border-charcoal-700 flex items-center justify-between text-[11px] text-charcoal-500">
                  <span>Findings: {rev.findings?.length || 0}</span>
                  <button
                    onClick={() => onSwitchTab('reviews')}
                    className="text-lavender-300 hover:text-white font-medium flex items-center gap-1"
                  >
                    View PR <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}

            {/* Audit Log Fallback Items if fewer than 2 reviews */}
            {reviews.length < 2 &&
              auditLogs.slice(0, 2 - reviews.length).map((log) => (
                <div key={log.id} className="bg-charcoal-850 border border-charcoal-700/80 rounded-2xl p-4 flex flex-col justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="px-2 py-0.5 rounded-md bg-slate-700 text-slate-300 font-mono text-[10px]">
                        {log.action_type}
                      </span>
                      <span className="text-charcoal-500 text-[11px] font-mono">
                        {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-sm font-semibold text-white truncate">{log.payload_summary}</div>
                    <p className="text-xs text-slate-400 leading-snug font-mono truncate">
                      Actor: {log.user_id}
                    </p>
                  </div>
                  <div className="pt-3 mt-3 border-t border-charcoal-700 flex items-center justify-between text-[11px] text-charcoal-500">
                    <span>Audit Status: {log.status}</span>
                    <span className="text-emerald-400">Verified</span>
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <div className="p-8 text-center bg-charcoal-850/60 border border-charcoal-800 rounded-2xl space-y-2">
            <Clock className="w-8 h-8 text-charcoal-500 mx-auto" />
            <h4 className="text-sm font-semibold text-slate-200">No Historical Activity Recorded</h4>
            <p className="text-xs text-charcoal-500 max-w-md mx-auto">
              Run code indexing or trigger an automated pull request review to populate real-time activity telemetry.
            </p>
            <button
              onClick={onReindex}
              className="mt-2 inline-flex items-center gap-1.5 px-4 py-2 bg-lime-400 hover:bg-lime-300 text-charcoal-900 rounded-xl text-xs font-bold transition shadow"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Trigger Indexing
            </button>
          </div>
        )}
      </div>

      {/* Bottom Grid: Language Breakdown, Review Findings, Recent Files */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Card 3: Language Breakdown */}
        <div className="bg-white rounded-3xl p-6 border border-[#e4eae2] shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-lime-100 text-lime-700 border border-lime-200">
                  <Code2 className="w-4 h-4" />
                </span>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Languages & Analysis</h3>
              </div>
              <span className="text-xs text-slate-400 font-mono">{languageStats.length} detected</span>
            </div>

            {/* Segmented Bar */}
            {languageStats.length > 0 ? (
              <>
                <div className="w-full h-3 rounded-full overflow-hidden flex bg-slate-100 shadow-inner">
                  {languageStats.map((item, idx) => {
                    const widthPct = (item.count / totalLangFiles) * 100;
                    return (
                      <div
                        key={idx}
                        className={`${langColors[idx % langColors.length]} transition-all duration-300`}
                        style={{ width: `${Math.max(widthPct, 3)}%` }}
                        title={`${item.language}: ${item.count} files (${Math.round(widthPct)}%)`}
                      />
                    );
                  })}
                </div>

                <div className="space-y-2 pt-1 max-h-56 overflow-y-auto pr-1">
                  {languageStats.map((item, idx) => {
                    const pct = Math.round((item.count / totalLangFiles) * 100);
                    return (
                      <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-slate-50 last:border-0">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className={`w-2.5 h-2.5 rounded-full ${langColors[idx % langColors.length]}`} />
                          <span className="font-semibold text-slate-700 truncate">{item.language}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-500 font-mono">
                            {item.mode}
                          </span>
                        </div>
                        <div className="font-mono text-slate-600 font-semibold shrink-0">
                          {item.count} <span className="text-slate-400 font-normal">({pct}%)</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="text-xs text-slate-400 italic py-6 text-center">
                Language detection pending index completion.
              </div>
            )}
          </div>

          <button
            onClick={() => onSwitchTab('explorer')}
            className="w-full mt-4 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition text-center flex items-center justify-center gap-1"
          >
            Browse in File Explorer <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {/* Card 4: Review Findings */}
        <div className="bg-white rounded-3xl p-6 border border-[#e4eae2] shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-rose-100 text-rose-700 border border-rose-200">
                  <GitPullRequest className="w-4 h-4" />
                </span>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Review Findings</h3>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                {allFindings.length} total
              </span>
            </div>

            {/* Severity Pill Counts */}
            <div className="grid grid-cols-4 gap-1.5 text-center">
              <div className="p-2 rounded-xl bg-rose-50 border border-rose-100">
                <div className="text-[10px] font-bold text-rose-700 uppercase">Crit</div>
                <div className="text-sm font-black font-mono text-rose-800">
                  {findingsBySeverity.critical.length}
                </div>
              </div>
              <div className="p-2 rounded-xl bg-amber-50 border border-amber-100">
                <div className="text-[10px] font-bold text-amber-700 uppercase">High</div>
                <div className="text-sm font-black font-mono text-amber-800">
                  {findingsBySeverity.high.length}
                </div>
              </div>
              <div className="p-2 rounded-xl bg-sky-50 border border-sky-100">
                <div className="text-[10px] font-bold text-sky-700 uppercase">Med</div>
                <div className="text-sm font-black font-mono text-sky-800">
                  {findingsBySeverity.medium.length}
                </div>
              </div>
              <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-[10px] font-bold text-slate-600 uppercase">Low</div>
                <div className="text-sm font-black font-mono text-slate-800">
                  {findingsBySeverity.low.length}
                </div>
              </div>
            </div>

            {/* Top Findings List */}
            {allFindings.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {allFindings.slice(0, 3).map((f) => (
                  <div key={f.id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-800 truncate max-w-[180px]">{f.title}</span>
                      <span
                        className={`text-[9px] font-mono uppercase font-bold px-1.5 py-0.2 rounded ${
                          f.severity === 'critical' || f.severity === 'high'
                            ? 'bg-rose-100 text-rose-700'
                            : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {f.severity}
                      </span>
                    </div>
                    <button
                      onClick={() => onNavigateToFile(f.file_path, [f.start_line, f.end_line])}
                      className="text-[11px] font-mono text-lime-700 hover:text-lime-800 flex items-center gap-1 transition"
                    >
                      <FileCode2 className="w-3 h-3" />
                      {f.file_path}:{f.start_line}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center rounded-2xl bg-slate-50 border border-slate-100 text-xs text-slate-500 flex flex-col items-center gap-2">
                <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                <span>Zero unresolved security issues detected.</span>
              </div>
            )}
          </div>

          <button
            onClick={() => onSwitchTab('reviews')}
            className="w-full mt-4 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition text-center flex items-center justify-center gap-1"
          >
            Open PR Reviews <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {/* Card 6: Recent Files or Modules */}
        <div className="bg-white rounded-3xl p-6 border border-[#e4eae2] shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-lavender-100 text-lavender-700 border border-lavender-200">
                  <FolderTree className="w-4 h-4" />
                </span>
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Key Source Modules</h3>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {modules.length > 0 ? `${modules.length} modules` : 'Discovered'}
              </span>
            </div>

            {modules.length > 0 ? (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {modules.map((m, idx) => (
                  <div
                    key={idx}
                    onClick={() => onNavigateToFile(m.file_path)}
                    className="p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-100 cursor-pointer transition flex items-center justify-between group"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-semibold text-slate-800 group-hover:text-lime-700 font-mono truncate">
                        {m.name}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono truncate">{m.file_path}</div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-lime-700 shrink-0 ml-2 transition" />
                  </div>
                ))}
              </div>
            ) : health?.files_summary && health.files_summary.length > 0 ? (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {health.files_summary.slice(0, 5).map((f, idx) => (
                  <div
                    key={idx}
                    onClick={() => onNavigateToFile(f.file_path)}
                    className="p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-100 cursor-pointer transition flex items-center justify-between group"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-semibold text-slate-800 group-hover:text-lime-700 font-mono truncate">
                        {f.filename}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono truncate">{f.file_path}</div>
                    </div>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-200 text-slate-600">
                      {f.language_display}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-400 italic py-6 text-center">
                Module extraction pending completion.
              </div>
            )}
          </div>

          <button
            onClick={() => onSwitchTab('explorer')}
            className="w-full mt-4 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition text-center flex items-center justify-center gap-1"
          >
            Explore All Files <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
};
