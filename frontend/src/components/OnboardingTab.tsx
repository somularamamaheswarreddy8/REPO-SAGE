import React, { useState, useEffect, useRef } from 'react';
import {
  Compass,
  FileCode,
  Layers,
  GitFork,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  HelpCircle,
} from 'lucide-react';
import { api } from '../services/api';
import { Repository, RepositoryOnboarding } from '../types';

interface OnboardingTabProps {
  repository: Repository;
  onNavigateToFile?: (filePath: string, startLine?: number, endLine?: number) => void;
}

export const OnboardingTab: React.FC<OnboardingTabProps> = ({
  repository,
  onNavigateToFile,
}) => {
  const [data, setData] = useState<RepositoryOnboarding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeRepoIdRef = useRef<number>(repository.id);

  useEffect(() => {
    activeRepoIdRef.current = repository.id;
    setData(null);
    setError(null);
    loadOnboarding();
  }, [repository.id, repository.indexed_commit_sha]);

  const loadOnboarding = async () => {
    const targetRepoId = repository.id;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await api.getOnboardingGuide(targetRepoId);
      if (activeRepoIdRef.current !== targetRepoId) return;
      setData(res);
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setError(err.message || 'Failed to load onboarding guide.');
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setLoading(false);
      }
    }
  };

  const handleCitationClick = (citation: string, filePath?: string, startLine?: number, endLine?: number) => {
    if (!onNavigateToFile) return;
    if (citation.includes('Not confirmed') || !filePath || filePath === 'Not detected') return;

    if (startLine && endLine) {
      onNavigateToFile(filePath, startLine, endLine);
    } else {
      const match = citation.match(/^([^:]+):(\d+)(?:-(\d+))?$/);
      if (match) {
        const path = match[1];
        const s = parseInt(match[2], 10);
        const e = match[3] ? parseInt(match[3], 10) : s;
        onNavigateToFile(path, s, e);
      } else {
        onNavigateToFile(filePath, 1, 1);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-slate-400 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="text-sm">Synthesizing repository onboarding guide and verifying citations...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
        <div className="flex items-center gap-3 text-rose-400">
          <AlertTriangle className="w-6 h-6" />
          <h3 className="font-semibold text-white">Unable to Load Onboarding Guide</h3>
        </div>
        <p className="text-xs text-slate-400">{error || 'No onboarding data available.'}</p>
        <button
          onClick={loadOnboarding}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-500/30 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <Compass className="w-6 h-6 text-emerald-400" />
              <h2 className="text-xl font-bold text-white tracking-tight">
                Repository Onboarding Guide
              </h2>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
                Start Here
              </span>
            </div>
            <p className="text-xs text-slate-300 max-w-3xl leading-relaxed">
              {data.overview_summary}
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-slate-400 bg-slate-950/60 p-3 rounded-xl border border-slate-800 shrink-0">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-sans">Branch</div>
              <div className="text-emerald-300 font-semibold">{data.branch}</div>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-sans">Commit</div>
              <div className="text-slate-300">{data.commit_sha ? data.commit_sha.slice(0, 8) : 'HEAD'}</div>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-sans">Modules</div>
              <div className="text-white font-bold">{data.total_modules}</div>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Evidence-grounded: Every claim is linked to verified source lines or marked &quot;Not confirmed&quot;.</span>
          </div>
          <button
            onClick={loadOnboarding}
            className="flex items-center gap-1 text-slate-400 hover:text-white transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh Guide</span>
          </button>
        </div>
      </div>

      {/* Grid: Entry Points & Key Modules */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Likely Entry Points */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <FileCode className="w-4 h-4 text-emerald-400" />
              Likely Application Entry Points
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">
              {data.entry_points.length} detected
            </span>
          </div>

          <div className="space-y-3">
            {data.entry_points.map((entry, idx) => (
              <div
                key={idx}
                className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-xs font-semibold text-emerald-300 truncate">
                      {entry.file_path}
                    </span>
                    {entry.symbol && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {entry.symbol}
                      </span>
                    )}
                  </div>
                  {entry.confirmed ? (
                    <button
                      onClick={() => handleCitationClick(entry.citation, entry.file_path, entry.start_line, entry.end_line)}
                      className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 transition shrink-0"
                      title="Open source file and line range"
                    >
                      <span>{entry.citation}</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  ) : (
                    <span className="text-[10px] text-amber-400 font-mono bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                      Not confirmed from indexed files.
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">{entry.reason}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Important Modules and Responsibilities */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              Core Modules &amp; Responsibilities
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">
              {data.modules.length} modules
            </span>
          </div>

          <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
            {data.modules.map((mod, idx) => (
              <div
                key={idx}
                className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-semibold text-white truncate">
                    {mod.module_name}
                  </span>
                  <button
                    onClick={() => handleCitationClick(mod.citation, mod.file_path, mod.start_line, mod.end_line)}
                    className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 transition shrink-0"
                  >
                    <span>{mod.citation}</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
                <p className="text-xs text-slate-300">{mod.responsibility}</p>
                {mod.symbols.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {mod.symbols.slice(0, 5).map((sym, sIdx) => (
                      <span
                        key={sIdx}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 font-mono"
                      >
                        {sym}
                      </span>
                    ))}
                    {mod.symbols.length > 5 && (
                      <span className="text-[10px] text-slate-400">+{mod.symbols.length - 5} more</span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Module Connections (Static Architecture Graph) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <GitFork className="w-4 h-4 text-emerald-400" />
              How Major Modules Connect
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Statically verified imports and call connections across indexed repository files.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {data.module_connections.length} connections
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.module_connections.map((conn, idx) => (
            <div
              key={idx}
              className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-mono">
                  <span className="text-emerald-300 font-semibold">{conn.source_module.split('/').pop()}</span>
                  <span className="text-slate-400">&rarr;</span>
                  <span className="text-cyan-300 font-semibold">{conn.target_module.split('/').pop()}</span>
                </div>
                {conn.confirmed ? (
                  <button
                    onClick={() => handleCitationClick(conn.citation, conn.file_path, conn.line_number, conn.line_number)}
                    className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20"
                  >
                    <span>{conn.citation}</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                ) : (
                  <span className="text-[10px] text-amber-400 font-mono bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                    Not confirmed from indexed files.
                  </span>
                )}
              </div>
              <div className="text-xs text-slate-400 flex items-center gap-2">
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-900 text-slate-300 uppercase font-mono">
                  {conn.relationship_type}
                </span>
                <span className="text-slate-300 font-mono text-[11px] truncate">
                  {conn.source_symbol} &rarr; {conn.target_symbol}
                </span>
              </div>
              {conn.evidence_snippet && (
                <pre className="text-[11px] font-mono p-2 bg-slate-900 border border-slate-800/80 rounded text-slate-300 overflow-x-auto">
                  {conn.evidence_snippet}
                </pre>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Existing Tests for Modules */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Existing Tests for Modules
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Verified test suites corresponding to primary architectural modules.
            </p>
          </div>
        </div>

        <div className="space-y-2.5">
          {data.module_tests.map((test, idx) => (
            <div
              key={idx}
              className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-3 hover:border-slate-700 transition"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-semibold text-white">
                    {test.module_path}
                  </span>
                  {test.has_tests ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      Tests Found
                    </span>
                  ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 font-semibold flex items-center gap-1">
                      <HelpCircle className="w-3 h-3" />
                      Not confirmed from indexed files.
                    </span>
                  )}
                </div>
                {test.has_tests && test.test_cases.length > 0 && (
                  <div className="text-[11px] text-slate-400">
                    Test cases: {test.test_cases.join(', ')}
                  </div>
                )}
              </div>

              {test.has_tests && test.test_file ? (
                <button
                  onClick={() => handleCitationClick(test.citation, test.test_file || undefined, test.start_line || 1, test.end_line || 1)}
                  className="inline-flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 font-mono bg-emerald-500/10 px-3 py-1 rounded-lg border border-emerald-500/20 shrink-0 self-start md:self-auto"
                >
                  <span>{test.citation}</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              ) : (
                <span className="text-xs text-slate-400 font-mono shrink-0">
                  Not confirmed from indexed files.
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
