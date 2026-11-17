import React, { useState, useEffect, useRef } from 'react';
import {
  GitCompare,
  FileDiff,
  Layers,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  CheckCircle,
} from 'lucide-react';
import { api } from '../services/api';
import { Repository, CommitCompareData } from '../types';

interface CommitCompareTabProps {
  repository: Repository;
  onNavigateToFile?: (filePath: string, startLine?: number, endLine?: number) => void;
}

export const CommitCompareTab: React.FC<CommitCompareTabProps> = ({
  repository,
  onNavigateToFile,
}) => {
  const [baseRef, setBaseRef] = useState<string>(repository.default_branch || 'main');
  const [headRef, setHeadRef] = useState<string>('develop');
  const [data, setData] = useState<CommitCompareData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeRepoIdRef = useRef<number>(repository.id);

  useEffect(() => {
    activeRepoIdRef.current = repository.id;
    setBaseRef(repository.default_branch || 'main');
    setData(null);
    setError(null);
    handleCompare();
  }, [repository.id, repository.indexed_commit_sha]);

  const handleCompare = async () => {
    const targetRepoId = repository.id;
    if (!baseRef.trim() || !headRef.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await api.compareCommits(targetRepoId, baseRef.trim(), headRef.trim());
      if (activeRepoIdRef.current !== targetRepoId) return;
      setData(res);
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setError(err.message || 'Failed to compare commits.');
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setLoading(false);
      }
    }
  };

  const handleCitationClick = (citation: string, filePath?: string) => {
    if (!onNavigateToFile || !filePath) return;
    const match = citation.match(/^([^:]+):(\d+)/);
    if (match) {
      onNavigateToFile(match[1], parseInt(match[2], 10), parseInt(match[2], 10));
    } else {
      onNavigateToFile(filePath, 1, 1);
    }
  };

  return (
    <div className="space-y-6">
      {/* Compare Control Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-bold text-white tracking-tight">
                Commit &amp; Branch Comparison
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              Inspect file diffs, architecture shifts, and new vs. resolved findings between two commits or branches.
            </p>
          </div>

          {/* Controls */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">Base:</span>
              <input
                type="text"
                value={baseRef}
                onChange={(e) => setBaseRef(e.target.value)}
                placeholder="main or SHA"
                className="px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-xl text-white font-mono focus:outline-none focus:border-emerald-500 w-32"
              />
            </div>

            <span className="text-slate-400">&larr;</span>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">Head:</span>
              <input
                type="text"
                value={headRef}
                onChange={(e) => setHeadRef(e.target.value)}
                placeholder="develop or SHA"
                className="px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-xl text-white font-mono focus:outline-none focus:border-emerald-500 w-32"
              />
            </div>

            <button
              onClick={handleCompare}
              disabled={loading}
              className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition shadow"
            >
              {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <GitCompare className="w-3.5 h-3.5" />}
              <span>Compare</span>
            </button>
          </div>
        </div>

        {/* SHA & Freshness Badges */}
        {data && (
          <div className="pt-3 border-t border-slate-800/80 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            {/* Base */}
            <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-slate-400">Base: </span>
                <span className="text-white font-semibold">{data.base.ref_name}</span>
                <span className="text-slate-400 ml-2">({data.base.commit_sha.slice(0, 8)})</span>
              </div>
              <div className="flex items-center gap-2">
                {data.base.is_indexed ? (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    Indexed
                  </span>
                ) : (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    Not Indexed
                  </span>
                )}
                {data.base.is_stale && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
                    Stale
                  </span>
                )}
              </div>
            </div>

            {/* Head */}
            <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-slate-400">Head: </span>
                <span className="text-emerald-300 font-semibold">{data.head.ref_name}</span>
                <span className="text-slate-400 ml-2">({data.head.commit_sha.slice(0, 8)})</span>
              </div>
              <div className="flex items-center gap-2">
                {data.head.is_indexed ? (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    Indexed
                  </span>
                ) : (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    Not Indexed
                  </span>
                )}
                {data.head.is_stale && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
                    Stale
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 text-slate-400 space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
          <p className="text-sm">Calculating diffs, architecture shifts, and review finding changes...</p>
        </div>
      ) : error ? (
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="font-semibold text-white">Comparison Failed</h3>
          </div>
          <p className="text-xs text-slate-400">{error}</p>
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Summary Metric Counters */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
              <div className="text-[11px] text-slate-400">Total Changed</div>
              <div className="text-xl font-bold text-white">{data.summary.total_changed_files}</div>
            </div>
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
              <div className="text-[11px] text-emerald-400">Added</div>
              <div className="text-xl font-bold text-emerald-400">{data.summary.added_count}</div>
            </div>
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
              <div className="text-[11px] text-cyan-400">Modified</div>
              <div className="text-xl font-bold text-cyan-400">{data.summary.modified_count}</div>
            </div>
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
              <div className="text-[11px] text-rose-400">Deleted</div>
              <div className="text-xl font-bold text-rose-400">{data.summary.deleted_count}</div>
            </div>
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1">
              <div className="text-[11px] text-amber-400">Renamed</div>
              <div className="text-xl font-bold text-amber-400">{data.summary.renamed_count}</div>
            </div>
          </div>

          {/* Architecture Shifts */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              Architecture Map Changes
            </h3>
            <p className="text-xs text-slate-300">
              {data.architecture_diff.architecture_shift_summary}
            </p>

            {data.architecture_diff.dependency_changes.length > 0 && (
              <div className="space-y-2 pt-2">
                {data.architecture_diff.dependency_changes.map((dc, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-white font-semibold">{dc.module}</span>
                      <span className="text-slate-400">&mdash;</span>
                      <span className="text-slate-300">{dc.change}</span>
                    </div>
                    <button
                      onClick={() => handleCitationClick(dc.citation, dc.module)}
                      className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-mono hover:text-emerald-300"
                    >
                      <span>{dc.citation}</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Review Findings Diff */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Review Findings Comparison
              </h3>
              <span className="text-xs text-slate-400 font-mono">
                {data.findings_diff.status_label}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* New Findings */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-rose-400 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  New Findings Introduced ({data.findings_diff.new_findings.length})
                </div>
                {data.findings_diff.new_findings.length === 0 ? (
                  <p className="text-xs text-slate-400 p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    No new findings detected in head commit.
                  </p>
                ) : (
                  data.findings_diff.new_findings.map((f: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-950/60 border border-rose-900/40 rounded-xl space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white">{f.title}</span>
                        <span className="font-mono text-rose-400 uppercase text-[10px]">{f.severity}</span>
                      </div>
                      <p className="text-slate-400">{f.explanation}</p>
                    </div>
                  ))
                )}
              </div>

              {/* Resolved Findings */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Resolved Findings ({data.findings_diff.resolved_findings.length})
                </div>
                {data.findings_diff.resolved_findings.length === 0 ? (
                  <p className="text-xs text-slate-400 p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    No findings were resolved between compared commits.
                  </p>
                ) : (
                  data.findings_diff.resolved_findings.map((f: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-950/60 border border-emerald-900/40 rounded-xl space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white">{f.title}</span>
                        <span className="font-mono text-emerald-400 text-[10px]">Resolved</span>
                      </div>
                      <p className="text-slate-400 font-mono text-[11px]">{f.citation}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Files Changed List */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <FileDiff className="w-4 h-4 text-emerald-400" />
              Files Changed ({data.files_changed.length})
            </h3>

            <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
              {data.files_changed.map((f, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex items-center justify-between text-xs hover:border-slate-700 transition"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-mono uppercase font-semibold ${
                        f.status === 'added'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : f.status === 'deleted'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                      }`}
                    >
                      {f.status}
                    </span>
                    <span className="font-mono text-white truncate">{f.path}</span>
                  </div>

                  {f.status !== 'deleted' && (
                    <button
                      onClick={() => handleCitationClick(f.citation, f.path)}
                      className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-mono hover:text-emerald-300 shrink-0"
                    >
                      <span>{f.citation}</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
