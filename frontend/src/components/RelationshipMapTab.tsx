import React, { useEffect, useState } from 'react';
import { Network, ArrowRight, Layers, Box, FileCode } from 'lucide-react';
import { Repository, RelationshipGraph } from '../types';
import { api } from '../services/api';

interface RelationshipMapTabProps {
  repo: Repository;
}

export const RelationshipMapTab: React.FC<RelationshipMapTabProps> = ({ repo }) => {
  const [graph, setGraph] = useState<RelationshipGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  useEffect(() => {
    loadGraph();
  }, [repo.id]);

  const loadGraph = async () => {
    setLoading(true);
    try {
      const data = await api.getRelationshipGraph(repo.id);
      setGraph(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const edges = graph?.edges || [];
  const uniqueModules = Array.from(new Set(edges.map((e) => e.source.replace('file:', ''))));

  const filteredEdges = edges.filter((e) => {
    const matchesType = filterType === 'all' ? true : e.type === filterType;
    const matchesModule = selectedModule ? e.source.replace('file:', '') === selectedModule : true;
    return matchesType && matchesModule;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Network className="w-5 h-5 text-emerald-400" />
            Code Relationship & Dependency Map
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Visualizes module imports, symbol references, and cross-file dependencies with line-level evidence citations.
          </p>
        </div>

        {/* Filter buttons */}
        <div className="flex items-center gap-2">
          {['all', 'imports', 'calls', 'inherits'].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition ${
                filterType === type
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Visual Module Dependency Architecture Diagram */}
      {uniqueModules.length > 0 && (
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
              <Layers className="w-4 h-4 text-emerald-400" />
              Interactive Architecture & Module Graph
            </div>
            <div className="text-xs text-slate-400">
              Click any module to isolate its incoming/outgoing dependencies
            </div>
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            <button
              onClick={() => setSelectedModule(null)}
              className={`text-xs px-3 py-1.5 rounded-lg border font-mono transition flex items-center gap-1.5 ${
                selectedModule === null
                  ? 'bg-emerald-600 text-white border-emerald-500 shadow'
                  : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              All Modules ({edges.length} edges)
            </button>

            {uniqueModules.map((mod) => {
              const count = edges.filter((e) => e.source.replace('file:', '') === mod).length;
              return (
                <button
                  key={mod}
                  onClick={() => setSelectedModule(selectedModule === mod ? null : mod)}
                  className={`text-xs px-3 py-1.5 rounded-lg border font-mono transition flex items-center gap-1.5 ${
                    selectedModule === mod
                      ? 'bg-sky-600 text-white border-sky-500 shadow'
                      : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5 text-sky-400" />
                  {mod}
                  <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-900/80 text-slate-400">
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Relationship Graph Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-400 text-sm">Loading code relationship map...</div>
      ) : filteredEdges.length === 0 ? (
        <div className="p-8 text-center bg-slate-800/20 border border-slate-800 rounded-xl text-slate-400 text-sm">
          No relationship edges found. Ensure the repository has been indexed.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
            <span>
              Showing {filteredEdges.length} Verified Evidence Edges {selectedModule && `for ${selectedModule}`}
            </span>
            <span className="font-mono text-emerald-400 text-[11px]">
              Commit {repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 8) : ''}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredEdges.map((edge, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 text-xs space-y-2.5 hover:border-slate-600 transition"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {edge.type}
                  </span>
                  <span className="font-mono text-slate-400 text-[11px]">Line {edge.line_number}</span>
                </div>

                <div className="flex items-center gap-2 text-slate-200 font-medium">
                  <span className="truncate max-w-[45%] text-slate-300 font-mono" title={edge.source}>
                    {edge.source.replace('file:', '')}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  <span className="truncate max-w-[45%] text-emerald-400 font-mono" title={edge.target}>
                    {edge.target.replace('target:', '')}
                  </span>
                </div>

                <div className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-[11px] text-slate-400 overflow-x-auto">
                  {edge.evidence}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
