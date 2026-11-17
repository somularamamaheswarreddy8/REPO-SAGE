"""
PR Change Impact Analysis and Test-Gap Advisor.
Statically analyzes:
- Changed files and key functions/classes/symbols
- Dependent modules importing/calling the changed code
- Potentially affected tests
- Areas that could not be traced (marked uncertain)
- Test-Gap Advisor: identifies behaviors lacking test coverage, distinguishes 'no related test found' from 'untested behavior', and suggests concrete test cases with citations.
Never executes repository code.
"""
import re
from typing import List, Dict, Any, Optional, Set
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.models.relationship import CodeRelationship
from app.services.reviewer.diff_parser import parse_unified_diff, FileDiff


class PRImpactAnalyzer:
    def __init__(
        self,
        repository: Repository,
        pr_number: int,
        diff_text: str,
        chunks: List[CodeChunk],
        relationships: List[CodeRelationship],
    ):
        self.repository = repository
        self.pr_number = pr_number
        self.diff_text = diff_text
        self.chunks = chunks
        self.relationships = relationships

    def analyze(self) -> Dict[str, Any]:
        """Runs static change impact analysis and test gap inspection."""
        diff_files = parse_unified_diff(self.diff_text)
        
        changed_symbols = self._identify_changed_symbols(diff_files)
        downstream_dependents = self._trace_dependents(diff_files, changed_symbols)
        affected_tests = self._find_affected_tests(diff_files, changed_symbols)
        untraced_areas = self._find_untraced_areas(diff_files)
        test_gaps = self._analyze_test_gaps(diff_files, changed_symbols, affected_tests)

        return {
            "pr_number": self.pr_number,
            "repository_id": self.repository.id,
            "commit_sha": self.repository.indexed_commit_sha,
            "changed_files_count": len(diff_files),
            "changed_files": [
                {
                    "file_path": f.file_path,
                    "old_path": f.file_path,
                    "change_type": "added" if f.is_new else ("deleted" if f.is_deleted else "modified"),
                    "additions": len(f.modified_lines),
                    "deletions": 0,
                    "symbols": [s for s in changed_symbols if s["file_path"] == f.file_path],
                }
                for f in diff_files
            ],
            "downstream_impacts": downstream_dependents,
            "affected_tests": affected_tests,
            "untraced_areas": untraced_areas,
            "test_gaps": test_gaps,
            "execution_policy": "Static analysis only. Repository code is never executed.",
            "coverage_notice": "Coverage results are not claimed without configured coverage data. Gaps are statically inferred from indexed source and test symbols."
        }

    def _identify_changed_symbols(self, diff_files: List[FileDiff]) -> List[Dict[str, Any]]:
        """Maps diff hunks to code chunk symbols to determine which functions/classes changed."""
        results: List[Dict[str, Any]] = []

        for df in diff_files:
            file_chunks = [c for c in self.chunks if c.file_path.replace("\\", "/") == df.file_path.replace("\\", "/")]
            
            # Collect changed line numbers in new file
            changed_lines: Set[int] = set(df.modified_lines)
            for hunk in df.hunks:
                start = hunk.target_start
                length = hunk.target_length
                for l in range(start, start + max(1, length)):
                    changed_lines.add(l)

            # Match lines to chunks
            matched_symbols = set()
            for chunk in file_chunks:
                chunk_range = range(chunk.start_line, chunk.end_line + 1)
                overlap = changed_lines.intersection(chunk_range)
                if overlap:
                    sym = chunk.symbol_name or f"module_block_{chunk.start_line}"
                    if sym not in matched_symbols:
                        matched_symbols.add(sym)
                        results.append({
                            "file_path": df.file_path,
                            "symbol_name": sym,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "citation": f"{df.file_path}:{chunk.start_line}-{chunk.end_line}",
                            "language": chunk.language,
                            "analysis_mode": chunk.analysis_mode,
                            "snippet": chunk.content[:160]
                        })

            # If no chunk matched specifically, add file-level symbol
            if not matched_symbols:
                results.append({
                    "file_path": df.file_path,
                    "symbol_name": "module_scope",
                    "start_line": 1,
                    "end_line": max(1, len(df.modified_lines)),
                    "citation": f"{df.file_path}:1-{max(1, len(df.modified_lines))}",
                    "language": "unknown",
                    "analysis_mode": "text_fallback",
                    "snippet": f"File modified with {len(df.modified_lines)} changes"
                })

        return results

    def _trace_dependents(
        self,
        diff_files: List[FileDiff],
        changed_symbols: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Statically traces modules that import or call changed files and symbols."""
        dependents: List[Dict[str, Any]] = []
        changed_paths = {df.file_path.replace("\\", "/") for df in diff_files}
        symbol_names = {s["symbol_name"] for s in changed_symbols if s["symbol_name"] != "module_scope"}

        for rel in self.relationships:
            target_f = (rel.target_file or "").replace("\\", "/")
            source_f = rel.source_file.replace("\\", "/")

            # Is this relationship pointing to a changed file or symbol?
            is_match = False
            match_reason = ""
            if target_f in changed_paths:
                is_match = True
                match_reason = f"Imports or references changed file '{target_f}'"
            elif rel.target_symbol in symbol_names:
                is_match = True
                match_reason = f"Calls changed symbol '{rel.target_symbol}'"

            # Avoid self-referencing in same file
            if is_match and source_f not in changed_paths:
                dependents.append({
                    "dependent_file": source_f,
                    "line_number": rel.line_number,
                    "citation": f"{source_f}:{rel.line_number}",
                    "relationship_type": rel.relationship_type,
                    "caller_symbol": rel.source_symbol,
                    "target_symbol": rel.target_symbol,
                    "reason": match_reason,
                    "evidence_snippet": rel.evidence_snippet[:140],
                    "status": "Confirmed statically from indexed files"
                })

        return dependents

    def _find_affected_tests(
        self,
        diff_files: List[FileDiff],
        changed_symbols: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Finds tests that exercise or reference changed files or symbols."""
        affected: List[Dict[str, Any]] = []
        changed_paths = {df.file_path.replace("\\", "/") for df in diff_files}
        symbol_names = {s["symbol_name"].lower() for s in changed_symbols if s["symbol_name"]}

        test_chunks = [
            c for c in self.chunks
            if "test" in c.file_path.lower() or ".spec." in c.file_path.lower()
        ]

        seen_tests = set()
        for tc in test_chunks:
            tcp = tc.file_path.replace("\\", "/")
            # If the test is in a changed file itself
            if tcp in changed_paths:
                key = f"{tcp}:{tc.start_line}"
                if key not in seen_tests:
                    seen_tests.add(key)
                    affected.append({
                        "test_file": tcp,
                        "test_name": tc.symbol_name or "test_suite",
                        "start_line": tc.start_line,
                        "end_line": tc.end_line,
                        "citation": f"{tcp}:{tc.start_line}-{tc.end_line}",
                        "relationship": "Test file modified in this pull request",
                        "confidence": "high"
                    })
                continue

            # Check if test file references changed symbols or file stems
            content_lower = tc.content.lower()
            for sym in symbol_names:
                if len(sym) >= 3 and sym in content_lower:
                    key = f"{tcp}:{tc.start_line}"
                    if key not in seen_tests:
                        seen_tests.add(key)
                        affected.append({
                            "test_file": tcp,
                            "test_name": tc.symbol_name or "test_case",
                            "start_line": tc.start_line,
                            "end_line": tc.end_line,
                            "citation": f"{tcp}:{tc.start_line}-{tc.end_line}",
                            "relationship": f"Exercises changed symbol '{sym}'",
                            "confidence": "high"
                        })
                    break

        return affected

    def _find_untraced_areas(self, diff_files: List[FileDiff]) -> List[Dict[str, Any]]:
        """Identifies dynamic, reflection, or unindexed areas that cannot be verified statically."""
        untraced: List[Dict[str, Any]] = []

        dynamic_indicators = [
            ("eval(", "Dynamic evaluation using eval() cannot be verified statically"),
            ("getattr(", "Dynamic attribute lookup via getattr() cannot be traced statically"),
            ("setattr(", "Dynamic attribute assignment via setattr() cannot be traced statically"),
            ("process.env", "Environment variable configuration dependency"),
            ("os.environ", "Dynamic runtime environment variable reading"),
            ("importlib", "Dynamic module loading via importlib"),
            ("emit(", "Event-driven message dispatch requires runtime broker verification"),
        ]

        for df in diff_files:
            file_chunks = [c for c in self.chunks if c.file_path.replace("\\", "/") == df.file_path.replace("\\", "/")]
            for chunk in file_chunks:
                for token, note in dynamic_indicators:
                    if token in chunk.content:
                        untraced.append({
                            "file_path": df.file_path,
                            "line_range": f"{chunk.start_line}-{chunk.end_line}",
                            "citation": f"{df.file_path}:{chunk.start_line}-{chunk.end_line}",
                            "indicator": token,
                            "uncertainty_reason": note,
                            "status": "Uncertain: dynamic/runtime relationship not confirmed from indexed files."
                        })

        return untraced

    def _analyze_test_gaps(
        self,
        diff_files: List[FileDiff],
        changed_symbols: List[Dict[str, Any]],
        affected_tests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Test-Gap Advisor:
        - Finds existing related tests
        - Identifies behaviors lacking test coverage
        - Distinguishes 'no related test found' from 'this behavior is definitely untested'
        - Suggests concrete test cases with citations and rationale.
        """
        gaps: List[Dict[str, Any]] = []
        tested_files = {t["test_file"].replace("\\", "/") for t in affected_tests}
        tested_symbols = {t["relationship"] for t in affected_tests}

        # Check all non-test changed files
        for df in diff_files:
            p = df.file_path.replace("\\", "/")
            if "test" in p.lower() or ".spec." in p.lower() or "doc" in p.lower():
                continue

            # Look for tests associated with this file
            mod_stem = p.split("/")[-1].split(".")[0]
            matching_tests = [t for t in affected_tests if mod_stem in t["test_file"].lower()]

            symbols_in_file = [s for s in changed_symbols if s["file_path"] == df.file_path]

            if not matching_tests:
                # Case 1: No related test found
                gaps.append({
                    "file_path": df.file_path,
                    "symbol_name": symbols_in_file[0]["symbol_name"] if symbols_in_file else "module",
                    "citation": symbols_in_file[0]["citation"] if symbols_in_file else f"{df.file_path}:1",
                    "gap_category": "no_related_test_found",
                    "gap_status": "No related test found (not confirmed from indexed files)",
                    "explanation": f"No existing unit or integration tests were found covering '{df.file_path}'.",
                    "suggested_test": f"Create test suite `tests/test_{mod_stem}.py` verifying core workflows and parameter validation for {df.file_path}.",
                    "why_it_matters": "Ensures baseline correctness and prevents regressions when this module is invoked by external callers."
                })
            else:
                # Case 2: Some tests exist, but examine changed symbols
                for sym in symbols_in_file:
                    s_name = sym["symbol_name"]
                    if s_name in ("module_scope", "module_block_1"):
                        continue
                    # Check if any test mentions this symbol
                    is_covered = any(s_name.lower() in t["relationship"].lower() for t in matching_tests)
                    if not is_covered:
                        gaps.append({
                            "file_path": df.file_path,
                            "symbol_name": s_name,
                            "citation": sym["citation"],
                            "gap_category": "untested_behavior",
                            "gap_status": f"Behavior in '{s_name}' appears to lack dedicated test coverage",
                            "explanation": f"Test files exist for '{mod_stem}', but no test case specifically exercises symbol '{s_name}'.",
                            "suggested_test": f"Add test case `test_{s_name}_validation` in {matching_tests[0]['test_file']} verifying valid inputs and edge cases.",
                            "why_it_matters": f"Directly tests boundary conditions and exception handling within '{s_name}' to avoid runtime failures."
                        })

        return gaps
