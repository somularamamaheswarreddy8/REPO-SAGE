import React from 'react';
import { Repository, IndexingStatus } from '../types';
import { GitBranch, GitCommit, CheckCircle2, AlertCircle, Clock, Database, RefreshCw } from 'lucide-react';

interface RepositoryContextBarProps {
  repo: Repository | null;
  indexingStatus?: IndexingStatus | null;
  compact?: boolean;
  className?: string;
}

export const RepositoryContextBar: React.FC<RepositoryContextBarProps> = ({
  repo,
  indexingStatus,
  compact = false,
  className = '',
}) => {
  if (!repo) {
    return (
      <div className={`flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-2xl animate-pulse ${className}`}>
        <div className="w-2.5 h-2.5 rounded-full bg-slate-300"></div>
        <span className="text-xs font-mono text-slate-400">Loading repository context...</span>
      </div>
    );
  }

  const isRunning =
    indexingStatus?.status === 'running' ||
    indexingStatus?.status === 'queued' ||
    repo.indexing_status === 'running' ||
    repo.indexing_status === 'queued';

  const isFailed = repo.indexing_status === 'failed' || indexingStatus?.status === 'failed';
  const isCompleted = repo.indexing_status === 'completed' && !isFailed;
  const isStale = repo.is_stale || isFailed || !repo.indexed_commit_sha || repo.indexed_commit_sha === 'unindexed';

  const formatLastIndexed = (timestamp?: string | null) => {
    if (!timestamp) return 'Never';
    try {
      const date = new Date(timestamp);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  if (compact) {
    return (
      <div className={`inline-flex items-center flex-wrap gap-2 px-3 py-1.5 rounded-2xl bg-white border border-[#e2e8df] text-xs shadow-sm ${className}`}>
        <span className="font-bold text-slate-900 font-mono">
          {repo.owner}/{repo.name}
        </span>
        <span className="text-slate-300">|</span>
        <span className="inline-flex items-center gap-1 font-mono text-slate-600 text-[11px]">
          <GitBranch className="w-3 h-3 text-slate-400" />
          {repo.default_branch}
        </span>
        <span className="inline-flex items-center gap-1 font-mono text-slate-600 text-[11px]">
          <GitCommit className="w-3 h-3 text-slate-400" />
          {repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 7) : 'HEAD'}
        </span>
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
          isRunning
            ? 'bg-amber-50 text-amber-700 border border-amber-200'
            : isCompleted
            ? 'bg-lime-50 text-lime-800 border border-lime-200'
            : 'bg-rose-50 text-rose-700 border border-rose-200'
        }`}>
          {isRunning ? (
            <RefreshCw className="w-2.5 h-2.5 animate-spin" />
          ) : isCompleted ? (
            <CheckCircle2 className="w-2.5 h-2.5 text-lime-600" />
          ) : (
            <AlertCircle className="w-2.5 h-2.5 text-rose-500" />
          )}
          {isRunning ? 'Indexing' : isCompleted ? 'Current' : 'Stale/Failed'}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-gradient-to-r from-slate-50 to-white border border-[#e2e8df] rounded-2xl text-xs shadow-sm ${className}`}>
      {/* Left: Owner/Name, Branch, Commit SHA */}
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="flex items-center gap-1.5">
          <Database className="w-4 h-4 text-slate-500" />
          <span className="font-bold text-slate-800 text-xs sm:text-sm tracking-tight font-mono">
            {repo.owner}/<span className="text-slate-900 font-extrabold">{repo.name}</span>
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-white border border-slate-200 font-mono text-[11px] text-slate-700 shadow-2xs">
            <GitBranch className="w-3 h-3 text-slate-400" />
            <span className="font-medium">{repo.default_branch}</span>
          </span>

          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-white border border-slate-200 font-mono text-[11px] text-slate-700 shadow-2xs" title={`Indexed Commit SHA: ${repo.indexed_commit_sha || 'Unindexed'}`}>
            <GitCommit className="w-3 h-3 text-slate-400" />
            <span className="font-semibold">{repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 8) : 'unindexed'}</span>
          </span>
        </div>
      </div>

      {/* Right: Indexing Status, Current/Stale Indicator, Last Indexed Time */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Status Badge */}
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-semibold border shadow-2xs ${
          isRunning
            ? 'bg-amber-50 border-amber-200 text-amber-800'
            : isCompleted
            ? 'bg-lime-50 border-lime-300 text-lime-900'
            : 'bg-rose-50 border-rose-200 text-rose-800'
        }`}>
          {isRunning ? (
            <RefreshCw className="w-3 h-3 text-amber-600 animate-spin" />
          ) : isCompleted ? (
            <CheckCircle2 className="w-3 h-3 text-lime-600" />
          ) : (
            <AlertCircle className="w-3 h-3 text-rose-500" />
          )}
          <span>
            {isRunning
              ? `Indexing (${indexingStatus?.progress ?? repo.indexing_progress}%)`
              : isCompleted
              ? 'Index Complete'
              : repo.indexing_status === 'failed'
              ? 'Index Failed'
              : 'Not Indexed'}
          </span>
        </span>

        {/* Index Freshness Badge */}
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-[11px] font-medium border shadow-2xs ${
          isStale
            ? 'bg-orange-50 border-orange-200 text-orange-800'
            : 'bg-emerald-50 border-emerald-200 text-emerald-800'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isStale ? 'bg-orange-500' : 'bg-emerald-500'}`}></span>
          <span>{isStale ? 'Index Stale' : 'Index Current'}</span>
        </span>

        {/* Last Indexed Time */}
        <div className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-100/70 text-slate-500 text-[11px] border border-slate-200/80 font-mono">
          <Clock className="w-3 h-3 text-slate-400" />
          <span>Last indexed: {formatLastIndexed(repo.last_indexed_at)}</span>
        </div>
      </div>
    </div>
  );
};
