import React, { useState, useEffect, useRef } from 'react';
import {
  Repository,
  IndexingStatus,
} from '../types';
import { api } from '../services/api';
import {
  Search,
  ChevronDown,
  RefreshCw,
  GitBranch,
  GitCommit,
  FileCode2,
  AlertCircle,
  Menu,
  Lock,
} from 'lucide-react';

interface DashboardHeaderProps {
  repositories: Repository[];
  selectedRepo: Repository | null;
  onSelectRepo: (repo: Repository) => void;
  onOpenConnectModal: () => void;
  indexingStatus: IndexingStatus | null;
  onReindex: () => void;
  onNavigateToFile: (filePath: string, lineRange?: [number, number]) => void;
  onToggleMobileSidebar?: () => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  repositories,
  selectedRepo,
  onSelectRepo,
  onOpenConnectModal,
  indexingStatus,
  onReindex,
  onNavigateToFile,
  onToggleMobileSidebar,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Debounced search for files
  useEffect(() => {
    if (!selectedRepo || !searchQuery.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const treeRes = await api.getRepositoryTree(selectedRepo.id, {
          search: searchQuery.trim(),
          limit: 8,
        });
        setSearchResults(treeRes.files || []);
        setShowSearchResults(true);
      } catch (err) {
        console.error('File search error:', err);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery, selectedRepo?.id]);

  // Click outside listener for search popup
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        searchContainerRef.current &&
        !searchContainerRef.current.contains(e.target as Node)
      ) {
        setShowSearchResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isIndexing =
    indexingStatus?.status === 'running' ||
    indexingStatus?.status === 'queued' ||
    selectedRepo?.indexing_status === 'running' ||
    selectedRepo?.indexing_status === 'queued';

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-[#e5eae3] px-4 sm:px-6 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
      {/* Top / Left: Mobile hamburger + Selected Repo Info & Switcher */}
      <div className="flex items-center gap-3 min-w-0">
        {onToggleMobileSidebar && (
          <button
            onClick={onToggleMobileSidebar}
            className="md:hidden p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            aria-label="Toggle navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Repository Switcher Pill */}
        <div className="relative shrink-0">
          <select
            value={selectedRepo?.id ?? ''}
            onChange={(e) => {
              const val = e.target.value;
              if (val === '__connect__') {
                onOpenConnectModal();
              } else {
                const found = repositories.find((r) => r.id === Number(val));
                if (found) onSelectRepo(found);
              }
            }}
            className="appearance-none bg-slate-50 hover:bg-slate-100 border border-[#e2e8df] rounded-2xl pl-3 pr-8 py-2 text-xs font-bold text-slate-800 focus:outline-none focus:border-lime-500 cursor-pointer shadow-sm transition max-w-[220px] sm:max-w-[260px] truncate"
            title="Switch active repository"
          >
            {repositories.map((r) => (
              <option key={r.id} value={r.id}>
                {r.full_name} {r.is_demo ? '(Demo)' : ''}
              </option>
            ))}
            <option value="__connect__">+ Connect New Repository...</option>
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-3 pointer-events-none" />
        </div>

        {/* Selected Repo Details */}
        {selectedRepo && (
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500 min-w-0">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-700">
              <GitBranch className="w-3 h-3 text-slate-400" />
              <span>{selectedRepo.default_branch}</span>
            </span>

            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-700">
              <GitCommit className="w-3 h-3 text-slate-400" />
              <span>{selectedRepo.indexed_commit_sha ? selectedRepo.indexed_commit_sha.slice(0, 7) : 'HEAD'}</span>
            </span>

            {selectedRepo.is_demo && (
              <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold">
                Demo
              </span>
            )}

            {/* Index Freshness & Status */}
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-xl text-[10px] font-semibold border ${
                selectedRepo.indexing_status === 'completed' && !selectedRepo.is_stale
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : isIndexing
                  ? 'bg-amber-50 border-amber-200 text-amber-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}
              title={
                selectedRepo.last_indexed_at
                  ? `Last indexed: ${new Date(selectedRepo.last_indexed_at).toLocaleString()}`
                  : 'Never indexed'
              }
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  selectedRepo.indexing_status === 'completed' && !selectedRepo.is_stale
                    ? 'bg-emerald-500'
                    : isIndexing
                    ? 'bg-amber-500 animate-pulse'
                    : 'bg-rose-500'
                }`}
              />
              <span>
                {isIndexing
                  ? 'Indexing'
                  : selectedRepo.indexing_status === 'completed'
                  ? selectedRepo.is_stale
                    ? 'Stale Index'
                    : 'Current'
                  : 'Unindexed'}
              </span>
            </span>
          </div>
        )}
      </div>

      {/* Center / Right: Interactive Search, Notifications, Reindex Button */}
      <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
        {/* Real-Time File Search */}
        <div ref={searchContainerRef} className="relative flex-1 md:w-72 lg:w-80">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Search repository files & code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => searchResults.length > 0 && setShowSearchResults(true)}
              className="w-full pl-8 pr-8 py-1.5 text-xs bg-slate-50 border border-[#e2e8df] rounded-2xl text-slate-800 placeholder-slate-400 focus:outline-none focus:border-lime-500 focus:bg-white shadow-inner transition"
            />
            {isSearching && (
              <RefreshCw className="w-3 h-3 text-lime-600 animate-spin absolute right-3 top-2.5" />
            )}
          </div>

          {/* Search Dropdown Results */}
          {showSearchResults && searchResults.length > 0 && (
            <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-[#e2e8df] rounded-2xl shadow-xl z-50 overflow-hidden max-h-72 overflow-y-auto">
              <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider bg-slate-50 border-b border-slate-100">
                Matching Files ({searchResults.length})
              </div>
              {searchResults.map((f, i) => (
                <div
                  key={i}
                  onClick={() => {
                    onNavigateToFile(f.file_path);
                    setShowSearchResults(false);
                    setSearchQuery('');
                  }}
                  className="px-3 py-2 hover:bg-lime-50/60 cursor-pointer transition border-b border-slate-50 last:border-0 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileCode2 className="w-3.5 h-3.5 text-lime-600 shrink-0" />
                    <span className="font-mono text-slate-700 truncate">{f.file_path}</span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 shrink-0 ml-2">
                    {f.language_display || 'file'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Zero Leakage Badge */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-lime-50 border border-lime-200 text-lime-800 text-[11px] font-semibold shrink-0">
          <Lock className="w-3 h-3 text-lime-600" />
          <span>Zero-Leakage</span>
        </div>

        {/* Indexing Alert Indicator */}
        {selectedRepo?.indexing_status === 'failed' && (
          <div className="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-[11px] font-semibold shrink-0">
            <AlertCircle className="w-3 h-3 text-rose-500" />
            <span>Index Alert</span>
          </div>
        )}

        {/* Re-index Action Button */}
        {selectedRepo && (
          <button
            onClick={onReindex}
            disabled={isIndexing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-2xl bg-slate-900 hover:bg-slate-800 text-white disabled:opacity-50 text-xs font-semibold shadow-sm transition shrink-0"
            title="Re-index repository code and refresh analysis"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-lime-400 ${isIndexing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{isIndexing ? 'Indexing...' : 'Re-index'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
