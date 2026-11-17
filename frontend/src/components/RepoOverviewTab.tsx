import React, { useEffect, useState, useRef } from 'react';
import {
  BookOpen,
  Code,
  FileText,
  Layers,
  RefreshCw,
  ShieldCheck,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Database,
  Terminal,
  Server,
  Workflow,
  AlertCircle,
  GitBranch,
  GitCommit,
  CheckCircle2,
  Clock,
  Cpu,
  Monitor,
  ArrowRight
} from 'lucide-react';
import { Repository, RepositorySummary, IndexingStatus, ProfileEvidenceCitation } from '../types';
import { api } from '../services/api';
import { RepositoryContextBar } from './RepositoryContextBar';

interface RepoOverviewTabProps {
  repo: Repository;
  onRefresh: () => void;
  indexingStatus?: IndexingStatus | null;
  onNavigateToFile?: (path: string, lineRange?: [number, number]) => void;
}

export const RepoOverviewTab: React.FC<RepoOverviewTabProps> = ({ repo, onRefresh, indexingStatus, onNavigateToFile }) => {
  const [summary, setSummary] = useState<RepositorySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [indexing, setIndexing] = useState(false);
  const [showDeepAnalysis, setShowDeepAnalysis] = useState(true);
  const [selectedCitation, setSelectedCitation] = useState<ProfileEvidenceCitation | null>(null);

  const activeRepoIdRef = useRef<number>(repo.id);

  useEffect(() => {
    activeRepoIdRef.current = repo.id;
    // Clear previous repository data immediately on repo change
    setSummary(null);
    setSelectedCitation(null);
    setSummaryError(null);

    if (repo.indexing_status !== 'completed') {
      setLoading(false);
      return;
    }

    loadSummary();
  }, [repo.id, repo.indexing_status, indexingStatus?.status]);

  const loadSummary = async () => {
    const targetRepoId = repo.id;
    try {
      setLoading(true);
      setSummaryError(null);
      setSummary(null);
      const data = await api.getRepositorySummary(targetRepoId);
      // Ignore if user switched repository while request was in-flight
      if (activeRepoIdRef.current !== targetRepoId) return;
      setSummary(data);
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setSummaryError(err.message || 'Failed to load summary');
      setSummary(null);
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setLoading(false);
      }
    }
  };

  const handleIndex = async (force: boolean = false) => {
    try {
      setIndexing(true);
      await api.triggerIndexing(repo.id, force);
      onRefresh();
    } catch (err: any) {
      alert(`Indexing trigger error: ${err.message}`);
    } finally {
      setIndexing(false);
    }
  };

  const isCompleted =
    repo.indexing_status === 'completed' &&
    !loading &&
    !summaryError &&
    summary !== null &&
    summary.repository_id === repo.id;

  return (
    <div className="space-y-6">
      {/* Repository Context Bar */}
      <RepositoryContextBar repo={repo} indexingStatus={indexingStatus} />

      {/* Staleness Warning Banner */}
      {repo.is_stale && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start gap-3 text-amber-300">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-400" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-amber-200">Stale Repository Index</h4>
            <p className="text-xs leading-relaxed text-amber-300/90">
              The remote branch has newer commits than your indexed commit ({repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 7) : 'None'}).
              This architectural summary was compiled against a prior commit. Re-index to inspect the latest code.
            </p>
          </div>
        </div>
      )}

      {/* Active Repository Identity Banner */}
      <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              {repo.full_name}
            </h2>
            {repo.is_demo && (
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-medium">
                Demo Repository
              </span>
            )}
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${
                repo.indexing_status === 'completed'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : repo.indexing_status === 'failed'
                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  : 'bg-sky-500/10 text-sky-400 border-sky-500/20'
              }`}
            >
              Status: {repo.indexing_status.toUpperCase()}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
            <span className="flex items-center gap-1.5 font-mono text-slate-300">
              <GitBranch className="w-3.5 h-3.5 text-slate-400" />
              Branch: {repo.default_branch}
            </span>
            <span className="flex items-center gap-1.5 font-mono text-slate-300">
              <GitCommit className="w-3.5 h-3.5 text-slate-400" />
              Commit: {repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 10) : 'Not indexed'}
            </span>
            {summary?.indexing_freshness && (
              <span className="flex items-center gap-1 text-slate-400">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                Freshness: {new Date(summary.indexing_freshness).toLocaleTimeString()}
              </span>
            )}
            {summary?.verified_citations_count ? (
              <span className="flex items-center gap-1 text-emerald-400 font-medium bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                <ShieldCheck className="w-3.5 h-3.5" />
                {summary.verified_citations_count} Grounded Code Citations
              </span>
            ) : null}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleIndex(true)}
            disabled={indexing || indexingStatus?.status === 'running' || repo.indexing_status === 'running'}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition shadow disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${
                indexing || indexingStatus?.status === 'running' || repo.indexing_status === 'running'
                  ? 'animate-spin'
                  : ''
              }`}
            />
            {repo.indexing_status === 'running' ? 'Indexing...' : 'Re-index Repository'}
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="p-12 rounded-xl bg-slate-800/30 border border-slate-700/50 flex flex-col items-center justify-center gap-3 text-slate-300 text-sm text-center">
          <RefreshCw className="w-7 h-7 animate-spin text-emerald-400" />
          <div>
            <p className="font-semibold text-white">Loading Overview for {repo.full_name}…</p>
            <p className="text-xs text-slate-400 mt-1">Verifying repository files and building grounded architectural profile</p>
          </div>
        </div>
      )}

      {/* Incomplete or Failed Indexing Notice */}
      {!loading && !isCompleted && (
        <div className="p-5 rounded-xl bg-amber-950/20 border border-amber-600/30 text-amber-200 space-y-3">
          <div className="flex items-center gap-2 font-semibold text-base text-amber-300">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
            Repository Analysis Unavailable: Indexing Required
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">
            {summaryError ||
              (repo.indexing_status === 'failed'
                ? `Indexing failed: ${repo.indexing_error || 'Internal fetch error'}`
                : `Repository indexing status is '${repo.indexing_status}' (${repo.indexing_progress}%). Please complete repository indexing before viewing architectural summaries or performing grounded code questions.`)}
          </p>
          <div className="pt-2">
            <button
              onClick={() => handleIndex(true)}
              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium transition shadow flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Start / Retry Indexing Now
            </button>
          </div>
        </div>
      )}

      {/* Grounded Overview & Analysis View (When Completed) */}
      {isCompleted && (
        <>
          {/* Quick Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{summary?.total_files ?? '--'}</div>
                <div className="text-xs text-slate-400">Indexed Files</div>
              </div>
            </div>

            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Code className="w-5 h-5" />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">{summary?.total_symbols ?? '--'}</div>
                <div className="text-xs text-slate-400">Symbols Extracted</div>
              </div>
            </div>

            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <div className="text-2xl font-bold text-emerald-400">
                  {summary?.verified_citations_count ?? 0}
                </div>
                <div className="text-xs text-slate-400">Verified Citations</div>
              </div>
            </div>

            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Layers className="w-5 h-5" />
              </div>
              <div className="truncate">
                <div className="text-sm font-semibold text-white truncate">
                  {summary?.languages?.join(', ') || 'Source Code'}
                </div>
                <div className="text-xs text-slate-400">Verified Languages</div>
              </div>
            </div>
          </div>

          {/* Visual System Architecture Diagram */}
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-5">
            <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-100 font-bold text-base">
                <Workflow className="w-5 h-5 text-emerald-400" />
                Verified System Architecture & Data Flow
              </div>
              <span className="text-xs text-emerald-400 font-mono bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                Source-Backed Architecture Tiers
              </span>
            </div>

            {/* Architecture Tiers Flow */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-stretch">
              {/* Tier 1: Client & Presentation */}
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-700/60 flex flex-col justify-between space-y-3 relative group hover:border-emerald-500/50 transition">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400 bg-sky-950/40 px-2 py-0.5 rounded border border-sky-800/40 flex items-center gap-1">
                      <Monitor className="w-3 h-3" /> Tier 1: Client
                    </span>
                  </div>
                  <h5 className="font-semibold text-white text-sm">
                    {summary?.deep_analysis?.modules?.some((m) => m.file_path.includes('frontend'))
                      ? 'Web Client Interface'
                      : 'HTTP & Webhook Clients'}
                  </h5>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Presentation layer submitting requests and handling user interactions.
                  </p>
                </div>
                <div className="pt-2 border-t border-slate-800">
                  <div className="text-[11px] font-mono text-sky-300">
                    {summary?.deep_analysis?.modules?.find((m) => m.file_path.includes('frontend') || m.file_path.includes('ui') || m.file_path.includes('web'))?.file_path || 'REST / JSON Payloads'}
                  </div>
                </div>
              </div>

              {/* Tier 2: API & Gateway Layer */}
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-700/60 flex flex-col justify-between space-y-3 relative group hover:border-emerald-500/50 transition">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40 flex items-center gap-1">
                      <Server className="w-3 h-3" /> Tier 2: API Gateway
                    </span>
                  </div>
                  <h5 className="font-semibold text-white text-sm">
                    {summary?.overview?.frameworks?.[0]?.name ? `${summary.overview.frameworks[0].name} Service Layer` : 'Application Gateway'}
                  </h5>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Handles incoming routing, request validation, authentication, and dispatch.
                  </p>
                </div>
                <div className="pt-2 border-t border-slate-800">
                  <div className="text-[11px] font-mono text-emerald-300">
                    {summary?.overview?.entry_points?.[0]?.file_path || 'Main application gateway'}
                  </div>
                </div>
              </div>

              {/* Tier 3: Core Processing & AI Logic */}
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-700/60 flex flex-col justify-between space-y-3 relative group hover:border-emerald-500/50 transition">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 bg-purple-950/40 px-2 py-0.5 rounded border border-purple-800/40 flex items-center gap-1">
                      <Cpu className="w-3 h-3" /> Tier 3: Core & AI
                    </span>
                  </div>
                  <h5 className="font-semibold text-white text-sm">
                    {summary?.overview?.frameworks?.some((f) => f.name.includes('Scikit') || f.name.includes('Learn'))
                      ? 'AI / ML Inference Engine'
                      : 'Business Logic & Services'}
                  </h5>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Domain algorithms, services, model inference, and business logic execution.
                  </p>
                </div>
                <div className="pt-2 border-t border-slate-800">
                  <div className="text-[11px] font-mono text-purple-300">
                    {summary?.deep_analysis?.modules?.find((m) => m.file_path.includes('utils') || m.file_path.includes('service') || m.file_path.includes('train'))?.file_path || 'Domain business logic'}
                  </div>
                </div>
              </div>

              {/* Tier 4: Data & Persistence */}
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-700/60 flex flex-col justify-between space-y-3 relative group hover:border-emerald-500/50 transition">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40 flex items-center gap-1">
                      <Database className="w-3 h-3" /> Tier 4: Storage
                    </span>
                  </div>
                  <h5 className="font-semibold text-white text-sm">
                    {summary?.overview?.integrations?.[0]?.name || 'Database Engine'}
                  </h5>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Persistent storage, database schemas, state caches, and data stores.
                  </p>
                </div>
                <div className="pt-2 border-t border-slate-800">
                  <div className="text-[11px] font-mono text-amber-300">
                    {summary?.overview?.integrations?.[0]?.file_path || 'State and database persistence'}
                  </div>
                </div>
              </div>
            </div>

            {/* Architecture Relationships Summary */}
            {summary?.deep_analysis?.architecture_map && summary.deep_analysis.architecture_map.length > 0 && (
              <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 space-y-2">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <ArrowRight className="w-3.5 h-3.5 text-emerald-400" />
                  Verified Component Interconnections ({summary.deep_analysis.architecture_map.length})
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                  {summary.deep_analysis.architecture_map.map((rel: any, i: number) => (
                    <div
                      key={i}
                      className="p-2.5 rounded bg-slate-800/60 border border-slate-700/50 text-xs text-slate-300 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="font-mono text-emerald-300 font-semibold truncate">{rel.from || rel.source}</span>
                        <span className="text-slate-500">&rarr;</span>
                        <span className="font-mono text-sky-300 font-semibold truncate">{rel.to || rel.target}</span>
                      </div>
                      <span className="text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded shrink-0 border border-slate-700/50 font-mono">
                        {rel.type}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Structured Concise Overview */}
          {summary?.overview && (
            <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-6 space-y-6">
              <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-100 font-bold text-base">
                  <BookOpen className="w-4 h-4 text-emerald-400" />
                  Concise Repository Overview (Evidence-Grounded)
                </div>
                <span className="text-xs text-slate-400 italic">
                  Isolated to commit {repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 8) : ''}
                </span>
              </div>

              {/* Purpose & Verified Citations */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Verified Purpose
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-medium">
                  {summary.overview.purpose}
                </p>
                {summary.overview.purpose_evidence?.length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {summary.overview.purpose_evidence.map((cit, idx) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedCitation(cit)}
                        className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700/80 font-mono transition flex items-center gap-1.5"
                      >
                        <FileText className="w-3 h-3" />
                        {cit.file_path}:L{cit.start_line}-L{cit.end_line}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Frameworks & Entry Points Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Detected Frameworks */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-2">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-emerald-400" />
                    Verified Frameworks & Dependencies
                  </div>
                  {summary.overview.frameworks?.length ? (
                    <div className="flex flex-wrap gap-2">
                      {summary.overview.frameworks.map((f, i) => (
                        <span
                          key={i}
                          className="text-xs px-2.5 py-1 rounded-md bg-emerald-950/30 border border-emerald-800/40 text-emerald-300 font-mono flex items-center gap-1.5"
                          title={f.evidence || f.file_path}
                        >
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          {f.name}
                          {f.file_path && (
                            <span className="text-[10px] text-slate-400">
                              ({f.file_path}:{f.lines || '1'})
                            </span>
                          )}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400">Standard Library / Not declared in manifest</div>
                  )}
                </div>

                {/* Entry Points */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-2">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Server className="w-3.5 h-3.5 text-sky-400" />
                    Main Entry Points & Key Modules
                  </div>
                  {summary.overview.entry_points?.length ? (
                    <div className="space-y-1.5">
                      {summary.overview.entry_points.map((ep, i) => (
                        <div key={i} className="text-xs text-slate-300 flex items-center justify-between">
                          <span className="font-mono text-sky-300 bg-sky-950/30 px-1.5 py-0.5 rounded border border-sky-800/40">
                            {ep.file_path}
                          </span>
                          <span className="text-slate-400 text-[11px]">{ep.description || ep.symbol}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400">No primary entry point file detected</div>
                  )}
                </div>
              </div>

              {/* Integrations & Commands Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Data Stores & External Integrations */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-2">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-purple-400" />
                    APIs, Data Stores & External Integrations
                  </div>
                  {summary.overview.integrations?.length ? (
                    <div className="space-y-2">
                      {summary.overview.integrations.map((it, i) => (
                        <div key={i} className="text-xs text-slate-300 p-2 rounded bg-slate-800/50 border border-slate-700/40">
                          <div className="font-semibold text-white flex items-center justify-between">
                            <span>{it.name}</span>
                            <span className="text-[10px] text-purple-300 bg-purple-950/40 px-1.5 py-0.5 rounded border border-purple-800/40 uppercase">
                              {it.type}
                            </span>
                          </div>
                          {it.file_path && (
                            <div className="text-[11px] font-mono text-slate-400 mt-1">
                              Evidence: {it.file_path}:{it.lines || '1'}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400">Not confirmed from the indexed files.</div>
                  )}
                </div>

                {/* Confirmed Commands */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-2">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-amber-400" />
                    Confirmed Build, Run & Test Commands
                  </div>
                  {summary.overview.commands?.length ? (
                    <div className="space-y-1.5">
                      {summary.overview.commands.map((cmd, i) => (
                        <div key={i} className="text-xs p-2 rounded bg-slate-900 border border-slate-700/50 flex items-center justify-between">
                          <div>
                            <span className="text-[11px] text-slate-400 uppercase font-semibold block">{cmd.name}</span>
                            <code className="text-emerald-400 font-mono text-xs">{cmd.command}</code>
                          </div>
                          {cmd.file_path && (
                            <span className="text-[10px] text-slate-500 font-mono">{cmd.file_path}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400">Not confirmed from the indexed files.</div>
                  )}
                </div>
              </div>

              {/* Unconfirmed Claims & Limitations Notice */}
              {summary.overview.unconfirmed?.length > 0 && (
                <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/40 space-y-2">
                  <div className="text-xs font-semibold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                    Limitations & Discrepancies (Untrusted README vs Source Code)
                  </div>
                  <ul className="list-disc list-inside text-xs text-slate-300 space-y-1">
                    {summary.overview.unconfirmed.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Deep Analysis View Toggle */}
          <div className="border border-slate-700/60 rounded-xl overflow-hidden bg-slate-800/30">
            <button
              onClick={() => setShowDeepAnalysis(!showDeepAnalysis)}
              className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-800/50 transition"
            >
              <div className="flex items-center gap-2">
                <Workflow className="w-5 h-5 text-sky-400" />
                <div>
                  <h4 className="text-sm font-bold text-white">
                    Deep Analysis View: Architecture, Modules & Code Flows
                  </h4>
                  <p className="text-xs text-slate-400">
                    Source-backed module explanations, architecture relationships, and potential risks.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-sky-400 font-medium">
                {showDeepAnalysis ? (
                  <>
                    Hide Deep Analysis <ChevronDown className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    Show Deep Analysis <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </div>
            </button>

            {showDeepAnalysis && (
              <div className="p-6 border-t border-slate-700/60 space-y-6">
                {/* Modules breakdown */}
                {summary?.deep_analysis?.modules && (
                  <div className="space-y-3">
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Module Deep Dive
                    </h5>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {summary.deep_analysis.modules.map((m, i) => (
                        <div key={i} className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-700/50 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white text-xs">{m.name}</span>
                            <span className="text-[10px] font-mono text-sky-400">{m.file_path}</span>
                          </div>
                          <p className="text-xs text-slate-300 leading-relaxed">{m.explanation}</p>
                          {m.citations?.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {m.citations.map((c, ci) => (
                                <button
                                  key={ci}
                                  onClick={() => setSelectedCitation(c)}
                                  className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-sky-300 font-mono hover:bg-slate-800 border border-slate-700/60"
                                >
                                  L{c.start_line}-L{c.end_line}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Architecture Map */}
                {summary?.deep_analysis?.architecture_map && summary.deep_analysis.architecture_map.length > 0 && (
                  <div className="space-y-3">
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Source-Backed Architecture Map
                    </h5>
                    <div className="space-y-2">
                      {summary.deep_analysis.architecture_map.map((rel: any, i: number) => (
                        <div
                          key={i}
                          className="p-3 rounded-lg bg-slate-800/30 border border-slate-700/40 text-xs text-slate-300 flex items-center justify-between"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-emerald-300 font-semibold">{rel.from || rel.source}</span>
                            <span className="text-slate-500">&rarr;</span>
                            <span className="font-mono text-sky-300 font-semibold">{rel.to || rel.target}</span>
                            <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700/50">
                              {rel.type}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 font-mono">{rel.evidence || `${rel.source} connection`}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Key Code Execution Flows */}
                {summary?.deep_analysis?.key_code_flows && summary.deep_analysis.key_code_flows.length > 0 && (
                  <div className="space-y-3">
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Key Code Execution Flows
                    </h5>
                    <div className="space-y-3">
                      {summary.deep_analysis.key_code_flows.map((flow, i) => (
                        <div key={i} className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-700/50 space-y-2">
                          <div className="font-semibold text-xs text-white">{flow.name}</div>
                          <p className="text-xs text-slate-300">{flow.description}</p>
                          <div className="space-y-1 pl-2 border-l-2 border-sky-500/40">
                            {flow.steps.map((st, si) => (
                              <div key={si} className="text-xs text-slate-300 flex items-center gap-2">
                                <span className="text-[10px] font-bold text-sky-400">{st.order}.</span>
                                <span>{st.step}</span>
                                {st.file_path && (
                                  <span className="text-[10px] text-slate-400 font-mono">
                                    ({st.file_path}:{st.lines || '1'})
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Potential Code Risks */}
                {summary?.deep_analysis?.potential_risks && summary.deep_analysis.potential_risks.length > 0 && (
                  <div className="space-y-3">
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      Potential Architectural & Security Risks
                    </h5>
                    <div className="space-y-2">
                      {summary.deep_analysis.potential_risks.map((risk, i) => (
                        <div
                          key={i}
                          className="p-3 rounded-lg bg-rose-950/20 border border-rose-800/40 text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-rose-300">{risk.title}</span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950/60 text-rose-400 border border-rose-800 uppercase font-bold">
                              {risk.severity}
                            </span>
                          </div>
                          <p className="text-slate-300">{risk.description}</p>
                          {risk.evidence?.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {risk.evidence.map((ev, ei) => (
                                <button
                                  key={ei}
                                  onClick={() => setSelectedCitation(ev)}
                                  className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-rose-300 font-mono hover:bg-slate-800 border border-slate-700/60"
                                >
                                  {ev.file_path}:L{ev.start_line}-L{ev.end_line}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* Grounded Evidence Citation Viewer Modal */}
      {selectedCitation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-2xl w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-sky-400" />
                <h4 className="text-sm font-bold text-white font-mono">
                  {selectedCitation.file_path}:L{selectedCitation.start_line}-L{selectedCitation.end_line}
                </h4>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-slate-400 hover:text-white text-sm"
              >
                &times; Close
              </button>
            </div>
            {selectedCitation.statement && (
              <div className="text-xs text-slate-300 font-medium">
                Claim: &ldquo;{selectedCitation.statement}&rdquo;
              </div>
            )}
            <div className="rounded-lg bg-slate-950 p-4 font-mono text-xs text-slate-300 overflow-x-auto border border-slate-800">
              <pre className="whitespace-pre-wrap">{selectedCitation.snippet || '// Snippet indexed at commit'}</pre>
            </div>
            <div className="flex justify-end gap-2">
              {onNavigateToFile && (
                <button
                  onClick={() => {
                    const cit = selectedCitation;
                    setSelectedCitation(null);
                    onNavigateToFile(cit.file_path, [cit.start_line, cit.end_line]);
                  }}
                  className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow transition flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Open in File Explorer
                </button>
              )}
              <button
                onClick={() => setSelectedCitation(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
