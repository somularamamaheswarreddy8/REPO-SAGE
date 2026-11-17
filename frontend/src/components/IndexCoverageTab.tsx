import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  FileCode,
  FileText,
  AlertTriangle,
  FolderTree,
  Database,
  RefreshCw,
  Search,
  CheckCircle2,
  Lock,
  Clock
} from 'lucide-react';
import { Repository, RepositoryHealthDashboard, HealthFileItem } from '../types';
import { api } from '../services/api';

interface IndexCoverageTabProps {
  repo: Repository;
  onNavigateToFile: (filePath: string) => void;
  onRefreshRepo: () => void;
}

export const IndexCoverageTab: React.FC<IndexCoverageTabProps> = ({
  repo,
  onNavigateToFile,
  onRefreshRepo
}) => {
  const [dashboard, setDashboard] = useState<RepositoryHealthDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');

  const activeRepoIdRef = useRef<number>(repo.id);

  const fetchHealthDashboard = async () => {
    const targetRepoId = repo.id;
    setLoading(true);
    setError(null);
    setDashboard(null);
    try {
      const data = await api.getHealthDashboard(targetRepoId);
      if (activeRepoIdRef.current !== targetRepoId) return;
      setDashboard(data);
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setError(err.message || 'Failed to load repository health dashboard');
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    activeRepoIdRef.current = repo.id;
    fetchHealthDashboard();
  }, [repo.id, repo.indexed_commit_sha]);

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400 flex flex-col items-center gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
        <span className="text-sm">Analyzing index health and repository file safety...</span>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="p-8 text-center bg-rose-950/20 border border-rose-800/40 rounded-xl space-y-3 max-w-lg mx-auto">
        <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto" />
        <h3 className="text-base font-semibold text-white">Index Health Check Unavailable</h3>
        <p className="text-xs text-rose-300">{error || 'No index health metrics found.'}</p>
        <button
          onClick={fetchHealthDashboard}
          className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-white transition"
        >
          Retry Health Scan
        </button>
      </div>
    );
  }

  // Filter files
  const filteredFiles = (dashboard.files_summary || []).filter((file: HealthFileItem) => {
    const matchesSearch =
      !searchTerm ||
      file.file_path.toLowerCase().includes(searchTerm.toLowerCase()) ||
      file.filename.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'indexed' && (file.status === 'indexed' || file.status === 'fallback')) ||
      (statusFilter === 'parser_aware' && file.analysis_mode === 'parser_aware') ||
      (statusFilter === 'fallback' && file.analysis_mode === 'text_fallback') ||
      (statusFilter === 'excluded' && file.status === 'excluded') ||
      (statusFilter === 'failed' && (file.status === 'failed' || file.status === 'unsupported'));

    const matchesCategory =
      categoryFilter === 'all' ||
      (categoryFilter === 'secret' && file.is_secret) ||
      (categoryFilter === 'binary' && file.is_binary) ||
      (categoryFilter === 'vendor' && file.category === 'vendor/config') ||
      (categoryFilter === 'source' && file.category === 'source');

    return matchesSearch && matchesStatus && matchesCategory;
  });

  const percentIndexed =
    dashboard.total_discovered_files > 0
      ? Math.round((dashboard.indexed_files_count / dashboard.total_discovered_files) * 100)
      : 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Staleness Warning Banner */}
      {dashboard.is_stale && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start gap-3 text-amber-300">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-amber-200">Stale Repository Index Detected</h4>
            <p className="text-xs leading-relaxed text-amber-300/90">
              The remote branch <span className="font-mono font-semibold">{dashboard.branch}</span> has newer commits
              (Head: <span className="font-mono">{dashboard.remote_commit_sha?.slice(0, 7)}</span>) than your indexed commit
              (<span className="font-mono">{dashboard.indexed_commit_sha?.slice(0, 7)}</span>). PR reviews and code answers
              should be refreshed to reflect recent code modifications.
            </p>
            <button
              onClick={() => {
                api.triggerIndexing(repo.id, false).then(() => {
                  onRefreshRepo();
                  fetchHealthDashboard();
                });
              }}
              className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-600 hover:bg-amber-500 text-slate-950 font-semibold text-xs transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Re-index to Latest Commit
            </button>
          </div>
        </div>
      )}

      {/* Header Info */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-white tracking-tight">{dashboard.full_name}</h2>
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 border border-slate-700 text-slate-300 font-mono">
              {dashboard.branch}
            </span>
            {dashboard.is_stale ? (
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                Stale Index
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Up to Date
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-400 mt-2 font-mono">
            <span>Commit: {dashboard.indexed_commit_sha ? dashboard.indexed_commit_sha.slice(0, 10) : 'None'}</span>
            {dashboard.last_indexed_at && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />
                Indexed: {new Date(dashboard.last_indexed_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchHealthDashboard}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh Health Metrics
          </button>
        </div>
      </div>

      {/* Database Mode and Vector Engine Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 flex-shrink-0">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <div className="font-semibold text-white flex items-center gap-2">
              <span>Database Engine: {dashboard.database_mode}</span>
              {dashboard.database_mode.includes('Fallback') && (
                <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  SQLite Memory Cosine
                </span>
              )}
            </div>
            <div className="text-slate-400 text-[11px] mt-0.5">
              {dashboard.database_vector_capabilities}
            </div>
          </div>
        </div>
      </div>

      {/* KPI Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Discovered Files</div>
          <div className="text-2xl font-bold text-white">{dashboard.total_discovered_files}</div>
          <div className="text-[10px] text-slate-500">In tree at indexed commit</div>
        </div>

        <div className="bg-slate-900 border border-emerald-950/60 rounded-xl p-4 space-y-1">
          <div className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider">Indexed Files</div>
          <div className="text-2xl font-bold text-emerald-400">{dashboard.indexed_files_count}</div>
          <div className="text-[10px] text-emerald-500/80">{percentIndexed}% repository coverage</div>
        </div>

        <div className="bg-slate-900 border border-sky-950/60 rounded-xl p-4 space-y-1">
          <div className="text-[11px] font-medium text-sky-400 uppercase tracking-wider flex items-center gap-1">
            <FileCode className="w-3 h-3" /> Parser-Aware
          </div>
          <div className="text-2xl font-bold text-sky-400">{dashboard.parser_aware_count}</div>
          <div className="text-[10px] text-slate-500">AST symbol & line range</div>
        </div>

        <div className="bg-slate-900 border border-indigo-950/60 rounded-xl p-4 space-y-1">
          <div className="text-[11px] font-medium text-indigo-400 uppercase tracking-wider flex items-center gap-1">
            <FileText className="w-3 h-3" /> Text-Fallback
          </div>
          <div className="text-2xl font-bold text-indigo-400">{dashboard.text_fallback_count}</div>
          <div className="text-[10px] text-slate-500">Generic text chunking</div>
        </div>

        <div className="bg-slate-900 border border-amber-950/60 rounded-xl p-4 space-y-1">
          <div className="text-[11px] font-medium text-amber-400 uppercase tracking-wider flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" /> Excluded Secrets
          </div>
          <div className="text-2xl font-bold text-amber-400">{dashboard.excluded_secrets_count}</div>
          <div className="text-[10px] text-slate-500">Zero-leakage protected</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Lock className="w-3 h-3" /> Binaries & Vendor
          </div>
          <div className="text-2xl font-bold text-slate-300">
            {dashboard.excluded_binaries_count + dashboard.excluded_vendors_count}
          </div>
          <div className="text-[10px] text-slate-500">Excluded by policy</div>
        </div>
      </div>

      {/* File Classification Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-900/60">
          <div>
            <h3 className="text-sm font-semibold text-white">Repository File Classification & Safety Audit</h3>
            <p className="text-xs text-slate-400">
              Showing {filteredFiles.length} of {dashboard.files_summary.length} files. Click any safe file to view in the file explorer.
            </p>
          </div>

          {/* Controls: Search & Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5 pointer-events-none" />
              <input
                type="text"
                placeholder="Search file path..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-44"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
            >
              <option value="all">All Statuses</option>
              <option value="indexed">Indexed (All)</option>
              <option value="parser_aware">Parser-Aware</option>
              <option value="fallback">Text-Fallback</option>
              <option value="excluded">Excluded</option>
              <option value="failed">Failed / Skipped</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
            >
              <option value="all">All Categories</option>
              <option value="source">Source Code</option>
              <option value="secret">Secret / Credential</option>
              <option value="binary">Binary / Media</option>
              <option value="vendor">Vendor / Build</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto max-h-[500px]">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-950/60 sticky top-0 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <tr>
                <th className="py-2.5 px-4">File Path</th>
                <th className="py-2.5 px-3">Language</th>
                <th className="py-2.5 px-3">Analysis Mode</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Safety / Exclusion Reason</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredFiles.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">
                    No files match the selected search or filter criteria.
                  </td>
                </tr>
              ) : (
                filteredFiles.map((file: HealthFileItem) => (
                  <tr key={file.file_path} className="hover:bg-slate-800/40 transition">
                    <td className="py-2 px-4 font-medium text-slate-200 truncate max-w-xs" title={file.file_path}>
                      {file.file_path}
                    </td>
                    <td className="py-2 px-3 text-slate-400 font-sans">{file.language_display}</td>
                    <td className="py-2 px-3">
                      {file.analysis_mode === 'parser_aware' ? (
                        <span className="inline-flex items-center gap-1 text-sky-400 text-[11px] font-sans">
                          <FileCode className="w-3 h-3" /> Parser-Aware
                        </span>
                      ) : file.analysis_mode === 'text_fallback' ? (
                        <span className="inline-flex items-center gap-1 text-indigo-400 text-[11px] font-sans">
                          <FileText className="w-3 h-3" /> Text-Fallback
                        </span>
                      ) : (
                        <span className="text-slate-500 text-[11px] font-sans">Excluded</span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      {file.status === 'indexed' || file.status === 'fallback' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-sans">
                          Indexed
                        </span>
                      ) : file.status === 'failed' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 font-sans">
                          Failed
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700 font-sans">
                          Excluded
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 font-sans text-slate-400 max-w-xs truncate" title={file.exclusion_reason || ''}>
                      {file.is_secret ? (
                        <span className="inline-flex items-center gap-1 text-amber-400 text-xs">
                          <Lock className="w-3 h-3" /> Credential / Secret Protected
                        </span>
                      ) : file.is_binary ? (
                        <span className="inline-flex items-center gap-1 text-slate-400 text-xs">
                          Binary File (Content Omitted)
                        </span>
                      ) : file.exclusion_reason ? (
                        <span className="text-slate-400 text-xs">{file.exclusion_reason}</span>
                      ) : (
                        <span className="text-emerald-400 text-xs flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Safe
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-4 text-right font-sans">
                      {file.is_safe_to_view_in_explorer ? (
                        <button
                          onClick={() => onNavigateToFile(file.file_path)}
                          className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-medium text-xs transition"
                          title="Open file in Explorer preview"
                        >
                          <FolderTree className="w-3 h-3" /> View in Tree
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-600 cursor-not-allowed" title="Preview forbidden for safety">
                          Protected
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
