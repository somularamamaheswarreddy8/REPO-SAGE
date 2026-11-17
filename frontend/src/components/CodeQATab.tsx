import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Sparkles,
  BookOpen,
  FileCode,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  ExternalLink,
  MessageSquare
} from 'lucide-react';
import { Repository, CodeQuestionResponse } from '../types';
import { api } from '../services/api';
import { RepositoryContextBar } from './RepositoryContextBar';

interface CodeQATabProps {
  repo: Repository;
  onNavigateToFile?: (path: string, lineRange?: [number, number]) => void;
}

type FeedbackCategory =
  | 'Useful'
  | 'Wrong repository'
  | 'Wrong file or citation'
  | 'Irrelevant answer'
  | 'Outdated information';

export const CodeQATab: React.FC<CodeQATabProps> = ({ repo, onNavigateToFile }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<CodeQuestionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isEvidenceExpanded, setIsEvidenceExpanded] = useState(true);
  const [selectedCitation, setSelectedCitation] = useState<number | null>(null);

  // Feedback state
  const [selectedCategory, setSelectedCategory] = useState<FeedbackCategory | null>(null);
  const [feedbackReason, setFeedbackReason] = useState<string>('');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  const activeRepoIdRef = useRef<number>(repo.id);

  // Clear Q&A state immediately when switching to another repository
  useEffect(() => {
    activeRepoIdRef.current = repo.id;
    setQuery('');
    setResponse(null);
    setError(null);
    setSelectedCitation(null);
    setSelectedCategory(null);
    setFeedbackReason('');
    setFeedbackMessage(null);
  }, [repo.id, repo.indexed_commit_sha]);

  const feedbackCategories: { label: FeedbackCategory; key: string; isUseful: boolean }[] = [
    { label: 'Useful', key: 'useful', isUseful: true },
    { label: 'Wrong repository', key: 'wrong_repository', isUseful: false },
    { label: 'Wrong file or citation', key: 'wrong_citation', isUseful: false },
    { label: 'Irrelevant answer', key: 'irrelevant_answer', isUseful: false },
    { label: 'Outdated information', key: 'outdated_info', isUseful: false },
  ];

  const handleFeedbackSubmit = async (cat: FeedbackCategory, explicitReason?: string) => {
    if (!response) return;
    const item = feedbackCategories.find((c) => c.label === cat);
    if (!item) return;

    setIsSubmittingFeedback(true);
    try {
      await api.submitRepositoryFeedback(repo.id, {
        branch: repo.default_branch,
        commit_sha: response.commit_sha || repo.indexed_commit_sha || 'unknown',
        target_type: 'answer',
        target_id: `answer_${Date.now()}`,
        category: item.key,
        is_useful: item.isUseful,
        reason: explicitReason || feedbackReason.trim() || `Marked as ${cat}`,
      });
      setSelectedCategory(cat);
      setFeedbackMessage(`Feedback recorded: "${cat}". Thank you for improving accuracy.`);
      setTimeout(() => setFeedbackMessage(null), 4000);
    } catch (err: any) {
      alert(`Feedback submission failed: ${err.message}`);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const getSampleQuestions = () => {
    const nameLower = repo.full_name.toLowerCase();
    if (nameLower.includes('phish')) {
      return [
        'How does phishing detection or get_uci_features work in utils.py?',
        'Where are URL features extracted in the codebase?',
        'What database setup or table creation is handled in database.py?',
        'How is the email classifier trained in train_email_model.py?',
      ];
    }
    if (nameLower.includes('polyglot')) {
      return [
        'Where is the Rust TaskEngine defined and what does it do?',
        'How does the Go worker pool dispatcher work?',
        'Where is the Java Application cluster initialized?',
        'What smart contracts or tokens exist in this platform?',
      ];
    }
    if (nameLower.includes('ecommerce') || nameLower.includes('payment')) {
      return [
        'How is PaymentService implemented and what does process_payment do?',
        'How are orders routed in api/orders.py?',
        'Where and how are webhook signatures verified?',
        'What authentication mechanism is used for users?',
      ];
    }
    return [
      'What are the primary entry points and services in this repository?',
      'How is user authentication or session management handled?',
      'What database models or data storage entities are used?',
      'Are there any unit tests covering the core business logic?',
    ];
  };

  const sampleQuestions = getSampleQuestions();

  const handleAsk = async (textToAsk?: string) => {
    const q = textToAsk || query;
    if (!q.trim()) return;

    const currentRepoId = repo.id;
    setLoading(true);
    setError(null);
    setResponse(null);
    setSelectedCitation(null);
    setSelectedCategory(null);
    setFeedbackMessage(null);

    try {
      const data = await api.askQuestion(currentRepoId, q);
      // Ignore if user switched repository while request was in-flight
      if (activeRepoIdRef.current !== currentRepoId) return;
      setResponse(data);
    } catch (err: any) {
      if (activeRepoIdRef.current !== currentRepoId) return;
      setError(err.message || 'Failed to get answer');
    } finally {
      if (activeRepoIdRef.current === currentRepoId) {
        setLoading(false);
      }
    }
  };

  const isIndexed = repo.indexing_status === 'completed';

  return (
    <div className="space-y-6">
      {/* 1. Repository Context Bar (Requirement 1) */}
      <RepositoryContextBar repo={repo} />

      {/* Staleness Warning Banner */}
      {repo.is_stale && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-start gap-3 text-amber-800">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-600" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-amber-900">Stale Repository Index Notice</h4>
            <p className="text-xs leading-relaxed text-amber-800/90">
              Answers generated will be scoped strictly to indexed commit{' '}
              <span className="font-mono font-bold">{repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 8) : 'HEAD'}</span> on branch{' '}
              <span className="font-mono font-bold">{repo.default_branch}</span>.
              Re-index from the header to refresh with the latest remote changes.
            </p>
          </div>
        </div>
      )}

      {!isIndexed && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
          <div>
            <strong className="block text-sm text-amber-950 font-bold">Code Q&A Unavailable Before Indexing</strong>
            RepoSage answers queries strictly from verified code chunks belonging to the active repository.
            Please click <span className="font-semibold underline">Re-index</span> in the header to index{' '}
            <span className="font-mono font-semibold">{repo.full_name}</span>.
          </div>
        </div>
      )}

      {/* Search Input Box */}
      <div className="bg-white border border-[#e2e8df] rounded-3xl p-6 shadow-sm space-y-4">
        <div>
          <h3 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-lime-600" />
            Code Q&A Grounded in Repository Evidence
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Answers are retrieved strictly from indexed files in <span className="font-mono font-semibold text-slate-700">{repo.full_name}</span> ({repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 8) : 'unindexed'}).
            Claims are grounded in verifiable file citations; if no evidence exists, RepoSage states &quot;Not confirmed from indexed files.&quot;
          </p>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && isIndexed && handleAsk()}
            placeholder={
              isIndexed
                ? `Ask about ${repo.name} (e.g. 'How does authentication work?')...`
                : "Indexing required to ask questions..."
            }
            disabled={!isIndexed}
            className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-lime-500 focus:bg-white shadow-inner transition disabled:opacity-50"
          />
          <button
            onClick={() => handleAsk()}
            disabled={loading || !query.trim() || !isIndexed}
            className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white font-semibold text-sm transition shadow-sm"
          >
            {loading ? <Sparkles className="w-4 h-4 text-lime-400 animate-spin" /> : <Send className="w-4 h-4 text-lime-400" />}
            Ask
          </button>
        </div>

        {/* Preset prompts */}
        <div className="flex flex-wrap items-center gap-2 pt-2">
          <span className="text-xs text-slate-400 font-medium">Suggested queries:</span>
          {sampleQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(q);
                if (isIndexed) handleAsk(q);
              }}
              disabled={!isIndexed}
              className="text-xs px-3 py-1.5 rounded-xl bg-slate-100/80 hover:bg-lime-50 hover:text-lime-900 hover:border-lime-300 text-slate-700 border border-slate-200 transition disabled:opacity-50 font-medium"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-sm text-rose-800 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Answer Area */}
      {response && (
        <div className="space-y-6">
          {/* Ambiguity Clarification Banner (Requirement 3) */}
          {response.clarification_prompt && (
            <div className="p-4 bg-sky-50 border border-sky-200 rounded-2xl flex items-start gap-3 text-sky-900 shadow-sm">
              <HelpCircle className="w-5 h-5 text-sky-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-sm font-bold text-sky-950 flex items-center gap-1.5">
                  Clarification Suggested
                </h4>
                <p className="text-xs leading-relaxed text-sky-800">
                  {response.clarification_prompt}
                </p>
              </div>
            </div>
          )}

          {/* Main Answer Card */}
          <div className="bg-white border border-[#e2e8df] rounded-3xl p-6 shadow-sm space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <span className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-lime-600" />
                RepoSage Answer
              </span>

              <div className="flex items-center gap-2">
                {response.supported_by_evidence && !response.answer.includes("Not confirmed from indexed files") ? (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1.5 shadow-2xs">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    Grounded by Verified Evidence
                  </span>
                ) : (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1.5 shadow-2xs">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                    Not confirmed from indexed files
                  </span>
                )}
              </div>
            </div>

            {/* Markdown/Text Answer */}
            <div className="prose max-w-none text-sm text-slate-800 leading-relaxed whitespace-pre-wrap font-sans">
              {response.answer}
            </div>

            {/* Context Verification Footer */}
            <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 font-mono">
              <div className="flex items-center gap-2">
                <span>Repository Context:</span>
                <span className="font-semibold text-slate-700">{repo.full_name}</span>
                <span>@</span>
                <span className="font-semibold text-slate-700">{response.commit_sha ? response.commit_sha.slice(0, 8) : 'HEAD'}</span>
              </div>
              <div className="text-[11px] text-slate-400">
                Safe Untrusted Isolation &middot; No Code Executed
              </div>
            </div>

            {/* 4. Answer Feedback Controls (Requirement 4) */}
            <div className="pt-4 border-t border-slate-100 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="font-bold text-slate-700 flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
                  Rate answer quality:
                </span>
                <span className="text-[11px] text-slate-400">
                  Logged for accuracy evaluation reports
                </span>
              </div>

              {/* 5 Feedback Buttons */}
              <div className="flex flex-wrap items-center gap-2">
                {feedbackCategories.map((cat) => {
                  const isSelected = selectedCategory === cat.label;
                  return (
                    <button
                      key={cat.label}
                      onClick={() => handleFeedbackSubmit(cat.label)}
                      disabled={isSubmittingFeedback}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition shadow-2xs ${
                        isSelected
                          ? cat.isUseful
                            ? 'bg-emerald-600 text-white border-emerald-600'
                            : 'bg-rose-600 text-white border-rose-600'
                          : cat.isUseful
                          ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-200'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                      }`}
                    >
                      {cat.label}
                    </button>
                  );
                })}
              </div>

              {/* Optional Explanation Input */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="text"
                  value={feedbackReason}
                  onChange={(e) => setFeedbackReason(e.target.value)}
                  placeholder="Optional brief explanation for feedback..."
                  className="flex-1 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-lime-500"
                />
                {selectedCategory && (
                  <button
                    onClick={() => handleFeedbackSubmit(selectedCategory, feedbackReason)}
                    disabled={isSubmittingFeedback || !feedbackReason.trim()}
                    className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold disabled:opacity-40 transition"
                  >
                    Save Note
                  </button>
                )}
              </div>

              {feedbackMessage && (
                <div className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-xl font-medium animate-fadeIn">
                  {feedbackMessage}
                </div>
              )}
            </div>
          </div>

          {/* 2. "Why this answer?" Evidence Panel (Requirement 2) */}
          <div className="bg-white border border-[#e2e8df] rounded-3xl overflow-hidden shadow-sm">
            <button
              onClick={() => setIsEvidenceExpanded(!isEvidenceExpanded)}
              className="w-full px-6 py-4 flex items-center justify-between bg-slate-50/70 hover:bg-slate-100/60 transition text-left"
            >
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-lime-600" />
                <span className="font-bold text-slate-900 text-sm">
                  &ldquo;Why this answer?&rdquo; Evidence Panel
                </span>
                <span className="px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 text-xs font-mono font-bold">
                  {response.citations.length} cited {response.citations.length === 1 ? 'source' : 'sources'}
                </span>
              </div>
              <div className="flex items-center gap-1 text-slate-500 text-xs">
                <span>{isEvidenceExpanded ? 'Collapse' : 'Expand'}</span>
                {isEvidenceExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </div>
            </button>

            {isEvidenceExpanded && (
              <div className="p-6 space-y-4 border-t border-slate-100">
                {response.citations.length === 0 ? (
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-slate-500 text-xs text-center">
                    No source files or code chunks were cited. This question had no matching indexed evidence in this commit.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {response.citations.map((cite, i) => (
                      <div
                        key={i}
                        className={`p-4 rounded-2xl border transition ${
                          selectedCitation === i
                            ? 'bg-lime-50/30 border-lime-400 shadow-sm'
                            : 'bg-white border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        {/* File path + Line range with Navigation Link */}
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                          <button
                            onClick={() => {
                              setSelectedCitation(i);
                              if (onNavigateToFile) {
                                onNavigateToFile(cite.file_path, [cite.start_line, cite.end_line]);
                              }
                            }}
                            className="inline-flex items-center gap-1.5 font-mono text-xs font-bold text-slate-900 hover:text-lime-700 group cursor-pointer"
                            title="Open in File Explorer"
                          >
                            <FileCode className="w-3.5 h-3.5 text-lime-600 group-hover:scale-110 transition-transform" />
                            <span className="underline underline-offset-2">{cite.file_path}</span>
                            <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-lime-600 ml-0.5" />
                          </button>

                          <button
                            onClick={() => {
                              setSelectedCitation(i);
                              if (onNavigateToFile) {
                                onNavigateToFile(cite.file_path, [cite.start_line, cite.end_line]);
                              }
                            }}
                            className="font-mono text-xs text-slate-600 hover:text-slate-900 bg-slate-100 px-2 py-0.5 rounded-lg border border-slate-200 font-semibold"
                          >
                            Lines {cite.start_line}–{cite.end_line}
                          </button>
                        </div>

                        {/* Relevance Reason */}
                        <div className="mb-2.5 p-2 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-600">
                          <span className="font-semibold text-slate-800">Why relevant: </span>
                          <span>
                            {cite.relevance_reason ||
                              `Direct lexical and vector match for question concepts in ${cite.file_path}`}
                          </span>
                          {cite.symbol_name && (
                            <span className="ml-2 px-1.5 py-0.5 rounded bg-slate-200/80 font-mono text-[10px] text-slate-700">
                              Symbol: {cite.symbol_name}
                            </span>
                          )}
                        </div>

                        {/* Safe Source Snippet */}
                        <div className="rounded-xl bg-slate-900 text-slate-200 p-3 overflow-x-auto text-[11px] font-mono leading-relaxed border border-slate-800">
                          <pre className="whitespace-pre-wrap">{cite.snippet}</pre>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
