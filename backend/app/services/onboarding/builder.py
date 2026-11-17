"""
Repository Onboarding Guide Service ("Start here" view).
Evidence-grounded onboarding guide identifying:
- Likely application entry points with line citations
- Important modules and their responsibilities
- How major modules connect via static import/call graphs
- Existing tests related to those modules
- All claims cited or explicitly labeled 'Not confirmed from indexed files.'
"""
import re
from typing import List, Dict, Any, Optional
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.models.relationship import CodeRelationship
from app.models.repository_file import RepositoryFile

ENTRY_POINT_PATTERNS = [
    re.compile(r"^(?:src/)?(?:main|app|server|index|manage|cli)\.(?:py|ts|js|go|rs|rb|php)$", re.IGNORECASE),
    re.compile(r"^.*Application\.(?:java|kt|scala)$", re.IGNORECASE),
    re.compile(r"^(?:Dockerfile|Makefile|docker-compose\.ya?ml)$", re.IGNORECASE),
    re.compile(r"^(?:package\.json|pyproject\.toml|Cargo\.toml|go\.mod)$", re.IGNORECASE),
]


class OnboardingGuideBuilder:
    def __init__(
        self,
        repository: Repository,
        chunks: List[CodeChunk],
        relationships: List[CodeRelationship],
        files: Optional[List[RepositoryFile]] = None
    ):
        self.repository = repository
        self.chunks = chunks
        self.relationships = relationships
        self.files = files or []

    def build_guide(self) -> Dict[str, Any]:
        """Builds a complete, evidence-grounded onboarding guide."""
        entry_points = self._detect_entry_points()
        modules = self._detect_important_modules()
        connections = self._trace_module_connections(modules)
        test_mappings = self._map_module_tests(modules)

        return {
            "repository_id": self.repository.id,
            "full_name": self.repository.full_name,
            "branch": self.repository.default_branch,
            "commit_sha": self.repository.indexed_commit_sha,
            "indexing_status": self.repository.indexing_status,
            "overview_summary": self.repository.summary or "Repository initialized. Explore entry points and core modules below.",
            "entry_points": entry_points,
            "modules": modules,
            "module_connections": connections,
            "module_tests": test_mappings,
            "total_modules": len(modules),
            "total_entry_points": len(entry_points),
            "unconfirmed_note": "If a relationship or test is not verified from indexed chunks, it is explicitly labeled 'Not confirmed from indexed files.'"
        }

    def _detect_entry_points(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        seen_files = set()

        for chunk in self.chunks:
            p = chunk.file_path.replace("\\", "/")
            # Skip test files and assets
            if p.startswith("tests/") or p.startswith("test/") or ".spec." in p or ".test." in p:
                continue

            is_entry = False
            reason = "Entry point candidate based on filename convention"
            for pattern in ENTRY_POINT_PATTERNS:
                if pattern.search(p):
                    is_entry = True
                    if "docker" in p.lower():
                        reason = "Container execution and deployment configuration"
                    elif "makefile" in p.lower():
                        reason = "Build and execution automation entry point"
                    elif "package.json" in p or "pyproject.toml" in p or "cargo.toml" in p:
                        reason = "Project manifest, scripts, and package entry definition"
                    else:
                        reason = f"Primary application entry module ({chunk.language})"
                    break

            # Also check for main function in chunk
            if not is_entry and (chunk.symbol_name in ("main", "start", "run", "app", "create_app") or "def main(" in chunk.content or "func main(" in chunk.content or "fn main(" in chunk.content):
                is_entry = True
                reason = f"Contains entry point symbol '{chunk.symbol_name or 'main'}'"

            if is_entry and p not in seen_files:
                seen_files.add(p)
                entries.append({
                    "file_path": p,
                    "symbol": chunk.symbol_name,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "citation": f"{p}:{chunk.start_line}-{chunk.end_line}",
                    "language": chunk.language,
                    "reason": reason,
                    "confirmed": True,
                    "status_label": "Confirmed from indexed files"
                })

        if not entries:
            # Fallback entry point notification when no canonical entry is detected
            entries.append({
                "file_path": "Not detected",
                "symbol": None,
                "start_line": 0,
                "end_line": 0,
                "citation": "Not confirmed from indexed files.",
                "language": "unknown",
                "reason": "No canonical application entry point was detected in indexed files.",
                "confirmed": False,
                "status_label": "Not confirmed from indexed files."
            })

        return entries

    def _detect_important_modules(self) -> List[Dict[str, Any]]:
        """Identifies key functional modules and derives responsibilities from docstrings and symbols."""
        modules_by_file: Dict[str, Dict[str, Any]] = {}

        for chunk in self.chunks:
            p = chunk.file_path.replace("\\", "/")
            if p.startswith("tests/") or p.startswith("test/") or ".spec." in p or ".test." in p:
                continue
            if p.startswith("docs/") or p.startswith(".github/") or p in (".env", "README.md"):
                continue

            if p not in modules_by_file:
                # Extract first docstring / comment line as candidate responsibility
                doc = ""
                lines = chunk.content.splitlines()
                for line in lines[:8]:
                    stripped = line.strip(" \t'\"#/*")
                    if stripped and not stripped.startswith("import") and not stripped.startswith("from"):
                        doc = stripped
                        break

                modules_by_file[p] = {
                    "module_name": p,
                    "file_path": p,
                    "language": chunk.language,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "citation": f"{p}:{chunk.start_line}-{chunk.end_line}",
                    "responsibility": doc or f"Core module handling logic in {p}",
                    "symbols": [],
                    "confirmed": True,
                    "status_label": "Confirmed from indexed files"
                }

            if chunk.symbol_name and chunk.symbol_name not in modules_by_file[p]["symbols"]:
                modules_by_file[p]["symbols"].append(chunk.symbol_name)
                # Keep line range updated
                modules_by_file[p]["end_line"] = max(modules_by_file[p]["end_line"], chunk.end_line)
                modules_by_file[p]["citation"] = f"{p}:{modules_by_file[p]['start_line']}-{modules_by_file[p]['end_line']}"

        result = list(modules_by_file.values())
        return result[:15]  # Top modules

    def _trace_module_connections(self, modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Traces static imports and calls connecting major modules."""
        connections: List[Dict[str, Any]] = []
        module_paths = {m["file_path"] for m in modules}

        for rel in self.relationships:
            src = rel.source_file.replace("\\", "/")
            tgt = (rel.target_file or "").replace("\\", "/")
            
            # Match relationships between known modules or source files
            if src in module_paths or tgt in module_paths:
                connections.append({
                    "source_module": src,
                    "target_module": tgt or rel.target_symbol,
                    "relationship_type": rel.relationship_type,
                    "source_symbol": rel.source_symbol,
                    "target_symbol": rel.target_symbol,
                    "file_path": src,
                    "line_number": rel.line_number,
                    "citation": f"{src}:{rel.line_number}",
                    "evidence_snippet": rel.evidence_snippet[:140],
                    "confirmed": True,
                    "status_label": "Confirmed from indexed files"
                })

        # Check for modules with zero connections
        connected_srcs = {c["source_module"] for c in connections}
        connected_tgts = {c["target_module"] for c in connections}
        for m in modules:
            p = m["file_path"]
            if p not in connected_srcs and p not in connected_tgts:
                connections.append({
                    "source_module": p,
                    "target_module": "None detected",
                    "relationship_type": "independent",
                    "source_symbol": m["symbols"][0] if m["symbols"] else p,
                    "target_symbol": "None",
                    "file_path": p,
                    "line_number": m["start_line"],
                    "citation": f"{p}:{m['start_line']}",
                    "evidence_snippet": "No static imports or cross-module call relationships identified.",
                    "confirmed": False,
                    "status_label": "Not confirmed from indexed files."
                })

        return connections

    def _map_module_tests(self, modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Maps each module to its existing unit and integration tests with line citations."""
        # Find all test chunks
        test_chunks: List[CodeChunk] = [
            c for c in self.chunks
            if "test" in c.file_path.lower() or ".spec." in c.file_path.lower()
        ]

        test_mappings: List[Dict[str, Any]] = []

        for m in modules:
            mod_path = m["file_path"]
            mod_basename = mod_path.split("/")[-1].split(".")[0]

            # Find matching tests
            matched_tests = []
            for tc in test_chunks:
                tc_path = tc.file_path.replace("\\", "/")
                # Direct match by naming (e.g. test_payment.py for payment.py)
                if mod_basename in tc_path.lower():
                    matched_tests.append(tc)
                # Or check if test chunk mentions the module or its symbols
                elif any(sym.lower() in tc.content.lower() for sym in m["symbols"] if len(sym) > 3):
                    matched_tests.append(tc)

            if matched_tests:
                primary_test = matched_tests[0]
                tp = primary_test.file_path.replace("\\", "/")
                test_names = [t.symbol_name for t in matched_tests if t.symbol_name]
                test_mappings.append({
                    "module_path": mod_path,
                    "has_tests": True,
                    "test_file": tp,
                    "start_line": primary_test.start_line,
                    "end_line": primary_test.end_line,
                    "citation": f"{tp}:{primary_test.start_line}-{primary_test.end_line}",
                    "test_cases": list(set(test_names)) if test_names else ["Integrated test suite"],
                    "status_label": "Confirmed from indexed files"
                })
            else:
                test_mappings.append({
                    "module_path": mod_path,
                    "has_tests": False,
                    "test_file": None,
                    "start_line": None,
                    "end_line": None,
                    "citation": "Not confirmed from indexed files.",
                    "test_cases": [],
                    "status_label": "Not confirmed from indexed files."
                })

        return test_mappings
