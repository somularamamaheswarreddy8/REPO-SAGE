import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  RefreshCw,
  GitBranch,
  GitCommit,
  AlertTriangle,
  Info,
  Check
} from 'lucide-react';
import { QualityReportData } from '../types';
import { api } from '../services/api';

export const AccuracyQualityDashboard: React.FC = () => {
  const [report, setReport] = useState<QualityReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningBenchmark, setRunningBenchmark] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getQualityReport();
      setReport(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load accuracy and quality report');
    } finally {
      setLoading(false);
    }
  };

  const handleRunBenchmark = async () => {
    setRunningBenchmark(true);
    setError(null);
    setSuccessNotice(null);
    try {
      const updated = await api.runQABenchmark();
      setReport(updated);
      setSuccessNotice('Benchmark completed across all repositories. Metrics updated with live evaluation.');
      setTimeout(() => setSuccessNotice(null), 5000);
    } catch (err: any) {
      setError(err.message || 'Failed to run repeatable benchmark');
    } finally {
      setRunningBenchmark(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 rounded-3xl bg-white border border-[#e2e8df] flex flex-col items-center justify-center gap-3 text-slate-500 shadow-sm">
        <RefreshCw className="w-6 h-6 animate-spin text-lime-600" />
        <span className="text-xs font-semibold">Loading measured quality metrics...</span>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-6 rounded-3xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{error || 'Unable to load evaluation report'}</span>
        </div>
        <button
          onClick={loadReport}
          className="px-3 py-1.5 rounded-xl bg-white border border-rose-300 text-rose-800 hover:bg-rose-100 font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  const feedbackTotal = Object.values(report.feedback_breakdown || {}).reduce((a, b) => a + b, 0);

  return (
    <div className="bg-white border border-[#e2e8df] rounded-3xl p-6 shadow-sm space-y-6">
      {/* Header with Benchmark Status & Run Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-lime-600" />
            <h3 className="text-lg font-extrabold text-slate-900">
              Accuracy & Index Quality Dashboard
            </h3>
            <span className="px-2.5 py-0.5 rounded-full bg-lime-50 text-lime-800 border border-lime-200 text-[10px] font-mono font-bold">
              {report.benchmark_version}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Measured evaluation of answer correctness, citation accuracy, correct repository selection, and cross-repo isolation.
          </p>
        </div>

        <button
          onClick={handleRunBenchmark}
          disabled={runningBenchmark}
          className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white font-semibold text-xs transition shadow-sm shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-lime-400 ${runningBenchmark ? 'animate-spin' : ''}`} />
          <span>{runningBenchmark ? 'Evaluating 15 Cases...' : 'Run Repeatable Benchmark'}</span>
        </button>
      </div>

      {successNotice && (
        <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2 font-medium">
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successNotice}</span>
        </div>
      )}

      {/* Metadata Bar: Sample Size, Evaluation Date */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-2xl bg-slate-50 border border-slate-100 text-xs">
        <div>
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Sample Size</span>
          <span className="font-mono font-extrabold text-slate-900 text-sm">{report.sample_size} cases</span>
        </div>
        <div>
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Evaluation Date</span>
          <span className="font-mono text-slate-700 text-xs">
            {new Date(report.evaluation_date).toLocaleDateString(undefined, {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        </div>
        <div>
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Repositories Tested</span>
          <span className="font-mono font-extrabold text-slate-900 text-sm">
            {report.tested_commits.length} Repositories
          </span>
        </div>
        <div>
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Failing Cases</span>
          <span className={`font-mono font-extrabold text-sm ${report.failing_cases.length > 0 ? 'text-rose-600' : 'text-emerald-700'}`}>
            {report.failing_cases.length} cases
          </span>
        </div>
      </div>

      {/* 6 Key Quality Metric Cards */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Core Retrieval & Grounding Metrics
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* 1. Answer Correctness */}
          <div className="p-4 rounded-2xl bg-white border border-[#e2e8df] shadow-2xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Answer Correctness
            </span>
            <div className="text-2xl font-extrabold text-slate-900 font-mono">
              {report.answer_correctness_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-lime-700 font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-lime-600" />
              Target &ge; 90%
            </div>
          </div>

          {/* 2. Citation Accuracy */}
          <div className="p-4 rounded-2xl bg-white border border-[#e2e8df] shadow-2xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Citation Accuracy
            </span>
            <div className="text-2xl font-extrabold text-slate-900 font-mono">
              {report.citation_accuracy_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-lime-700 font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-lime-600" />
              Target &ge; 95%
            </div>
          </div>

          {/* 3. Correct Repo Selection */}
          <div className="p-4 rounded-2xl bg-white border border-[#e2e8df] shadow-2xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Repo Selection
            </span>
            <div className="text-2xl font-extrabold text-slate-900 font-mono">
              {report.correct_repo_selection_pct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-lime-700 font-semibold flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-lime-600" />
              Target 100%
            </div>
          </div>

          {/* 4. Cross-Repo Leakage */}
          <div className="p-4 rounded-2xl bg-white border border-[#e2e8df] shadow-2xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Cross-Repo Leakage
            </span>
            <div className={`text-2xl font-extrabold font-mono ${report.cross_repo_leakage_count === 0 ? 'text-emerald-700' : 'text-rose-600'}`}>
              {report.cross_repo_leakage_count}
            </div>
            <div className="text-[10px] text-slate-500 font-medium">
              Target: 0 Leakage
            </div>
          </div>

          {/* 5. Indexing Failures */}
          <div className="p-4 rounded-2xl bg-white border border-[#e2e8df] shadow-2xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Indexing Failures
            </span>
            <div className={`text-2xl font-extrabold font-mono ${report.indexing_failures_count === 0 ? 'text-slate-900' : 'text-rose-600'}`}>
              {report.indexing_failures_count}
            </div>
            <div className="text-[10px] text-slate-500 font-medium">
              Zero Uncaught Errors
            </div>
          </div>

          {/* 6. Stale Indexes */}
          <div className="p-4 rounded-2xl bg-white border border-[#e2e8df] shadow-2xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Stale Indexes
            </span>
            <div className={`text-2xl font-extrabold font-mono ${report.stale_indexes_count === 0 ? 'text-emerald-700' : 'text-amber-700'}`}>
              {report.stale_indexes_count}
            </div>
            <div className="text-[10px] text-slate-500 font-medium">
              {report.stale_indexes_count === 0 ? 'All Fresh' : 'Needs Re-index'}
            </div>
          </div>
        </div>
      </div>

      {/* Tested Repositories & Commits Table */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Tested Commits & Repository Health
        </h4>
        <div className="border border-slate-200 rounded-2xl overflow-hidden shadow-2xs">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold">
              <tr>
                <th className="px-4 py-2.5">Repository</th>
                <th className="px-4 py-2.5">Branch</th>
                <th className="px-4 py-2.5">Tested Commit</th>
                <th className="px-4 py-2.5">Indexing Status</th>
                <th className="px-4 py-2.5">Index Freshness</th>
                <th className="px-4 py-2.5">Last Indexed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {report.tested_commits.map((t) => (
                <tr key={t.repository_id} className="hover:bg-slate-50/70 transition">
                  <td className="px-4 py-2.5 font-bold text-slate-900 font-mono">
                    {t.full_name}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600 font-mono">
                    <span className="inline-flex items-center gap-1">
                      <GitBranch className="w-3 h-3 text-slate-400" />
                      {t.branch}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-slate-700 font-mono">
                    <span className="inline-flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded-lg border border-slate-200 font-semibold">
                      <GitCommit className="w-3 h-3 text-slate-400" />
                      {t.indexed_commit_sha ? t.indexed_commit_sha.slice(0, 8) : 'unindexed'}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                        t.indexing_status === 'completed'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : t.indexing_status === 'failed'
                          ? 'bg-rose-50 text-rose-800 border-rose-200'
                          : 'bg-amber-50 text-amber-800 border-amber-200'
                      }`}
                    >
                      {t.indexing_status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        t.is_stale
                          ? 'bg-amber-50 text-amber-800 border border-amber-200'
                          : 'bg-lime-50 text-lime-900 border border-lime-200'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${t.is_stale ? 'bg-amber-500' : 'bg-lime-600'}`}></span>
                      {t.is_stale ? 'Stale' : 'Current'}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-slate-500 font-mono text-[11px]">
                    {t.last_indexed_at ? new Date(t.last_indexed_at).toLocaleTimeString() : 'Never'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Developer Feedback Category Breakdown */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Developer Feedback Breakdown ({feedbackTotal} total ratings)
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="p-3 rounded-2xl bg-emerald-50/60 border border-emerald-200 text-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 block">Useful</span>
            <div className="text-xl font-bold text-emerald-900 font-mono mt-0.5">
              {report.feedback_breakdown?.useful ?? 0}
            </div>
          </div>
          <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 block">Wrong Repository</span>
            <div className="text-xl font-bold text-slate-800 font-mono mt-0.5">
              {report.feedback_breakdown?.wrong_repository ?? 0}
            </div>
          </div>
          <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 block">Wrong Citation</span>
            <div className="text-xl font-bold text-slate-800 font-mono mt-0.5">
              {report.feedback_breakdown?.wrong_citation ?? 0}
            </div>
          </div>
          <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 block">Irrelevant Answer</span>
            <div className="text-xl font-bold text-slate-800 font-mono mt-0.5">
              {report.feedback_breakdown?.irrelevant_answer ?? 0}
            </div>
          </div>
          <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 text-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 block">Outdated Info</span>
            <div className="text-xl font-bold text-slate-800 font-mono mt-0.5">
              {report.feedback_breakdown?.outdated_info ?? 0}
            </div>
          </div>
        </div>
      </div>

      {/* Failing Cases List (if any) */}
      {report.failing_cases.length > 0 && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 space-y-2 text-xs">
          <div className="flex items-center gap-1.5 font-bold text-rose-900">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            Detected Failing Cases ({report.failing_cases.length})
          </div>
          <div className="space-y-1.5 font-mono text-[11px] text-rose-800">
            {report.failing_cases.map((fc: any, i: number) => (
              <div key={i} className="p-2 bg-white rounded-lg border border-rose-200">
                <strong>[{fc.id}]</strong> Repo {fc.repo_id}: {fc.query} &mdash; <em>{fc.reason}</em>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Known Limitations and Transparency Policy */}
      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
        <div className="flex items-center gap-1.5 font-bold text-slate-800 uppercase tracking-wider">
          <Info className="w-4 h-4 text-slate-500" />
          Benchmark Scope & System Limitations
        </div>
        <ul className="space-y-1.5 text-slate-600 leading-relaxed list-disc list-inside">
          {report.limitations.map((lim, idx) => (
            <li key={idx} className="text-[11px]">
              {lim}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
