import React, { useEffect, useState } from 'react';
import { History, CheckCircle2, User, Clock, ShieldCheck, AlertTriangle, Link2, Cpu } from 'lucide-react';
import { AuditLogEntry, AuditVerificationResult } from '../types';
import { api } from '../services/api';

export const AuditLogTab: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<AuditVerificationResult | null>(null);

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs();
      setLogs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyIntegrity = async () => {
    setVerifying(true);
    try {
      const result = await api.verifyAuditTrail();
      setVerificationResult(result);
    } catch (err: any) {
      alert(`Verification failed: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-400" />
            Append-Only Tamper-Evident Audit Trail
          </h3>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Cryptographically chained SHA-256 hash log recording every privileged and user-approved action:
            repository connections, comment publications, CI setting changes, and index purges.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleVerifyIntegrity}
            disabled={verifying}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold transition shadow"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            {verifying ? 'Verifying Chain…' : 'Verify Cryptographic Chain'}
          </button>
          <button
            onClick={loadAuditLogs}
            className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-300 font-medium transition"
          >
            Refresh Log
          </button>
        </div>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 ${
            verificationResult.is_valid
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          {verificationResult.is_valid ? (
            <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider">
              {verificationResult.is_valid ? 'Cryptographic Integrity Verified' : 'Tamper Alert Detected'}
            </h4>
            <p className="text-xs mt-0.5 text-slate-300">
              {verificationResult.message} ({verificationResult.total_entries} block(s) verified).
            </p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-400 text-sm">Loading audit entries...</div>
      ) : logs.length === 0 ? (
        <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-xl text-slate-400 text-sm">
          No write actions recorded yet. Connect a repository or publish a review comment to generate an audit record.
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((entry) => (
            <div
              key={entry.id}
              className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-3 hover:border-slate-700 transition"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    {entry.action_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-slate-400 font-mono text-[11px]">ID #{entry.id}</span>
                </div>
                <span className="font-mono text-slate-400 text-[11px] flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {new Date(entry.created_at).toLocaleString()}
                </span>
              </div>

              <div className="flex items-center gap-4 text-slate-300 text-xs flex-wrap">
                <span className="flex items-center gap-1">
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  Actor: <strong className="text-white">{entry.user_id}</strong>
                </span>
                <span>
                  Repo: <strong className="font-mono text-emerald-400">{entry.repo_full_name}</strong>
                </span>
                {entry.pr_number && <span>PR: <strong>#{entry.pr_number}</strong></span>}
                {entry.model_name && (
                  <span className="flex items-center gap-1 text-sky-400">
                    <Cpu className="w-3.5 h-3.5" />
                    Model: {entry.model_name} ({entry.prompt_version || 'v1.0'})
                  </span>
                )}
                {entry.index_commit_sha && (
                  <span className="text-slate-400 font-mono">
                    Commit: {entry.index_commit_sha.slice(0, 7)}
                  </span>
                )}
              </div>

              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-slate-300 text-xs font-mono">
                {entry.payload_summary}
              </div>

              {/* Cryptographic Hashes */}
              {(entry.entry_hash || entry.previous_hash) && (
                <div className="p-2 rounded bg-slate-950/80 border border-slate-800/80 font-mono text-[10px] text-slate-500 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div className="truncate max-w-sm flex items-center gap-1">
                    <Link2 className="w-3 h-3 text-slate-600 flex-shrink-0" />
                    <span>Prev: {entry.previous_hash ? entry.previous_hash.slice(0, 24) + '…' : '00000000 (genesis)'}</span>
                  </div>
                  <div className="truncate max-w-sm text-emerald-400/80">
                    Hash: {entry.entry_hash ? entry.entry_hash.slice(0, 24) + '…' : 'pending'}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
