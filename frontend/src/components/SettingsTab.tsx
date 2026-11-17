import React, { useEffect, useState } from 'react';
import { Settings as SettingsIcon, ShieldCheck, Check, Trash2, AlertTriangle } from 'lucide-react';
import { Repository, RepositorySettings } from '../types';
import { api } from '../services/api';
import { RepositoryContextBar } from './RepositoryContextBar';
import { AccuracyQualityDashboard } from './AccuracyQualityDashboard';

interface SettingsTabProps {
  repo: Repository;
  onRefresh: () => void;
  onDisconnect?: (repoId: number) => void;
}

export const SettingsTab: React.FC<SettingsTabProps> = ({ repo, onRefresh, onDisconnect }) => {
  const [settings, setSettings] = useState<RepositorySettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    loadData();
  }, [repo.id]);

  const loadData = async () => {
    try {
      const sData = await api.getRepositorySettings(repo.id);
      setSettings(sData);
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleCI = async (enabled: boolean) => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await api.updateRepositorySettings(repo.id, {
        optional_ci_enabled: enabled,
      });
      setSettings(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
      onRefresh();
    } catch (err: any) {
      alert(`Failed to update settings: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleAutoReview = async (enabled: boolean) => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await api.updateRepositorySettings(repo.id, {
        auto_review_prs: enabled,
      });
      setSettings(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Repository Context Bar */}
      <RepositoryContextBar repo={repo} />

      {/* Accuracy and Index Quality Dashboard (Requirement 5) */}
      <AccuracyQualityDashboard />

      {/* Repository Settings Panel */}
      <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-emerald-400" />
            <h3 className="text-lg font-bold text-white">Repository Settings & Permissions</h3>
          </div>
          {saveSuccess && (
            <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
              <Check className="w-3.5 h-3.5" /> Saved
            </span>
          )}
        </div>

        {/* Optional Advisory CI Check */}
        <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span className="text-sm font-semibold text-white">
                Optional Advisory GitHub Check Summary
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-medium">
                Advisory Mode
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed max-w-xl">
              When enabled, RepoSage publishes a non-blocking advisory Check Run summary on PR head commits.
              Requires GitHub App <code className="text-emerald-400 font-mono">Checks: Read & write</code> permission.
              <strong> Does not block pull request merges.</strong>
            </p>
          </div>

          <label className="relative inline-flex items-center cursor-pointer shrink-0">
            <input
              type="checkbox"
              checked={settings?.optional_ci_enabled ?? false}
              onChange={(e) => handleToggleCI(e.target.checked)}
              disabled={saving}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
          </label>
        </div>

        {/* Blocking CI Check Setting */}
        <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span className="text-sm font-semibold text-white">
                Enforce Blocking CI Build Failures
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold uppercase tracking-wider">
                Quality Gate
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed max-w-xl">
              When enabled, CI check status will fail and block branch merges if
              unmitigated Critical or High severity security vulnerabilities are discovered.
            </p>
          </div>

          <label className="relative inline-flex items-center cursor-pointer shrink-0">
            <input
              type="checkbox"
              checked={settings?.blocking_ci_enabled ?? false}
              onChange={async (e) => {
                if (!settings) return;
                setSaving(true);
                try {
                  const updated = await api.updateRepositorySettings(repo.id, {
                    blocking_ci_enabled: e.target.checked,
                  });
                  setSettings(updated);
                  setSaveSuccess(true);
                  setTimeout(() => setSaveSuccess(false), 2500);
                  onRefresh();
                } catch (err: any) {
                  alert(err.message || 'Failed to update blocking CI setting.');
                } finally {
                  setSaving(false);
                }
              }}
              disabled={saving}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-rose-600"></div>
          </label>
        </div>

        {/* Auto Review Webhook Toggle */}
        <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">
                Automatic Review on Pull Request Webhook
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed max-w-xl">
              Queues an AI code review automatically whenever a pull request is opened or updated via GitHub webhooks.
              Review findings remain strictly advisory until explicit developer approval.
            </p>
          </div>

          <label className="relative inline-flex items-center cursor-pointer shrink-0">
            <input
              type="checkbox"
              checked={settings?.auto_review_prs ?? false}
              onChange={(e) => handleToggleAutoReview(e.target.checked)}
              disabled={saving}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
          </label>
        </div>
      </div>

      {/* Danger Zone: Disconnect Repository */}
      {onDisconnect && (
        <div className="bg-rose-950/20 border border-rose-900/50 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-rose-900/40 pb-3">
            <AlertTriangle className="w-5 h-5 text-rose-400" />
            <h3 className="text-base font-bold text-rose-300">Danger Zone: Disconnect Repository</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Disconnecting <strong className="font-mono text-rose-200">{repo.full_name}</strong> will purge all indexed source code chunks, architecture profiles, and cached pull request reviews from RepoSage.
          </p>
          <div className="pt-1">
            <button
              onClick={() => onDisconnect(repo.id)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-700 hover:bg-rose-600 text-white text-xs font-semibold transition shadow"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Disconnect {repo.name}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
