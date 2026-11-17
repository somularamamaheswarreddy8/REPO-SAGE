import React, { useState } from 'react';
import { Check, X, ShieldAlert, GitPullRequest } from 'lucide-react';
import { ReviewFinding } from '../types';

interface PublishConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (userIdentifier: string) => void;
  findings: ReviewFinding[];
  repoFullName: string;
  prNumber: number;
  isPublishing: boolean;
}

export const PublishConfirmModal: React.FC<PublishConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  findings,
  repoFullName,
  prNumber,
  isPublishing,
}) => {
  const [confirmed, setConfirmed] = useState(false);
  const [userIdentifier, setUserIdentifier] = useState('developer_approved');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-800/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-100">Confirm Publishing to GitHub</h3>
              <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                <GitPullRequest className="w-3.5 h-3.5" />
                {repoFullName} &middot; PR #{prNumber} &middot; {findings.length} comment(s)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4">
          <div className="p-3.5 rounded-lg bg-amber-950/30 border border-amber-800/40 text-xs text-amber-200">
            <strong>Human Approval Required:</strong> RepoSage never publishes comments or changes source code automatically.
            Please inspect the exact review comments below that will be posted under your authorization.
          </div>

          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Selected Review Comments ({findings.length})
            </h4>
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {findings.map((f) => (
                <div key={f.id} className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-200">{f.title}</span>
                    <span className="font-mono text-[11px] text-slate-400">
                      {f.file_path}:L{f.start_line}-L{f.end_line}
                    </span>
                  </div>
                  <p className="text-slate-400 line-clamp-2">{f.explanation}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Developer Identity (recorded in audit log)
              </label>
              <input
                type="text"
                value={userIdentifier}
                onChange={(e) => setUserIdentifier(e.target.value)}
                placeholder="e.g. dev_jane or github_user"
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <label className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/30 border border-slate-700/40 cursor-pointer">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-0"
              />
              <span className="text-xs text-slate-300">
                I have inspected these findings, verified the code evidence, and explicitly approve publishing them to GitHub PR #{prNumber}.
              </span>
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-800/20 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-300 hover:text-white transition"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(userIdentifier)}
            disabled={!confirmed || isPublishing || !userIdentifier.trim()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:pointer-events-none text-white text-sm font-medium transition shadow"
          >
            {isPublishing ? (
              <>Publishing to GitHub...</>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Approve & Publish Comments
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
