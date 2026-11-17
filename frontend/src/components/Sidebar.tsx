import React from 'react';
import {
  LayoutDashboard,
  FolderTree,
  Code2,
  Sparkles,
  GitPullRequest,
  Network,
  History,
  Settings,
  Shield,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Plus,
  Lock,
  ChevronDown,
  User as UserIcon,
  X,
} from 'lucide-react';
import { Repository, IndexingStatus, UserProfile } from '../types';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  repositories: Repository[];
  selectedRepo: Repository | null;
  onSelectRepo: (repo: Repository) => void;
  onOpenConnectModal: () => void;
  onDisconnectRepo: (repoId: number) => void;
  indexingStatus: IndexingStatus | null;
  onReindex: () => void;
  currentUser?: UserProfile | null;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  repositories,
  selectedRepo,
  onSelectRepo,
  onOpenConnectModal,
  onDisconnectRepo,
  indexingStatus,
  onReindex,
  currentUser,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  // Core navigation items supporting essential workflows
  const primaryNavItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, description: 'Intelligence metrics & activity' },
    { id: 'explorer', label: 'File Explorer', icon: FolderTree, description: 'Searchable tree & syntax preview' },
    { id: 'overview', label: 'Repository Overview', icon: Code2, description: 'Deep architecture & modules' },
    { id: 'qa', label: 'Code Q&A', icon: Sparkles, description: 'Evidence-grounded code search' },
    { id: 'reviews', label: 'PR Reviews', icon: GitPullRequest, description: 'Security diff review & audits' },
    { id: 'relationships', label: 'System Architecture', icon: Network, description: '4-tier component map' },
    { id: 'audit', label: 'Audit Log', icon: History, description: 'Approval & publish trace' },
    { id: 'settings', label: 'Settings & Eval', icon: Settings, description: 'CI check & benchmarks' },
  ];

  const getStatusBadge = () => {
    if (!selectedRepo) return null;
    const status = indexingStatus?.status || selectedRepo.indexing_status;
    const progress = indexingStatus?.progress ?? selectedRepo.indexing_progress;

    if (status === 'running') {
      return (
        <div className="flex items-center gap-1.5 text-xs text-sky-400 font-mono">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          <span>Indexing ({Math.round(progress)}%)</span>
        </div>
      );
    }
    if (status === 'completed') {
      return (
        <div className="flex items-center gap-1.5 text-xs text-lime-400 font-mono">
          <CheckCircle2 className="w-3.5 h-3.5 text-lime-400" />
          <span>Indexed & Grounded</span>
        </div>
      );
    }
    if (status === 'failed') {
      return (
        <div className="flex items-center gap-1.5 text-xs text-rose-400 font-mono">
          <AlertCircle className="w-3.5 h-3.5" />
          <span>Indexing Failed</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
        <span className="w-2 h-2 rounded-full bg-slate-500"></span>
        <span>Not Indexed</span>
      </div>
    );
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-40 md:hidden"
        />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 w-72 bg-charcoal-900 border-r md:border border-charcoal-800 md:rounded-3xl flex flex-col flex-shrink-0 min-h-screen md:min-h-[calc(100vh-2.5rem)] shadow-xl transition-transform duration-300 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="p-4 sm:p-5 border-b border-charcoal-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-2xl bg-lime-400 text-charcoal-900 flex items-center justify-center font-black shadow-md shadow-lime-900/30">
              <Shield className="w-5 h-5 text-charcoal-900 fill-charcoal-900" />
            </div>
            <div>
              <div className="font-extrabold text-sm tracking-tight text-white flex items-center gap-1.5">
                RepoSage
                <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-lime-400/10 text-lime-400 border border-lime-400/30">
                  AI
                </span>
              </div>
              <div className="text-[10px] text-charcoal-500">Code Intelligence & Review</div>
            </div>
          </div>

          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="md:hidden text-charcoal-500 hover:text-white p-1 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* User Card */}
        <div className="p-3 border-b border-charcoal-800 bg-charcoal-850/60 mx-3 my-2 rounded-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              {currentUser?.avatar_url ? (
                <img
                  src={currentUser.avatar_url}
                  alt={currentUser.username}
                  className="w-5 h-5 rounded-full border border-charcoal-700 shrink-0"
                />
              ) : (
                <UserIcon className="w-4 h-4 text-lime-400 shrink-0" />
              )}
              <span className="text-xs font-semibold text-slate-200 truncate">
                {currentUser?.username || 'developer'}
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-lime-400/10 text-lime-300 border border-lime-400/20">
              Authenticated
            </span>
          </div>
        </div>

        {/* Active Repository Switcher in Sidebar */}
        <div className="p-3 border-b border-charcoal-800 bg-charcoal-850/60 mx-3 mb-2 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-[11px] text-charcoal-500 uppercase font-bold tracking-wider">
            <span>Repository</span>
            <button
              onClick={onOpenConnectModal}
              className="flex items-center gap-1 text-lime-400 hover:text-lime-300 transition text-[10px] font-semibold"
              title="Connect a GitHub repository"
            >
              <Plus className="w-3 h-3" />
              Connect
            </button>
          </div>

          {repositories.length > 0 ? (
            <div className="relative">
              <select
                value={selectedRepo?.id ?? ''}
                onChange={(e) => {
                  const r = repositories.find((item) => item.id === Number(e.target.value));
                  if (r) onSelectRepo(r);
                }}
                className="w-full appearance-none bg-charcoal-800 border border-charcoal-700 rounded-xl px-2.5 py-1.5 pr-7 text-xs font-semibold text-slate-200 focus:outline-none focus:border-lime-400 cursor-pointer truncate"
              >
                {repositories.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.full_name} {r.is_demo ? '(Demo)' : ''}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          ) : (
            <div className="text-xs text-charcoal-500 py-1">No repositories connected.</div>
          )}
        </div>

        {/* Navigation Items */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
          <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-charcoal-500">
            Workspace Navigation
          </div>

          {primaryNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  if (onCloseMobile) onCloseMobile();
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-2xl text-xs font-medium text-left transition-all ${
                  isActive
                    ? 'bg-lime-400 text-charcoal-900 font-bold shadow-md shadow-lime-950/20'
                    : 'text-slate-300 hover:text-white hover:bg-charcoal-800'
                }`}
              >
                <Icon
                  className={`w-4 h-4 flex-shrink-0 ${
                    isActive ? 'text-charcoal-900' : 'text-slate-400'
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="text-xs leading-none truncate">{item.label}</div>
                  <div
                    className={`text-[10px] mt-0.5 truncate ${
                      isActive ? 'text-charcoal-800 opacity-90' : 'text-charcoal-500'
                    }`}
                  >
                    {item.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Repository Status Section at Bottom of Sidebar */}
        {selectedRepo && (
          <div className="p-3 border-t border-charcoal-800 bg-charcoal-850/80 m-3 rounded-2xl space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold tracking-wider text-charcoal-500">
                Repository Status
              </span>
              <button
                onClick={onReindex}
                className="p-1 rounded hover:bg-charcoal-800 text-charcoal-500 hover:text-lime-400 transition"
                title="Re-index repository"
              >
                <RefreshCw
                  className={`w-3 h-3 ${
                    indexingStatus?.status === 'running' ? 'animate-spin text-lime-400' : ''
                  }`}
                />
              </button>
            </div>

            <div>{getStatusBadge()}</div>

            <div className="text-[11px] font-mono text-charcoal-500 truncate flex items-center justify-between pt-1 border-t border-charcoal-800">
              <span className="truncate">{selectedRepo.name}</span>
              <button
                onClick={() => onDisconnectRepo(selectedRepo.id)}
                className="text-[10px] text-charcoal-500 hover:text-rose-400 transition"
                title="Disconnect repository"
              >
                Disconnect
              </button>
            </div>

            <div className="flex items-center gap-1.5 pt-1 text-[10px] text-lime-400/90 font-medium">
              <Lock className="w-3 h-3 text-lime-400" />
              <span>Zero-Leakage Protection Active</span>
            </div>
          </div>
        )}
      </aside>
    </>
  );
};
