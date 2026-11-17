import React from 'react';
import { Shield, GitPullRequest, Code2, Network, Settings, History, Sparkles } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isDemo: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, isDemo }) => {
  const navItems = [
    { id: 'overview', label: 'Repository', icon: Code2 },
    { id: 'qa', label: 'Code Q&A', icon: Sparkles },
    { id: 'reviews', label: 'PR Reviews', icon: GitPullRequest },
    { id: 'relationships', label: 'Code Map', icon: Network },
    { id: 'audit', label: 'Audit Log', icon: History },
    { id: 'settings', label: 'Settings & Eval', icon: Settings },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-white flex items-center gap-2">
                RepoSage
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Secure AI
                </span>
              </span>
            </div>
          </div>

          <nav className="flex space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="flex items-center gap-3">
            {isDemo && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                Demo Mode Active
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
