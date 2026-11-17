import React, { useState, useEffect, useRef } from 'react';
import {
  GitPullRequest,
  AlertCircle,
  CheckCircle,
  HelpCircle,
  Layers,
  ArrowRight,
  ExternalLink,
  RefreshCw,
  Code2,
  FileCheck,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../services/api';
import { Repository, PRReview, PRImpactAnalysis } from '../types';

interface ChangeImpactTabProps {
  repository: Repository;
  onNavigateToFile?: (filePath: string, startLine?: number, endLine?: number) => void;
}

export const ChangeImpactTab: React.FC<ChangeImpactTabProps> = ({
  repository,
  onNavigateToFile,
}) => {
  const [reviews, setReviews] = useState<PRReview[]>([]);
  const [selectedReviewId, setSelectedReviewId] = useState<number | null>(null);
  const [impactData, setImpactData] = useState<PRImpactAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeRepoIdRef = useRef<number>(repository.id);

  useEffect(() => {
    activeRepoIdRef.current = repository.id;
    setReviews([]);
    setSelectedReviewId(null);
    setImpactData(null);
    setError(null);
    loadReviews();
  }, [repository.id, repository.indexed_commit_sha]);

  useEffect(() => {
    if (selectedReviewId) {
      loadImpact(selectedReviewId);
    }
  }, [selectedReviewId]);

  const loadReviews = async () => {
    const targetRepoId = repository.id;
    setLoading(true);
    setError(null);
    try {
      const list = await api.listReviews(targetRepoId);
      if (activeRepoIdRef.current !== targetRepoId) return;
      setReviews(list);
      if (list.length > 0) {
        setSelectedReviewId(list[0].id);
      } else {
        setImpactData(null);
        setLoading(false);
      }
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setError(err.message || 'Failed to load repository PR reviews.');
      setLoading(false);
    }
  };

  const loadImpact = async (reviewId: number) => {
    const targetRepoId = repository.id;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getPRImpact(targetRepoId, reviewId);
      if (activeRepoIdRef.current !== targetRepoId) return;
      setImpactData(data);
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setError(err.message || 'Failed to analyze PR impact.');
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setLoading(false);
      }
    }
  };

  const handleCitationClick = (citation: string, filePath?: string, startLine?: number, endLine?: number) => {
    if (!onNavigateToFile) return;
    if (citation.includes('Not confirmed') || !filePath) return;

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

  return (
    <div className="space-y-6">
      {/* Header & PR Selector */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <GitPullRequest className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-bold text-white tracking-tight">
                Pull-Request Change Impact Analysis &amp; Test-Gap Advisor
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              Statically traces downstream dependents, affected tests, untraced dynamic areas, and missing test coverage.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {reviews.length > 0 && (
              <select
                value={selectedReviewId || ''}
                onChange={(e) => setSelectedReviewId(Number(e.target.value))}
                className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500 font-mono"
              >
                {reviews.map((r) => (
                  <option key={r.id} value={r.id}>
                    PR #{r.pr_number}: {r.title.slice(0, 40)}
                  </option>
                ))}
              </select>
            )}

            <button
              onClick={() => selectedReviewId && loadImpact(selectedReviewId)}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-[11px] text-slate-400 gap-2">
          <span>{impactData?.execution_policy || 'Static analysis only. Repository code is never executed.'}</span>
          <span className="text-emerald-400/90 font-mono">
            {impactData?.coverage_notice || 'Gaps statically inferred from indexed source and test symbols.'}
          </span>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 text-slate-400 space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
          <p className="text-sm">Tracing static symbols, downstream callers, and test gaps...</p>
        </div>
      ) : error || !impactData ? (
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
          <div className="flex items-center gap-3 text-rose-400">
            <AlertCircle className="w-6 h-6" />
            <h3 className="font-semibold text-white">Impact Analysis Unavailable</h3>
          </div>
          <p className="text-xs text-slate-400">{error || 'No pull request review selected or available.'}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Changed Files & Key Symbols */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-sm">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Code2 className="w-4 h-4 text-emerald-400" />
              Changed Files &amp; Key Modified Symbols
            </h3>

            <div className="space-y-3">
              {impactData.changed_files.map((cf, idx) => (
                <div
                  key={idx}
                  className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-mono text-xs font-semibold text-emerald-300">
                        {cf.file_path}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase font-mono">
                        {cf.change_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className="text-emerald-400">+{cf.additions}</span>
                      <span className="text-rose-400">-{cf.deletions}</span>
                    </div>
                  </div>

                  {cf.symbols.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <div className="text-[11px] text-slate-400">Detected Changed Symbols:</div>
                      <div className="flex flex-wrap gap-2">
                        {cf.symbols.map((sym, sIdx) => (
                          <button
                            key={sIdx}
                            onClick={() => handleCitationClick(sym.citation, sym.file_path, sym.start_line, sym.end_line)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-emerald-500/50 text-xs font-mono transition"
                          >
                            <span className="text-cyan-400">{sym.symbol_name}</span>
                            <span className="text-[10px] text-slate-400">({sym.citation})</span>
                            <ExternalLink className="w-3 h-3 text-slate-400" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Grid: Downstream Impacts & Affected Tests */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Downstream Callers */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-emerald-400" />
                  Related Modules (Statically Traced Callers &amp; Importers)
                </h3>
                <span className="text-xs font-mono text-slate-400">
                  {impactData.downstream_impacts.length} modules
                </span>
              </div>

              {impactData.downstream_impacts.length === 0 ? (
                <p className="text-xs text-slate-400 p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  No downstream modules directly import or call the changed symbols statically.
                </p>
              ) : (
                <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                  {impactData.downstream_impacts.map((dep, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-1.5 hover:border-slate-700 transition"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-semibold text-white truncate">
                          {dep.dependent_file}
                        </span>
                        <button
                          onClick={() => handleCitationClick(dep.citation, dep.dependent_file, dep.line_number, dep.line_number)}
                          className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 shrink-0"
                        >
                          <span>{dep.citation}</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </div>
                      <div className="text-xs text-slate-400">
                        <span className="text-slate-300 font-semibold">{dep.reason}</span>
                      </div>
                      {dep.evidence_snippet && (
                        <pre className="text-[10px] font-mono p-1.5 bg-slate-900 rounded text-slate-400 overflow-x-auto">
                          {dep.evidence_snippet}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Affected Tests */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-emerald-400" />
                  Potentially Affected Tests
                </h3>
                <span className="text-xs font-mono text-slate-400">
                  {impactData.affected_tests.length} tests
                </span>
              </div>

              {impactData.affected_tests.length === 0 ? (
                <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl space-y-1">
                  <div className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4" />
                    No directly affected tests identified
                  </div>
                  <p className="text-[11px] text-slate-400">
                    No unit or integration tests statically exercise the changed symbols. See Test-Gap Advisor below.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                  {impactData.affected_tests.map((test, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-1 hover:border-slate-700 transition"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-semibold text-white truncate">
                          {test.test_file}
                        </span>
                        <button
                          onClick={() => handleCitationClick(test.citation, test.test_file, test.start_line, test.end_line)}
                          className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 shrink-0"
                        >
                          <span>{test.citation}</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </div>
                      <p className="text-xs text-slate-300">{test.relationship}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Test-Gap Advisor Section */}
          <div className="bg-slate-900 border border-emerald-500/30 rounded-2xl p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-emerald-400" />
                  Test-Gap Advisor: Recommended Test Cases
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Identifies untested behaviors and recommends concrete test scenarios with citations and rationale.
                </p>
              </div>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
                {impactData.test_gaps.length} recommendations
              </span>
            </div>

            {impactData.test_gaps.length === 0 ? (
              <div className="p-4 bg-emerald-950/30 border border-emerald-800/40 rounded-xl text-xs text-emerald-300 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                All changed functions and symbols appear to have matching test coverage in indexed test files.
              </div>
            ) : (
              <div className="space-y-3">
                {impactData.test_gaps.map((gap, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2.5 hover:border-slate-700 transition"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase font-mono ${
                            gap.gap_category === 'no_related_test_found'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          }`}
                        >
                          {gap.gap_category === 'no_related_test_found' ? 'No Test Found' : 'Untested Behavior'}
                        </span>
                        <span className="text-xs font-semibold text-white font-mono">
                          {gap.symbol_name}
                        </span>
                      </div>

                      <button
                        onClick={() => handleCitationClick(gap.citation, gap.file_path)}
                        className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 shrink-0 self-start sm:self-auto"
                      >
                        <span>{gap.citation}</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </div>

                    <div className="text-xs text-slate-300 font-medium">{gap.gap_status}</div>
                    <p className="text-xs text-slate-400 leading-relaxed">{gap.explanation}</p>

                    <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg space-y-1">
                      <div className="text-[11px] font-semibold text-emerald-300 flex items-center gap-1.5">
                        <ArrowRight className="w-3 h-3" />
                        Suggested Test Case:
                      </div>
                      <div className="text-xs font-mono text-slate-200">{gap.suggested_test}</div>
                      <div className="text-[11px] text-slate-400 pt-0.5">
                        <strong className="text-slate-300 font-sans">Why it matters:</strong> {gap.why_it_matters}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Untraced Dynamic Areas */}
          {impactData.untraced_areas.length > 0 && (
            <div className="bg-slate-900 border border-amber-500/20 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-amber-300 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-amber-400" />
                Areas That Could Not Be Traced Statically (Uncertain)
              </h3>
              <p className="text-xs text-slate-400">
                These code regions contain dynamic reflection, event emitters, or runtime dispatch that cannot be proven statically.
              </p>

              <div className="space-y-2">
                {impactData.untraced_areas.map((un, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl flex items-center justify-between text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="font-mono text-amber-300 font-semibold">{un.indicator}</div>
                      <div className="text-slate-400">{un.uncertainty_reason}</div>
                    </div>
                    <button
                      onClick={() => handleCitationClick(un.citation, un.file_path)}
                      className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-white font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800 shrink-0"
                    >
                      <span>{un.citation}</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
