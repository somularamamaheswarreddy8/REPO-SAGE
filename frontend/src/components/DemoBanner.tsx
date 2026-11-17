import React from 'react';
import { Info, Sparkles } from 'lucide-react';

interface DemoBannerProps {
  onLoadDemoRepo: () => void;
  isDemoRepoLoaded: boolean;
}

export const DemoBanner: React.FC<DemoBannerProps> = ({ onLoadDemoRepo, isDemoRepoLoaded }) => {
  return (
    <div className="bg-amber-50/80 border-b border-amber-200/80 px-4 sm:px-6 py-2.5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2 text-amber-900">
          <Info className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>Zero-Credential Demo Mode:</strong> Running with offline GitHub & Mock AI providers.
            Answers & reviews are grounded in sample indexing analysis.
          </span>
        </div>
        {!isDemoRepoLoaded ? (
          <button
            onClick={onLoadDemoRepo}
            className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-900 text-xs font-bold transition shadow-sm shrink-0"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Load Sample Repo
          </button>
        ) : (
          <span className="text-amber-800 font-mono text-[11px] font-semibold flex items-center gap-1">
            Active: reposage-demo/ecommerce-api
          </span>
        )}
      </div>
    </div>
  );
};
