import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardHeader } from './components/DashboardHeader';
import { DashboardTab } from './components/DashboardTab';
import { DemoBanner } from './components/DemoBanner';
import { RepoOverviewTab } from './components/RepoOverviewTab';
import { FileExplorerTab } from './components/FileExplorerTab';
import { CodeQATab } from './components/CodeQATab';
import { PRReviewTab } from './components/PRReviewTab';
import { RelationshipMapTab } from './components/RelationshipMapTab';
import { SettingsTab } from './components/SettingsTab';
import { AuditLogTab } from './components/AuditLogTab';
import { Repository, IndexingStatus, UserProfile } from './types';
import { api } from './services/api';
import { Sparkles, RefreshCw, Shield } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [indexingStatus, setIndexingStatus] = useState<IndexingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [newRepoName, setNewRepoName] = useState('');
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Target file navigation state from citation clicks
  const [targetFileNav, setTargetFileNav] = useState<{
    filePath: string;
    lineRange?: [number, number];
  } | null>(null);

  useEffect(() => {
    loadRepositories();
    initUser();
  }, []);

  const initUser = async () => {
    try {
      const user = await api.getCurrentUser();
      setCurrentUser(user);
    } catch {
      try {
        const loginRes = await api.login('developer', 'DeveloperPassword123!');
        setCurrentUser(loginRes.user);
      } catch (err) {
        console.error('Failed to init user session:', err);
      }
    }
  };

  // Poll indexing status when running or queued
  useEffect(() => {
    if (!selectedRepo) return;

    let intervalId: any = null;
    const fetchStatus = async () => {
      try {
        const s = await api.getIndexingStatus(selectedRepo.id);
        setIndexingStatus(s);

        // Update selectedRepo and repositories if status changed
        setSelectedRepo((prev) => {
          if (!prev || prev.id !== s.repository_id) return prev;
          if (
            prev.indexing_status !== s.status ||
            prev.indexing_progress !== s.progress ||
            (s.indexed_commit_sha && prev.indexed_commit_sha !== s.indexed_commit_sha)
          ) {
            return {
              ...prev,
              indexing_status: s.status,
              indexing_progress: s.progress,
              indexed_commit_sha: s.indexed_commit_sha || prev.indexed_commit_sha,
              indexing_error: s.error ?? prev.indexing_error ?? null,
            };
          }
          return prev;
        });

        setRepositories((prev) =>
          prev.map((r) =>
            r.id === s.repository_id
              ? {
                  ...r,
                  indexing_status: s.status,
                  indexing_progress: s.progress,
                  indexed_commit_sha: s.indexed_commit_sha || r.indexed_commit_sha,
                  indexing_error: s.error ?? r.indexing_error ?? null,
                }
              : r
          )
        );

        if (s.status !== 'running' && s.status !== 'queued' && intervalId) {
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error(err);
      }
    };

    fetchStatus();
    intervalId = setInterval(fetchStatus, 2000);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [selectedRepo?.id, selectedRepo?.indexing_status]);

  const loadRepositories = async () => {
    setLoading(true);
    try {
      const repos = await api.getRepositories();
      setRepositories(repos);
      if (repos.length > 0) {
        setSelectedRepo((prev) => {
          if (!prev) return repos[0];
          const found = repos.find((r) => r.id === prev.id);
          return found || repos[0];
        });
      }
    } catch (err) {
      console.error('Failed to load repositories:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemoRepo = async () => {
    try {
      const demo = await api.connectRepository('reposage-demo/ecommerce-api', true);
      setRepositories((prev) => [demo, ...prev.filter((r) => r.id !== demo.id)]);
      setSelectedRepo(demo);
    } catch (err: any) {
      const existing = repositories.find((r) => r.full_name === 'reposage-demo/ecommerce-api');
      if (existing) setSelectedRepo(existing);
    }
  };

  const [connectLoading, setConnectLoading] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const parseRepoPreview = (raw: string): { repo: string; branch?: string } | null => {
    if (!raw || !raw.trim()) return null;
    let clean = raw.trim();
    if (clean.toLowerCase().startsWith('git clone ')) {
      clean = clean.slice(10).trim();
    }
    const md = clean.match(/\[.*?\]\((https?:\/\/[^\)]+)\)/);
    if (md) clean = md[1];
    clean = clean.replace(/^[<>"'`()\[\]]+|[<>"'`()\[\]]+$/g, '');
    clean = clean.split('#')[0].split('?')[0].trim();

    let branch: string | undefined;
    const branchMatch = clean.match(/\/(?:tree|blob)\/([^\/]+)/);
    if (branchMatch) {
      branch = branchMatch[1];
    }

    if (clean.includes('@') && !clean.startsWith('http')) {
      if (clean.startsWith('ssh://')) clean = clean.slice(6);
      clean = clean.split('@')[1] || clean;
      clean = clean.replace(/:\d+\//, '/').replace(':', '/');
    }
    if (clean.includes('://')) {
      clean = clean.split('://')[1] || clean;
    }
    if (clean.includes('@')) {
      clean = clean.split('@')[1] || clean;
    }
    clean = clean.replace(/^(?:www\.)?(?:localhost|[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+)(?::\d+)?\//, '');
    const parts = clean.split('/').filter(Boolean);
    if (parts.length >= 2) {
      let repoName = parts[1];
      if (repoName.endsWith('.git')) repoName = repoName.slice(0, -4);
      return { repo: `${parts[0]}/${repoName}`, branch };
    } else if (parts.length === 1) {
      let repoName = parts[0];
      if (repoName.endsWith('.git')) repoName = repoName.slice(0, -4);
      return { repo: `user/${repoName}`, branch };
    }
    return null;
  };

  const handleConnectRepo = async () => {
    if (!newRepoName.trim()) return;
    setConnectLoading(true);
    setConnectError(null);
    try {
      const repo = await api.connectRepository(newRepoName.trim(), false);
      setRepositories((prev) => [repo, ...prev.filter((r) => r.id !== repo.id)]);
      setSelectedRepo(repo);
      setShowConnectModal(false);
      setNewRepoName('');
    } catch (err: any) {
      const errMsg = err.message || '';
      if (errMsg.toLowerCase().includes('already connected')) {
        try {
          const allRepos = await api.getRepositories();
          setRepositories(allRepos);
          const preview = parseRepoPreview(newRepoName.trim());
          const target = (preview ? preview.repo : newRepoName.trim()).toLowerCase();
          const existing = allRepos.find(
            (r) =>
              r.full_name.toLowerCase() === target ||
              r.full_name.toLowerCase().includes(target) ||
              target.includes(r.full_name.toLowerCase())
          );
          if (existing) {
            setSelectedRepo(existing);
            setShowConnectModal(false);
            setNewRepoName('');
            if (existing.indexing_status === 'not_indexed') {
              api.triggerIndexing(existing.id, false).catch(console.error);
            }
            return;
          }
        } catch (fetchErr) {
          console.error('Failed to resolve existing repository:', fetchErr);
        }
      }
      setConnectError(err.message || 'Failed to connect repository.');
    } finally {
      setConnectLoading(false);
    }
  };

  const handleDisconnectRepo = async (repoId: number) => {
    const target = repositories.find((r) => r.id === repoId);
    if (!target) return;
    const confirmDelete = window.confirm(`Disconnect repository '${target.full_name}'? Indexed data and code chunks will be removed.`);
    if (!confirmDelete) return;

    try {
      await api.disconnectRepository(repoId);
      const remaining = repositories.filter((r) => r.id !== repoId);
      setRepositories(remaining);
      setSelectedRepo(remaining.length > 0 ? remaining[0] : null);
    } catch (err: any) {
      alert(`Failed to disconnect repository: ${err.message}`);
    }
  };

  const handleNavigateToFile = (
    filePath: string,
    lineRangeOrStart?: [number, number] | number,
    endLine?: number
  ) => {
    let range: [number, number] | undefined = undefined;
    if (Array.isArray(lineRangeOrStart)) {
      range = lineRangeOrStart;
    } else if (typeof lineRangeOrStart === 'number') {
      range = [lineRangeOrStart, typeof endLine === 'number' ? endLine : lineRangeOrStart];
    }
    setTargetFileNav({ filePath, lineRange: range });
    setActiveTab('explorer');
  };

  const isDemoRepoLoaded = repositories.some(
    (r) => r.full_name === 'reposage-demo/ecommerce-api'
  );

  return (
    <div className="min-h-screen bg-paleLime-canvas p-2 sm:p-3 md:p-4 lg:p-5 flex flex-col md:flex-row gap-4 font-sans text-slate-800 antialiased">
      {/* Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        repositories={repositories}
        selectedRepo={selectedRepo}
        onSelectRepo={(r) => {
          setSelectedRepo(r);
          setTargetFileNav(null);
        }}
        onOpenConnectModal={() => setShowConnectModal(true)}
        onDisconnectRepo={handleDisconnectRepo}
        indexingStatus={indexingStatus}
        onReindex={() => selectedRepo && api.triggerIndexing(selectedRepo.id, false)}
        currentUser={currentUser}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0 bg-white md:rounded-3xl border border-[#e2e8df] shadow-sm overflow-hidden">
        {/* Dashboard Header with repo switcher, file search, and alerts */}
        <DashboardHeader
          repositories={repositories}
          selectedRepo={selectedRepo}
          onSelectRepo={(r) => {
            setSelectedRepo(r);
            setTargetFileNav(null);
          }}
          onOpenConnectModal={() => setShowConnectModal(true)}
          indexingStatus={indexingStatus}
          onReindex={() => selectedRepo && api.triggerIndexing(selectedRepo.id, false)}
          onNavigateToFile={handleNavigateToFile}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        />

        <DemoBanner
          onLoadDemoRepo={handleLoadDemoRepo}
          isDemoRepoLoaded={isDemoRepoLoaded}
        />

        {/* Content Body */}
        <main className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 bg-slate-50/40">
          {loading ? (
            <div className="p-16 text-center text-slate-500 text-sm flex flex-col items-center gap-3">
              <RefreshCw className="w-6 h-6 text-lime-500 animate-spin" />
              <span>Loading RepoSage intelligence workspace...</span>
            </div>
          ) : !selectedRepo ? (
            <div className="p-12 text-center bg-white border border-[#e2e8df] rounded-3xl space-y-4 max-w-lg mx-auto mt-12 shadow-sm">
              <div className="w-12 h-12 rounded-2xl bg-lime-100 border border-lime-300 flex items-center justify-center text-lime-700 mx-auto">
                <Shield className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">No Connected Repository</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                Connect a GitHub repository or load a sample repository to inspect code symbols, view 4-tier architecture, and run evidence-grounded security reviews.
              </p>
              <div className="flex justify-center gap-2 pt-2">
                <button
                  onClick={handleLoadDemoRepo}
                  className="px-4 py-2 rounded-2xl bg-lime-400 hover:bg-lime-300 text-charcoal-900 text-xs font-bold transition shadow-sm"
                >
                  Load Sample Repository
                </button>
                <button
                  onClick={() => setShowConnectModal(true)}
                  className="px-4 py-2 rounded-2xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition"
                >
                  Connect Repository
                </button>
              </div>
            </div>
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <DashboardTab
                  key={`dashboard-${selectedRepo.id}-${selectedRepo.indexed_commit_sha || 'head'}`}
                  repo={selectedRepo}
                  indexingStatus={indexingStatus}
                  onNavigateToFile={handleNavigateToFile}
                  onSwitchTab={setActiveTab}
                  onReindex={() => selectedRepo && api.triggerIndexing(selectedRepo.id, false)}
                />
              )}
              {activeTab === 'explorer' && (
                <FileExplorerTab
                  key={`explorer-${selectedRepo.id}-${selectedRepo.indexed_commit_sha || 'head'}`}
                  repo={selectedRepo}
                  initialFilePath={targetFileNav?.filePath}
                  initialLineRange={targetFileNav?.lineRange}
                  onClearInitialNav={() => setTargetFileNav(null)}
                />
              )}
              {activeTab === 'overview' && (
                <RepoOverviewTab
                  key={`overview-${selectedRepo.id}-${selectedRepo.indexed_commit_sha || 'head'}`}
                  repo={selectedRepo}
                  onRefresh={loadRepositories}
                  indexingStatus={indexingStatus}
                  onNavigateToFile={handleNavigateToFile}
                />
              )}
              {activeTab === 'qa' && (
                <CodeQATab
                  key={`qa-${selectedRepo.id}-${selectedRepo.indexed_commit_sha || 'head'}`}
                  repo={selectedRepo}
                  onNavigateToFile={handleNavigateToFile}
                />
              )}
              {activeTab === 'reviews' && (
                <PRReviewTab
                  key={`reviews-${selectedRepo.id}-${selectedRepo.indexed_commit_sha || 'head'}`}
                  repo={selectedRepo}
                  onNavigateToFile={handleNavigateToFile}
                />
              )}
              {activeTab === 'relationships' && (
                <RelationshipMapTab
                  key={`rel-${selectedRepo.id}-${selectedRepo.indexed_commit_sha || 'head'}`}
                  repo={selectedRepo}
                />
              )}
              {activeTab === 'settings' && (
                <SettingsTab
                  key={`settings-${selectedRepo.id}-${selectedRepo.indexed_commit_sha || 'head'}`}
                  repo={selectedRepo}
                  onRefresh={loadRepositories}
                  onDisconnect={handleDisconnectRepo}
                />
              )}
              {activeTab === 'audit' && <AuditLogTab />}
            </>
          )}
        </main>
      </div>

      {/* Connect Repository Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-charcoal-950/70 backdrop-blur-sm">
          <div className="bg-white border border-[#e2e8df] rounded-3xl p-6 sm:p-7 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-lg flex items-center gap-2">
                <span className="p-1.5 rounded-xl bg-lime-100 text-lime-700">
                  <Sparkles className="w-4 h-4" />
                </span>
                Connect Repository
              </h3>
              <button
                onClick={() => {
                  setShowConnectModal(false);
                  setConnectError(null);
                }}
                className="text-slate-400 hover:text-slate-700 text-lg leading-none p-1 rounded-lg"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">
              Enter any GitHub URL or full repository name (e.g.{' '}
              <span className="font-mono text-lime-700 font-semibold">owner/repo</span>,{' '}
              <span className="font-mono text-lime-700 font-semibold">https://github.com/owner/repo</span>, or{' '}
              <span className="font-mono text-lime-700 font-semibold">git clone ...</span>). RepoSage automatically extracts the repository name and branch.
            </p>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-900 leading-relaxed flex gap-2">
              <span className="mt-0.5 flex-shrink-0">⚠️</span>
              <span>
                <strong>Demo Mode active.</strong> To index real GitHub repositories, configure{' '}
                <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[11px]">GITHUB_TOKEN=ghp_...</code>{' '}
                in <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[11px]">backend/.env</code>.
              </span>
            </div>

            <div className="space-y-1">
              <input
                type="text"
                placeholder="https://github.com/owner/repo or owner/repo"
                value={newRepoName}
                onChange={(e) => {
                  setNewRepoName(e.target.value);
                  if (connectError) setConnectError(null);
                }}
                onKeyDown={(e) => e.key === 'Enter' && !connectLoading && handleConnectRepo()}
                className="w-full px-3.5 py-2.5 text-xs bg-slate-50 border border-[#e2e8df] rounded-2xl text-slate-800 placeholder-slate-400 focus:outline-none focus:border-lime-500 font-mono transition"
                autoFocus
              />

              {parseRepoPreview(newRepoName) && (
                <div className="pt-1.5 px-1 flex items-center gap-2 text-xs font-mono text-lime-700">
                  <span className="text-slate-400">Detected:</span>
                  <span className="font-bold">{parseRepoPreview(newRepoName)?.repo}</span>
                  {parseRepoPreview(newRepoName)?.branch && (
                    <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200 text-[10px]">
                      branch: {parseRepoPreview(newRepoName)?.branch}
                    </span>
                  )}
                </div>
              )}
            </div>

            {connectError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-700 leading-relaxed">
                {connectError}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setShowConnectModal(false);
                  setConnectError(null);
                }}
                className="px-4 py-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConnectRepo}
                disabled={connectLoading || !newRepoName.trim()}
                className="px-4 py-2 rounded-2xl bg-lime-400 hover:bg-lime-300 disabled:opacity-50 text-charcoal-900 text-xs font-bold shadow-sm transition flex items-center gap-1.5"
              >
                {connectLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  'Connect & Index'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
