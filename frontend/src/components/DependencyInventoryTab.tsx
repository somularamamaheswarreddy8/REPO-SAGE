import React, { useState, useEffect, useRef } from 'react';
import {
  Package,
  Search,
  RefreshCw,
  ExternalLink,
  AlertCircle,
  FileCode,
  Info,
} from 'lucide-react';
import { api } from '../services/api';
import { Repository, DependencyInventoryData } from '../types';

interface DependencyInventoryTabProps {
  repository: Repository;
  onNavigateToFile?: (filePath: string, startLine?: number, endLine?: number) => void;
}

export const DependencyInventoryTab: React.FC<DependencyInventoryTabProps> = ({
  repository,
  onNavigateToFile,
}) => {
  const [data, setData] = useState<DependencyInventoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterManifest, setFilterManifest] = useState<string>('all');

  const activeRepoIdRef = useRef<number>(repository.id);

  useEffect(() => {
    activeRepoIdRef.current = repository.id;
    setData(null);
    setError(null);
    loadDependencies();
  }, [repository.id, repository.indexed_commit_sha]);

  const loadDependencies = async () => {
    const targetRepoId = repository.id;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await api.getDependencies(targetRepoId);
      if (activeRepoIdRef.current !== targetRepoId) return;
      setData(res);
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setError(err.message || 'Failed to load repository dependency inventory.');
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setLoading(false);
      }
    }
  };

  const handleManifestClick = (manifestFile: string) => {
    if (onNavigateToFile) {
      onNavigateToFile(manifestFile, 1, 1);
    }
  };

  const filteredDependencies = (data?.dependencies || []).filter((dep) => {
    const matchesSearch =
      dep.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dep.manifest_file.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesType =
      filterType === 'all' ||
      (filterType === 'direct' && dep.is_transitive === false) ||
      (filterType === 'transitive' && dep.is_transitive === true) ||
      (filterType === 'unconfirmed' && dep.is_transitive === null);

    const matchesManifest =
      filterManifest === 'all' || dep.manifest_file === filterManifest;

    return matchesSearch && matchesType && matchesManifest;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Package className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-bold text-white tracking-tight">
                Repository Dependency Inventory
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              Evidence-based inventory parsed directly from repository manifests and lock files.
            </p>
          </div>

          <button
            onClick={loadDependencies}
            disabled={loading}
            className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Scan</span>
          </button>
        </div>

        {/* Metric Counters */}
        {data && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
            <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl">
              <div className="text-[11px] text-slate-400">Total Dependencies</div>
              <div className="text-xl font-bold text-white">{data.summary.total_dependencies}</div>
            </div>
            <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl">
              <div className="text-[11px] text-emerald-400">Direct Dependencies</div>
              <div className="text-xl font-bold text-emerald-400">{data.summary.direct_dependencies}</div>
            </div>
            <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl">
              <div className="text-[11px] text-cyan-400">Transitive Dependencies</div>
              <div className="text-xl font-bold text-cyan-400">{data.summary.transitive_dependencies}</div>
            </div>
            <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl">
              <div className="text-[11px] text-slate-400">Detected Manifests</div>
              <div className="text-xl font-bold text-slate-200">{data.manifest_files.length}</div>
            </div>
          </div>
        )}

        {/* Security & Verification Notice */}
        <div className="pt-3 border-t border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between text-[11px] text-slate-400 gap-2">
          <div className="flex items-center gap-1.5 text-slate-300">
            <Info className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>
              {data?.vulnerability_notice || 'Vulnerability database is unconfigured. No false vulnerability claims are asserted.'}
            </span>
          </div>
          <div className="font-mono text-slate-400">
            Source: {data?.verification_source || 'Static Manifest Parser'} &bull; Checked: {data ? new Date(data.checked_at).toLocaleDateString() : 'N/A'}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 text-slate-400 space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
          <p className="text-sm">Scanning manifest and lock files for declared dependencies...</p>
        </div>
      ) : error || !data ? (
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertCircle className="w-5 h-5" />
            <h3 className="font-semibold text-white">Dependency Scan Failed</h3>
          </div>
          <p className="text-xs text-slate-400">{error || 'No dependencies found.'}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Search & Filter Toolbar */}
          <div className="flex flex-col md:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search dependencies by name or manifest file..."
                className="w-full pl-9 pr-3.5 py-2 text-xs bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-3 py-2 text-xs bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-emerald-500 font-mono"
              >
                <option value="all">All Dependency Types</option>
                <option value="direct">Direct Only</option>
                <option value="transitive">Transitive Only</option>
              </select>

              {data.manifest_files.length > 0 && (
                <select
                  value={filterManifest}
                  onChange={(e) => setFilterManifest(e.target.value)}
                  className="px-3 py-2 text-xs bg-slate-900 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-emerald-500 font-mono"
                >
                  <option value="all">All Manifest Files</option>
                  {data.manifest_files.map((mf, idx) => (
                    <option key={idx} value={mf}>
                      {mf}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Dependencies Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Dependency Name</th>
                    <th className="px-4 py-3">Declared Version</th>
                    <th className="px-4 py-3">Classification</th>
                    <th className="px-4 py-3">Origin Manifest</th>
                    <th className="px-4 py-3">Security Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {filteredDependencies.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                        No dependencies matching current filters.
                      </td>
                    </tr>
                  ) : (
                    filteredDependencies.map((dep, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/40 transition">
                        <td className="px-4 py-3 font-mono font-semibold text-white">
                          {dep.name}
                        </td>
                        <td className="px-4 py-3 font-mono text-emerald-400">
                          {dep.declared_version}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-mono uppercase font-semibold ${
                              dep.is_transitive === false
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                : dep.is_transitive === true
                                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {dep.is_transitive === false
                              ? 'Direct'
                              : dep.is_transitive === true
                              ? 'Transitive'
                              : 'Unconfirmed'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => handleManifestClick(dep.manifest_file)}
                            className="inline-flex items-center gap-1 font-mono text-xs text-slate-400 hover:text-emerald-300 transition"
                            title="Open manifest file in explorer"
                          >
                            <FileCode className="w-3.5 h-3.5 text-slate-400" />
                            <span>{dep.manifest_file}</span>
                            <ExternalLink className="w-3 h-3 text-slate-400" />
                          </button>
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-[11px]">
                          {dep.vulnerability_status}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="px-4 py-3 bg-slate-950/40 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Showing {filteredDependencies.length} of {data.dependencies.length} dependencies</span>
              <span>Direct dependencies confirmed by package declarations</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
