import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  Search,
  ShieldAlert,
  Lock,
  FileSpreadsheet,
  CheckCircle2,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Code2,
  Info
} from 'lucide-react';
import { Repository, RepositoryFileItem, RepositoryTreeCoverage, FileContentResponse } from '../types';
import { api } from '../services/api';

interface FileExplorerTabProps {
  repo: Repository;
  initialFilePath?: string | null;
  initialLineRange?: [number, number] | null;
  onClearInitialNav?: () => void;
}

interface TreeNode {
  name: string;
  path: string;
  isFolder: boolean;
  children: TreeNode[];
  fileItem?: RepositoryFileItem;
}

export const FileExplorerTab: React.FC<FileExplorerTabProps> = ({
  repo,
  initialFilePath,
  initialLineRange,
  onClearInitialNav
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<RepositoryFileItem[]>([]);
  const [coverage, setCoverage] = useState<RepositoryTreeCoverage | null>(null);

  // Filters and search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');

  // Tree expansion state
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  // Active selected file and file preview state
  const [selectedFile, setSelectedFile] = useState<RepositoryFileItem | null>(null);
  const [fileContent, setFileContent] = useState<FileContentResponse | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [targetLines, setTargetLines] = useState<[number, number] | null>(null);

  const previewCodeRef = useRef<HTMLDivElement>(null);
  const activeRepoIdRef = useRef<number>(repo.id);

  // Fetch tree data for repository
  const loadTree = async () => {
    const targetRepoId = repo.id;
    // Don't try to load the tree if the repo hasn't been indexed yet
    if (repo.indexing_status === 'queued' || repo.indexing_status === 'running') {
      setError(`Repository '${repo.full_name}' is currently indexing (${Math.round(repo.indexing_progress)}%). File tree will be available once indexing completes.`);
      setFiles([]);
      setCoverage(null);
      setSelectedFile(null);
      setFileContent(null);
      return;
    }
    if (repo.indexing_status === 'failed') {
      setError(repo.indexing_error || 'Indexing failed. Check configuration and retry.');
      setFiles([]);
      setCoverage(null);
      setSelectedFile(null);
      setFileContent(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRepositoryTree(targetRepoId, {
        search: searchQuery || undefined,
        language: selectedLanguage !== 'all' ? selectedLanguage : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
      });
      // Ignore response if user switched repository
      if (activeRepoIdRef.current !== targetRepoId) return;

      setFiles(data.files);
      setCoverage(data.coverage);

      // Auto-expand root folders
      const roots = new Set<string>();
      data.files.forEach((f) => {
        const parts = f.file_path.split('/');
        if (parts.length > 1) {
          roots.add(parts[0]);
        }
      });
      setExpandedFolders(roots);

      // If initialFilePath is provided from a citation click, select it
      if (initialFilePath) {
        const match = data.files.find((f) => f.file_path === initialFilePath);
        if (match) {
          handleSelectFile(match, initialLineRange);
        }
      } else if (!selectedFile && data.files.length > 0) {
        // Select first allowed file or first file by default
        const defaultChoice = data.files.find((f) => f.status === 'indexed' || f.status === 'fallback') || data.files[0];
        handleSelectFile(defaultChoice);
      }
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setError(err.message || 'Failed to load repository file tree.');
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    activeRepoIdRef.current = repo.id;
    // Clear previous repo files immediately
    setFiles([]);
    setCoverage(null);
    setSelectedFile(null);
    setFileContent(null);
    setError(null);
    loadTree();
  }, [repo.id, repo.indexed_commit_sha, repo.indexing_status]);

  // Handle initial navigation request (from citation click)
  useEffect(() => {
    if (initialFilePath && files.length > 0) {
      const match = files.find((f) => f.file_path === initialFilePath);
      if (match) {
        // Expand folders along the path
        const parts = initialFilePath.split('/');
        const toExpand = new Set(expandedFolders);
        let cur = '';
        for (let i = 0; i < parts.length - 1; i++) {
          cur = cur ? `${cur}/${parts[i]}` : parts[i];
          toExpand.add(cur);
        }
        setExpandedFolders(toExpand);
        handleSelectFile(match, initialLineRange);
      }
    }
  }, [initialFilePath, initialLineRange, files]);

  // Fetch content when file is selected
  const handleSelectFile = async (file: RepositoryFileItem, lineRange?: [number, number] | null) => {
    const targetRepoId = repo.id;
    setSelectedFile(file);
    setTargetLines(lineRange || null);
    setContentLoading(true);

    try {
      const contentRes = await api.getFileContent(targetRepoId, file.file_path);
      if (activeRepoIdRef.current !== targetRepoId) return;
      setFileContent(contentRes);
    } catch (err: any) {
      if (activeRepoIdRef.current !== targetRepoId) return;
      setFileContent({
        repository_id: targetRepoId,
        file_path: file.file_path,
        allowed: false,
        language: file.language,
        language_display: file.language_display,
        analysis_mode: file.analysis_mode,
        exclusion_reason: err.message || 'Failed to read file content.',
        is_secret: file.is_secret,
        is_binary: file.is_binary,
        content: null
      });
    } finally {
      if (activeRepoIdRef.current === targetRepoId) {
        setContentLoading(false);
      }
    }
  };

  // Auto-scroll to cited line range if set
  useEffect(() => {
    if (targetLines && previewCodeRef.current && fileContent?.content) {
      const [startLine] = targetLines;
      const targetElement = document.getElementById(`code-line-${startLine}`);
      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [targetLines, fileContent]);

  // Build hierarchical tree structure from flat files list
  const treeRoot = useMemo(() => {
    const root: TreeNode = { name: '', path: '', isFolder: true, children: [] };

    files.forEach((file) => {
      const parts = file.file_path.split('/');
      let current = root;

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        const isLast = i === parts.length - 1;
        const currentPath = parts.slice(0, i + 1).join('/');

        if (isLast) {
          current.children.push({
            name: part,
            path: currentPath,
            isFolder: false,
            children: [],
            fileItem: file
          });
        } else {
          let folder = current.children.find((c) => c.isFolder && c.name === part);
          if (!folder) {
            folder = {
              name: part,
              path: currentPath,
              isFolder: true,
              children: []
            };
            current.children.push(folder);
          }
          current = folder;
        }
      }
    });

    // Sort folders first, then files alphabetically
    const sortNodes = (node: TreeNode) => {
      node.children.sort((a, b) => {
        if (a.isFolder === b.isFolder) {
          return a.name.localeCompare(b.name);
        }
        return a.isFolder ? -1 : 1;
      });
      node.children.forEach(sortNodes);
    };

    sortNodes(root);
    return root;
  }, [files]);

  const toggleFolder = (folderPath: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderPath)) {
        next.delete(folderPath);
      } else {
        next.add(folderPath);
      }
      return next;
    });
  };

  const expandAll = () => {
    const all = new Set<string>();
    const collect = (node: TreeNode) => {
      if (node.isFolder && node.path) all.add(node.path);
      node.children.forEach(collect);
    };
    collect(treeRoot);
    setExpandedFolders(all);
  };

  const collapseAll = () => {
    setExpandedFolders(new Set());
  };

  // Distinct language options for filter
  const availableLanguages = useMemo(() => {
    const set = new Set<string>();
    files.forEach((f) => {
      if (f.language) set.add(f.language);
    });
    return Array.from(set).sort();
  }, [files]);

  // Render tree node recursively
  const renderTreeNode = (node: TreeNode, depth: number = 0) => {
    if (node.isFolder) {
      if (!node.name) {
        // Root container
        return <div>{node.children.map((c) => renderTreeNode(c, depth))}</div>;
      }

      const isExpanded = expandedFolders.has(node.path);
      return (
        <div key={node.path} className="select-none">
          <div
            onClick={() => toggleFolder(node.path)}
            style={{ paddingLeft: `${depth * 14 + 8}px` }}
            className="flex items-center gap-1.5 py-1 px-2 rounded-md hover:bg-slate-800/70 text-slate-300 hover:text-white cursor-pointer text-xs font-medium transition group"
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 text-amber-400/90" />
            ) : (
              <Folder className="w-4 h-4 text-amber-400/70" />
            )}
            <span className="truncate">{node.name}</span>
          </div>
          {isExpanded && (
            <div>{node.children.map((c) => renderTreeNode(c, depth + 1))}</div>
          )}
        </div>
      );
    }

    // File Node
    const file = node.fileItem!;
    const isSelected = selectedFile?.file_path === file.file_path;

    return (
      <div
        key={file.file_path}
        onClick={() => handleSelectFile(file)}
        style={{ paddingLeft: `${depth * 14 + 18}px` }}
        className={`flex items-center justify-between py-1 px-2.5 rounded-md cursor-pointer text-xs transition group ${
          isSelected
            ? 'bg-emerald-600/20 text-emerald-300 font-semibold border border-emerald-500/30'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
        }`}
      >
        <div className="flex items-center gap-1.5 min-w-0 pr-1">
          {file.is_secret ? (
            <Lock className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
          ) : file.is_binary ? (
            <FileSpreadsheet className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
          ) : file.analysis_mode === 'parser_aware' ? (
            <FileCode className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
          ) : (
            <FileText className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {file.is_secret && (
            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
              SECRET
            </span>
          )}
          {file.is_binary && (
            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              BINARY
            </span>
          )}
          {file.status === 'excluded' && !file.is_secret && !file.is_binary && (
            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-700 text-slate-400">
              EXCLUDED
            </span>
          )}
          {file.analysis_mode === 'parser_aware' && (
            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              PARSER
            </span>
          )}
          {file.analysis_mode === 'text_fallback' && (
            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              FALLBACK
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Explorer Top Header Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Code2 className="w-5 h-5 text-emerald-400" />
                Repository File Explorer & Polyglot Index
              </h2>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {repo.default_branch} @ {repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 8) : 'HEAD'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Complete source navigation across all 35+ supported languages, parser-aware symbols, and zero-leakage safety exclusions.
            </p>
          </div>

          {/* Coverage Summary Badges */}
          {coverage && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300">
                <span className="text-slate-400">Total:</span>
                <span className="font-bold text-white">{coverage.total_files}</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300" title="Full AST or symbol parser extraction">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Parser-Aware:</span>
                <span className="font-bold text-emerald-400">{coverage.parser_aware}</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-300" title="Preserves line ranges and path without parser claim">
                <Info className="w-3.5 h-3.5 text-cyan-400" />
                <span>Fallback:</span>
                <span className="font-bold text-cyan-400">{coverage.fallback}</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300" title="Safely excluded secrets, binaries, vendors">
                <Lock className="w-3.5 h-3.5 text-rose-400" />
                <span>Excluded:</span>
                <span className="font-bold text-rose-400">{coverage.excluded}</span>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="mt-3 p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300">
            {error}
          </div>
        )}
      </div>

      {/* Main Two-Column View: Tree on Left, File Preview on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[620px]">
        {/* Left Side: Searchable Nested File Tree */}
        <div className="lg:col-span-5 xl:col-span-4 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden shadow-sm">
          {/* Tree Controls: Search & Filters */}
          <div className="p-3 border-b border-slate-800 space-y-2.5 bg-slate-900/90">
            {/* Search Bar */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search file path or name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadTree()}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />
            </div>

            {/* Filter Dropdowns */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <select
                  value={selectedLanguage}
                  onChange={(e) => {
                    setSelectedLanguage(e.target.value);
                  }}
                  className="w-full text-xs bg-slate-800 border border-slate-700 rounded-md py-1 px-2 text-slate-300 focus:outline-none focus:border-emerald-500 cursor-pointer"
                >
                  <option value="all">All Languages</option>
                  {availableLanguages.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <select
                  value={selectedStatus}
                  onChange={(e) => {
                    setSelectedStatus(e.target.value);
                  }}
                  className="w-full text-xs bg-slate-800 border border-slate-700 rounded-md py-1 px-2 text-slate-300 focus:outline-none focus:border-emerald-500 cursor-pointer"
                >
                  <option value="all">All Statuses</option>
                  <option value="parser">Parser-Aware</option>
                  <option value="fallback">Text Fallback</option>
                  <option value="excluded">Excluded</option>
                </select>
              </div>
            </div>

            {/* Tree Actions: Expand / Collapse All & Reload */}
            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <div className="flex items-center gap-2">
                <button
                  onClick={expandAll}
                  className="hover:text-slate-200 transition"
                >
                  Expand All
                </button>
                <span>•</span>
                <button
                  onClick={collapseAll}
                  className="hover:text-slate-200 transition"
                >
                  Collapse All
                </button>
              </div>
              <button
                onClick={loadTree}
                className="flex items-center gap-1 hover:text-emerald-400 transition"
                title="Reload file tree"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* Tree Scroll Area */}
          <div className="flex-1 overflow-y-auto p-2 max-h-[580px] space-y-0.5 font-mono">
            {loading ? (
              <div className="p-8 text-center text-xs text-slate-400">
                <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2 text-emerald-400" />
                Loading repository files...
              </div>
            ) : files.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 space-y-2">
                {error ? (
                  <>
                    <div className="text-rose-400 font-medium">{error}</div>
                    <div className="text-slate-600">Fix the issue and click Refresh.</div>
                  </>
                ) : (
                  'No files matched the current filters.'
                )}
              </div>
            ) : (
              renderTreeNode(treeRoot)
            )}
          </div>

          {/* Explorer Bottom File Count */}
          <div className="p-2.5 border-t border-slate-800 bg-slate-900/60 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Showing {files.length} paths</span>
            <span className="text-slate-500">Commit: {repo.indexed_commit_sha ? repo.indexed_commit_sha.slice(0, 7) : 'HEAD'}</span>
          </div>
        </div>

        {/* Right Side: Syntax-Highlighted File Preview or Safe Exclusion Banner */}
        <div className="lg:col-span-7 xl:col-span-8 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden shadow-sm">
          {selectedFile ? (
            <>
              {/* File Header */}
              <div className="p-3.5 border-b border-slate-800 bg-slate-900/90 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
                    {selectedFile.is_secret ? (
                      <Lock className="w-4 h-4 text-rose-400" />
                    ) : selectedFile.is_binary ? (
                      <FileSpreadsheet className="w-4 h-4 text-amber-400" />
                    ) : (
                      <FileCode className="w-4 h-4 text-emerald-400" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-white truncate font-mono">
                      {selectedFile.file_path}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400">
                      <span>{selectedFile.language_display || selectedFile.language}</span>
                      <span>•</span>
                      <span>{Math.round(selectedFile.file_size / 1024 * 10) / 10} KB</span>
                      {fileContent?.lines_count && (
                        <>
                          <span>•</span>
                          <span>{fileContent.lines_count} lines</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Analysis Mode Badge */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {selectedFile.analysis_mode === 'parser_aware' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      Parser-Aware (AST / Symbols)
                    </span>
                  )}
                  {selectedFile.analysis_mode === 'text_fallback' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                      <Info className="w-3.5 h-3.5 text-cyan-400" />
                      Generic Text Fallback
                    </span>
                  )}
                  {selectedFile.status === 'excluded' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20">
                      <Lock className="w-3.5 h-3.5 text-rose-400" />
                      Excluded File
                    </span>
                  )}
                </div>
              </div>

              {/* File Body Content */}
              <div className="flex-1 overflow-auto bg-[#070b14] p-4 text-xs font-mono">
                {contentLoading ? (
                  <div className="py-24 text-center text-slate-400 text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-400" />
                    Loading file contents...
                  </div>
                ) : fileContent?.allowed ? (
                  /* Allowed Text File Code Viewer */
                  <div ref={previewCodeRef} className="space-y-0.5 select-text">
                    {targetLines && (
                      <div className="mb-3 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
                        <span>
                          Jumped to cited range: <strong>L{targetLines[0]} - L{targetLines[1]}</strong>
                        </span>
                        <button
                          onClick={() => {
                            setTargetLines(null);
                            onClearInitialNav?.();
                          }}
                          className="text-slate-400 hover:text-white transition"
                        >
                          Clear
                        </button>
                      </div>
                    )}
                    {fileContent.content?.split('\n').map((line, idx) => {
                      const lineNum = idx + 1;
                      const isHighlighted =
                        targetLines && lineNum >= targetLines[0] && lineNum <= targetLines[1];

                      return (
                        <div
                          key={lineNum}
                          id={`code-line-${lineNum}`}
                          className={`flex items-start rounded px-1.5 py-0.5 transition ${
                            isHighlighted
                              ? 'bg-emerald-500/20 border-l-2 border-emerald-400 text-emerald-200'
                              : 'hover:bg-slate-800/40'
                          }`}
                        >
                          <span className="w-12 text-right pr-4 text-slate-600 select-none flex-shrink-0 text-[11px]">
                            {lineNum}
                          </span>
                          <span className="text-slate-200 whitespace-pre overflow-x-auto leading-relaxed">
                            {line || ' '}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  /* Safely Excluded / Zero Leakage Card */
                  <div className="max-w-md mx-auto my-16 p-6 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-4 shadow-lg">
                    <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
                      {fileContent?.is_secret ? (
                        <Lock className="w-6 h-6" />
                      ) : fileContent?.is_binary ? (
                        <FileSpreadsheet className="w-6 h-6" />
                      ) : (
                        <ShieldAlert className="w-6 h-6" />
                      )}
                    </div>

                    <div>
                      <h4 className="text-sm font-bold text-white">Content Excluded for Safety</h4>
                      <p className="text-xs text-rose-300 mt-1 font-semibold">
                        {fileContent?.exclusion_reason || 'File excluded by safety policy.'}
                      </p>
                    </div>

                    <div className="text-[11px] text-slate-400 bg-slate-800/60 p-3 rounded-lg text-left space-y-1.5">
                      <div className="font-semibold text-slate-300">RepoSage Zero-Leakage Guarantee:</div>
                      <p>
                        To protect credentials and prevent model poisoning, RepoSage never reads, previews, embeds, or sends sensitive or binary files to AI providers.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="p-16 text-center text-slate-500 text-xs">
              Select a file from the explorer on the left to inspect its contents and symbol breakdown.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
