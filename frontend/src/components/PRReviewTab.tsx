import React, { useState, useEffect, useRef } from 'react';
import {
  GitPullRequest,
  AlertTriangle,
  AlertOctagon,
  Info,
  UploadCloud,
  Check,
  RefreshCw,
  ShieldCheck,
  Code2,
  Download,
  GitBranch,
  Network,
  TestTube,
  ChevronDown,
  ChevronUp,
  ExternalLink
} from 'lucide-react';
import { Repository, PRReview, PRImpactAnalysis } from '../types';
import { api } from '../services/api';
import { PublishConfirmModal } from './PublishConfirmModal';
import { RepositoryContextBar } from './RepositoryContextBar';

interface PRReviewTabProps {
  repo: Repository;
  onNavigateToFile?: (path: string, lineRange?: [number, number]) => void;
}

type FeedbackCategory =
  | 'Useful'
  | 'Wrong repository'
  | 'Wrong file or citation'
  | 'Irrelevant answer'
  | 'Outdated information';

export const PRReviewTab: React.FC<PRReviewTabProps> = ({ repo, onNavigateToFile }) => {
  const [prNumber, setPrNumber] = useState(101);
  const [prTitle, setPrTitle] = useState('feat: Add payment retry & gateway webhook support');
  const [loading, setLoading] = useState(false);
  const [, setReviews] = useState<PRReview[]>([]);
  const [activeReview, setActiveReview] = useState<PRReview | null>(null);
  const [selectedFindings, setSelectedFindings] = useState<number[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);

  // Impact analysis state
  const [impactAnalysis, setImpactAnalysis] = useState<PRImpactAnalysis | null>(null);
  const [loadingImpact, setLoadingImpact] = useState(false);
  const [showImpactPanel, setShowImpactPanel] = useState(true);

  // Finding feedback input state
  const [findingReasonInput, setFindingReasonInput] = useState<number | null>(null);
  const [reasonText, setReasonText] = useState<string>('');

  const activeRepoIdRef = useRef<number>(repo.id);

  const feedbackCategories: { label: FeedbackCategory; key: string; isUseful: boolean }[] = [
    { label: 'Useful', key: 'useful', isUseful: true },
    { label: 'Wrong repository', key: 'wrong_repository', isUseful: false },
    { label: 'Wrong file or citation', key: 'wrong_citation', isUseful: false },
    { label: 'Irrelevant answer', key: 'irrelevant_answer', isUseful: false },
    { label: 'Outdated information', key: 'outdated_info', isUseful: false },
  ];

  useEffect(() => {
    activeRepoIdRef.current = repo.id;
    setActiveReview(null);
    setSelectedFindings([]);
    setIsModalOpen(false);
    setFeedbackSuccess(null);
    setImpactAnalysis(null);
    loadReviews();
  }, [repo.id, repo.indexed_commit_sha]);

  useEffect(() => {
    if (activeReview) {
      loadImpactAnalysis(activeReview.id);
    } else {
      setImpactAnalysis(null);
    }
  }, [activeReview?.id]);

  const loadReviews = async () => {
    const targetRepoId = repo.id;
    try {
      const data = await api.listReviews(targetRepoId);
      if (activeRepoIdRef.current !== targetRepoId) return;
      setReviews(data);
      setActiveReview(data.length > 0 ? data[0] : null);
    } catch (err) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      console.error('Error loading reviews:', err);
    }
  };

  const loadImpactAnalysis = async (reviewId: number) => {
    setLoadingImpact(true);
    try {
      const impact = await api.getPRImpact(repo.id, reviewId);
      if (activeRepoIdRef.current !== repo.id) return;
      setImpactAnalysis(impact);
    } catch (err) {
      console.warn('Change impact analysis not available for review:', err);
      setImpactAnalysis(null);
    } finally {
      setLoadingImpact(false);
    }
  };

  const handleExportReview = async (format: 'markdown' | 'json' | 'sarif') => {
    if (!activeReview) return;
    try {
      const content = await api.exportReview(repo.id, activeReview.id, format);
      const ext = format === 'markdown' ? 'md' : format;
      const mime = format === 'markdown' ? 'text/markdown' : 'application/json';
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `review-pr${activeReview.pr_number}-${activeReview.id}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleCreateReview = async () => {
    setLoading(true);
    try {
      const newReview = await api.createReview(repo.id, prNumber, prTitle);
      setActiveReview(newReview);
      await loadReviews();
      setSelectedFindings([]);
    } catch (err: any) {
      alert(`Review creation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleFindingSelection = (findingId: number) => {
    setSelectedFindings((prev) =>
      prev.includes(findingId) ? prev.filter((id) => id !== findingId) : [...prev, findingId]
    );
  };

  const handlePublishConfirm = async (userIdentifier: string) => {
    if (!activeReview || selectedFindings.length === 0) return;
    setIsPublishing(true);
    try {
      const res = await api.publishComments(repo.id, activeReview.id, selectedFindings, userIdentifier);
      alert(res.message);
      setIsModalOpen(false);
      setSelectedFindings([]);
      const updated = await api.getReview(repo.id, activeReview.id);
      setActiveReview(updated);
      await loadReviews();
    } catch (err: any) {
      alert(`Publish failed: ${err.message}`);
    } finally {
      setIsPublishing(false);
    }
  };

  const handleCategoryFeedback = async (
    findingId: number,
    cat: FeedbackCategory,
    explicitReason?: string
  ) => {
    const item = feedbackCategories.find((c) => c.label === cat);
    if (!item) return;

    try {
      await api.submitFeedback(
        findingId,
        item.isUseful,
        explicitReason || reasonText.trim() || `Marked as ${cat}`
      );
      if (activeReview) {
        await api.submitRepositoryFeedback(repo.id, {
          branch: repo.default_branch,
          commit_sha: activeReview.head_commit_sha || repo.indexed_commit_sha || 'unknown',
          target_type: 'finding',
          target_id: String(findingId),
          category: item.key,
          is_useful: item.isUseful,
          reason: explicitReason || reasonText.trim() || `Marked as ${cat}`,
        });
      }
      setFeedbackSuccess(`Feedback saved: "${cat}" recorded for finding #${findingId}.`);
      setFindingReasonInput(null);
      setReasonText('');
      setTimeout(() => setFeedbackSuccess(null), 3500);
    } catch (err: any) {
      alert(`Feedback submission failed: ${err.message}`);
    }
  };

  const handleTriggerCICheck = async () => {
    if (!activeReview) return;
    try {
      const res = await api.publishCICheck(repo.id, activeReview.id);
      alert(res.message);
      const updated = await api.getReview(repo.id, activeReview.id);
      setActiveReview(updated);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return (
          <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1">
            <AlertOctagon className="w-3 h-3 text-rose-600" />
            Critical
          </span>
        );
      case 'high':
        return (
          <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase bg-orange-50 text-orange-700 border border-orange-200 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-orange-600" />
            High
          </span>
        );
      case 'medium':
        return (
          <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            Medium
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase bg-sky-50 text-sky-700 border border-sky-200 flex items-center gap-1">
            <Info className="w-3 h-3 text-sky-600" />
            Low
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Repository Context Bar */}
      <RepositoryContextBar repo={repo} />

      {/* Review Trigger / PR Selection Form */}
      <div className="bg-white border border-[#e2e8df] rounded-3xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
              <GitPullRequest className="w-5 h-5 text-lime-600" />
              Pull Request Code Review & Impact
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Analyzes unified diffs against indexed repository context. Synthesizes schema-validated findings and change impact.
            </p>
          </div>

          <button
            onClick={() => handleCreateReview()}
            disabled={loading || repo.indexing_status !== 'completed'}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white font-semibold text-xs transition shadow-sm shrink-0"
          >
            {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin text-lime-400" /> : <GitPullRequest className="w-3.5 h-3.5 text-lime-400" />}
            Analyze PR #{prNumber}
          </button>
        </div>

        {/* PR Selection Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-1">
          <div className="sm:col-span-1">
            <label className="block text-[11px] font-bold text-slate-500 mb-1">PR Number</label>
            <input
              type="number"
              value={prNumber}
              onChange={(e) => setPrNumber(Number(e.target.value))}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-900 focus:outline-none focus:border-lime-500"
            />
          </div>
          <div className="sm:col-span-3">
            <label className="block text-[11px] font-bold text-slate-500 mb-1">Pull Request Title</label>
            <input
              type="text"
              value={prTitle}
              onChange={(e) => setPrTitle(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 focus:outline-none focus:border-lime-500"
            />
          </div>
        </div>
      </div>

      {feedbackSuccess && (
        <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
          {feedbackSuccess}
        </div>
      )}

      {/* Active Review View */}
      {activeReview && (
        <div className="space-y-6">
          {/* Review Header Card */}
          <div className="bg-white border border-[#e2e8df] rounded-3xl p-6 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-lime-700">
                  PR #{activeReview.pr_number} Review Report
                </span>
                <h4 className="text-base font-bold text-slate-900 mt-0.5">{activeReview.title}</h4>
                <div className="flex items-center gap-2 mt-1.5 text-xs text-slate-500 font-mono">
                  <span>Base: {activeReview.base_commit_sha ? activeReview.base_commit_sha.slice(0, 8) : 'HEAD~1'}</span>
                  <span>&rarr;</span>
                  <span>Head: {activeReview.head_commit_sha ? activeReview.head_commit_sha.slice(0, 8) : 'HEAD'}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="relative">
                  <button
                    onClick={() => setShowExportMenu(!showExportMenu)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700 transition"
                  >
                    <Download className="w-3.5 h-3.5 text-slate-500" />
                    Export
                  </button>
                  {showExportMenu && (
                    <div className="absolute right-0 top-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg z-20 py-1 w-32 text-xs">
                      <button
                        onClick={() => {
                          handleExportReview('markdown');
                          setShowExportMenu(false);
                        }}
                        className="w-full text-left px-3 py-1.5 hover:bg-slate-50 text-slate-700"
                      >
                        Markdown (.md)
                      </button>
                      <button
                        onClick={() => {
                          handleExportReview('json');
                          setShowExportMenu(false);
                        }}
                        className="w-full text-left px-3 py-1.5 hover:bg-slate-50 text-slate-700"
                      >
                        JSON (.json)
                      </button>
                      <button
                        onClick={() => {
                          handleExportReview('sarif');
                          setShowExportMenu(false);
                        }}
                        className="w-full text-left px-3 py-1.5 hover:bg-slate-50 text-slate-700"
                      >
                        SARIF (.sarif)
                      </button>
                    </div>
                  )}
                </div>

                <button
                  onClick={handleTriggerCICheck}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs text-slate-700 font-semibold transition"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-lime-600" />
                  {activeReview.ci_check_published ? 'CI Published' : 'Dispatch CI Check'}
                </button>

                <button
                  onClick={() => setIsModalOpen(true)}
                  disabled={selectedFindings.length === 0}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-white text-xs font-semibold transition shadow-sm"
                >
                  <UploadCloud className="w-3.5 h-3.5 text-lime-400" />
                  Publish Selected ({selectedFindings.length})
                </button>
              </div>
            </div>

            {/* Review Summary */}
            {activeReview.summary && (
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-xs text-slate-700 leading-relaxed">
                <strong className="text-slate-900">Summary:</strong> {activeReview.summary}
              </div>
            )}
          </div>

          {/* Change Impact Analysis & Test-Gap Advisor (Requirement 6) */}
          {impactAnalysis && (
            <div className="bg-white border border-[#e2e8df] rounded-3xl overflow-hidden shadow-sm">
              <button
                onClick={() => setShowImpactPanel(!showImpactPanel)}
                className="w-full px-6 py-4 flex items-center justify-between bg-slate-50/70 hover:bg-slate-100/60 transition text-left"
              >
                <div className="flex items-center gap-2">
                  <Network className="w-4 h-4 text-lime-600" />
                  <span className="font-bold text-slate-900 text-sm">
                    PR Change Impact & Test-Gap Advisor
                  </span>
                  {loadingImpact && (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-lime-600" />
                  )}
                  <span className="px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 text-xs font-mono font-bold">
                    {impactAnalysis.changed_files_count} modified {impactAnalysis.changed_files_count === 1 ? 'file' : 'files'}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-slate-500 text-xs">
                  <span>{showImpactPanel ? 'Collapse' : 'Expand'}</span>
                  {showImpactPanel ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </button>

              {showImpactPanel && (
                <div className="p-6 space-y-5 border-t border-slate-100">
                  {/* Notice: No fake coverage claims */}
                  <div className="p-3 rounded-2xl bg-sky-50 border border-sky-100 text-xs text-sky-800 leading-relaxed">
                    <strong>Grounded Impact Policy:</strong> {impactAnalysis.coverage_notice || 'All impacts are grounded in static relationship analysis. Dynamic invocations without static import chains are marked uncertain.'}
                  </div>

                  {/* Impact Grid: Downstream Impact + Test Gaps */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Downstream Impacts */}
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                      <h5 className="font-bold text-xs uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                        <GitBranch className="w-3.5 h-3.5 text-lime-600" />
                        Downstream Affected Modules ({impactAnalysis.downstream_impacts?.length || 0})
                      </h5>
                      {(!impactAnalysis.downstream_impacts || impactAnalysis.downstream_impacts.length === 0) ? (
                        <p className="text-xs text-slate-500">No downstream modules affected outside changed files.</p>
                      ) : (
                        <div className="space-y-2">
                          {impactAnalysis.downstream_impacts.map((imp, idx) => (
                            <div key={idx} className="p-2.5 rounded-xl bg-white border border-slate-200 text-xs">
                              <div className="font-mono font-bold text-slate-800">{imp.dependent_file}</div>
                              <div className="text-[11px] text-slate-500 mt-0.5">
                                Caller: <span className="font-mono">{imp.caller_symbol || 'module'}</span> &rarr; Target: <span className="font-mono">{imp.target_symbol || 'symbol'}</span> ({imp.relationship_type})
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Test Gap Suggestions */}
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                      <h5 className="font-bold text-xs uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                        <TestTube className="w-3.5 h-3.5 text-lime-600" />
                        Suggested Test Gaps ({impactAnalysis.test_gaps?.length || 0})
                      </h5>
                      {(!impactAnalysis.test_gaps || impactAnalysis.test_gaps.length === 0) ? (
                        <p className="text-xs text-slate-500">No unverified code paths detected in changed files.</p>
                      ) : (
                        <div className="space-y-2">
                          {impactAnalysis.test_gaps.map((gap, idx) => (
                            <div key={idx} className="p-2.5 rounded-xl bg-white border border-slate-200 text-xs space-y-1">
                              <div className="flex items-center justify-between font-mono font-semibold text-slate-800">
                                <span>{gap.file_path}</span>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                                  {gap.gap_category}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-600">{gap.suggested_test}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Findings List */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider">
                Review Findings ({activeReview.findings.length})
              </h4>
              <span className="text-xs text-slate-500">
                Check findings below to approve publishing inline review comments.
              </span>
            </div>

            {activeReview.findings.length === 0 ? (
              <div className="p-8 text-center bg-white border border-[#e2e8df] rounded-3xl text-slate-500 text-sm">
                No issues or vulnerabilities detected in this pull request diff.
              </div>
            ) : (
              activeReview.findings.map((f) => {
                const isSelected = selectedFindings.includes(f.id);
                return (
                  <div
                    key={f.id}
                    className={`bg-white border rounded-3xl p-5 space-y-4 transition ${
                      isSelected
                        ? 'border-lime-500 shadow-md bg-lime-50/20'
                        : 'border-[#e2e8df] hover:border-slate-300'
                    }`}
                  >
                    {/* Top Finding Header */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleFindingSelection(f.id)}
                          className="mt-1 w-4 h-4 rounded border-slate-300 text-lime-600 focus:ring-0 cursor-pointer"
                        />
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            {getSeverityBadge(f.severity)}
                            <h5 className="font-bold text-slate-900 text-sm">{f.title}</h5>
                            {f.category && (
                              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                                {f.category}
                              </span>
                            )}
                            {f.is_confirmed_problem ? (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                                Confirmed Defect
                              </span>
                            ) : (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                                Advisory / Potential Risk
                              </span>
                            )}
                          </div>
                          <div className="font-mono text-xs text-lime-700 mt-1 flex items-center gap-2 flex-wrap">
                            <span
                              onClick={() => {
                                if (onNavigateToFile) onNavigateToFile(f.file_path, [f.start_line, f.end_line]);
                              }}
                              className="hover:underline text-slate-900 font-bold cursor-pointer flex items-center gap-1"
                              title="Click to view file in Explorer"
                            >
                              {f.file_path}:L{f.start_line}-L{f.end_line}
                              <ExternalLink className="w-3 h-3 text-slate-400" />
                            </span>
                            {f.diff_line_reference && (
                              <span className="text-slate-400 text-[11px]">
                                ({f.diff_line_reference})
                              </span>
                            )}
                            <span className="text-slate-300">&middot;</span>
                            <span className="text-slate-500 font-medium">Confidence: {Math.round(f.confidence * 100)}%</span>
                          </div>
                        </div>
                      </div>

                      {f.published_to_github && (
                        <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full bg-sky-50 text-sky-700 border border-sky-200 shrink-0 font-semibold">
                          <Check className="w-3 h-3" /> Published
                        </span>
                      )}
                    </div>

                    {/* Explanation */}
                    <p className="text-xs text-slate-700 leading-relaxed">{f.explanation}</p>

                    {/* Why this is a problem */}
                    <div className="p-3 rounded-2xl bg-amber-50/70 border border-amber-200/80 text-xs space-y-1">
                      <span className="font-bold text-amber-900 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> Why this is a problem:
                      </span>
                      <p className="text-amber-900/90 leading-relaxed">{f.why_problem}</p>
                    </div>

                    {/* Suggested Improvement */}
                    <div className="space-y-1">
                      <span className="text-xs font-bold text-slate-700 flex items-center gap-1">
                        <Code2 className="w-3.5 h-3.5 text-lime-600" /> Suggested Fix:
                      </span>
                      <pre className="p-3 rounded-2xl bg-slate-900 text-xs font-mono text-lime-300 border border-slate-800 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                        {f.suggested_improvement}
                      </pre>
                    </div>

                    {/* 4. Feedback Controls (5 specific categories) */}
                    <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                      <span className="text-[11px] font-bold text-slate-500">Rate finding:</span>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {feedbackCategories.map((cat) => (
                          <button
                            key={cat.label}
                            onClick={() => {
                              if (cat.isUseful) {
                                handleCategoryFeedback(f.id, cat.label);
                              } else {
                                setFindingReasonInput(f.id);
                              }
                            }}
                            className={`px-2.5 py-1 rounded-xl text-[11px] font-semibold border transition ${
                              cat.isUseful
                                ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-200'
                                : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                            }`}
                          >
                            {cat.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Feedback explanation expansion */}
                    {findingReasonInput === f.id && (
                      <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                        <div className="text-[11px] font-bold text-slate-700">
                          Optional explanation for incorrect finding:
                        </div>
                        <input
                          type="text"
                          value={reasonText}
                          onChange={(e) => setReasonText(e.target.value)}
                          placeholder="e.g. Handled by framework middleware or wrong line range..."
                          className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-lime-500"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => {
                              setFindingReasonInput(null);
                              setReasonText('');
                            }}
                            className="px-2.5 py-1 text-xs text-slate-500 hover:text-slate-800"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleCategoryFeedback(f.id, 'Wrong file or citation', reasonText)}
                            className="px-3 py-1 bg-slate-900 text-white rounded-xl text-xs font-semibold hover:bg-slate-800 transition"
                          >
                            Submit Reason
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {activeReview && (
        <PublishConfirmModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onConfirm={handlePublishConfirm}
          findings={activeReview.findings.filter((f) => selectedFindings.includes(f.id))}
          repoFullName={repo.full_name}
          prNumber={activeReview.pr_number}
          isPublishing={isPublishing}
        />
      )}
    </div>
  );
};
