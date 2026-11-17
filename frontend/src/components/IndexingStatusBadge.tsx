import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, RefreshCw, GitCommit } from 'lucide-react';
import { IndexingStatus } from '../types';

interface IndexingStatusBadgeProps {
  status?: IndexingStatus | null;
  onReindex?: () => void;
  isIndexing?: boolean;
}

export const IndexingStatusBadge: React.FC<IndexingStatusBadgeProps> = ({
  status,
  onReindex,
  isIndexing,
}) => {
  if (!status) return null;

  const getStatusBadge = () => {
    switch (status.status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Indexed
          </span>
        );
      case 'running':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            Indexing ({Math.round(status.progress)}%)
          </span>
        );
      case 'queued':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
            <Clock className="w-3.5 h-3.5" />
            Queued
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
            Not Indexed
          </span>
        );
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      {getStatusBadge()}

      {status.indexed_commit_sha && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-xs border border-slate-700">
          <GitCommit className="w-3 h-3 text-slate-400" />
          {status.indexed_commit_sha.slice(0, 7)}
        </span>
      )}

      {status.status === 'running' && (
        <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-sky-500 transition-all duration-300"
            style={{ width: `${status.progress}%` }}
          />
        </div>
      )}

      {onReindex && (
        <button
          onClick={onReindex}
          disabled={isIndexing || status.status === 'running'}
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition disabled:opacity-50"
          title="Trigger Incremental Re-indexing"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isIndexing || status.status === 'running' ? 'animate-spin' : ''}`} />
        </button>
      )}
    </div>
  );
};
