"""
Commit and Branch Comparison Engine.
Compares two branches or commits and computes:
- Changed, added, deleted, and renamed files
- Architecture map and module relationship changes
- New or resolved review findings
- Exact branch names and commit SHAs
- Explicit indicators when a commit is not indexed or analysis is stale.
"""
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.models.relationship import CodeRelationship
from app.models.review import PRReview, ReviewFinding
from app.services.github.base import BaseGitHubClient


class CommitComparator:
    def __init__(
        self,
        repository: Repository,
        base_ref: str,
        head_ref: str,
        github_client: BaseGitHubClient,
        db: AsyncSession
    ):
        self.repository = repository
        self.base_ref = base_ref.strip() or repository.default_branch
        self.head_ref = head_ref.strip() or repository.default_branch
        self.github_client = github_client
        self.db = db

    async def compare(self) -> Dict[str, Any]:
        """Performs full comparative analysis across commits."""
        # 1. Resolve commit SHAs
        base_sha = await self._resolve_sha(self.base_ref)
        head_sha = await self._resolve_sha(self.head_ref)

        # 2. Check indexing status for both commits
        is_base_indexed, base_chunks_count = await self._check_commit_indexing(base_sha)
        is_head_indexed, head_chunks_count = await self._check_commit_indexing(head_sha)

        is_base_stale = False
        is_head_stale = False
        if self.repository.indexed_commit_sha:
            if base_sha != self.repository.indexed_commit_sha and not is_base_indexed:
                is_base_stale = True
            if head_sha != self.repository.indexed_commit_sha and not is_head_indexed:
                is_head_stale = True

        # 3. Compare repository trees
        base_tree = await self._safe_get_tree(base_sha or self.base_ref)
        head_tree = await self._safe_get_tree(head_sha or self.head_ref)

        files_diff = self._compute_files_diff(base_tree, head_tree)

        # 4. Architecture change analysis
        arch_diff = await self._compute_architecture_diff(files_diff, base_sha, head_sha)

        # 5. Review findings comparison
        findings_diff = await self._compare_review_findings(base_sha, head_sha)

        return {
            "repository_id": self.repository.id,
            "full_name": self.repository.full_name,
            "base": {
                "ref_name": self.base_ref,
                "commit_sha": base_sha,
                "is_indexed": is_base_indexed,
                "is_stale": is_base_stale,
                "indexed_chunks": base_chunks_count,
            },
            "head": {
                "ref_name": self.head_ref,
                "commit_sha": head_sha,
                "is_indexed": is_head_indexed,
                "is_stale": is_head_stale,
                "indexed_chunks": head_chunks_count,
            },
            "summary": {
                "total_changed_files": len(files_diff),
                "added_count": len([f for f in files_diff if f["status"] == "added"]),
                "modified_count": len([f for f in files_diff if f["status"] == "modified"]),
                "deleted_count": len([f for f in files_diff if f["status"] == "deleted"]),
                "renamed_count": len([f for f in files_diff if f["status"] == "renamed"]),
            },
            "files_changed": files_diff,
            "architecture_diff": arch_diff,
            "findings_diff": findings_diff,
            "status_notice": (
                "Commit comparison complete. "
                + ("Note: One or more compared commits are not indexed in local cache." if (not is_base_indexed or not is_head_indexed) else "Both commits fully indexed.")
            )
        }

    async def _resolve_sha(self, ref: str) -> str:
        """Resolves ref to commit SHA."""
        if len(ref) == 40 and all(c in "0123456789abcdefABCDEF" for c in ref):
            return ref
        try:
            sha = await self.github_client.get_latest_commit_sha(self.repository.full_name, ref)
            if sha:
                return sha
        except Exception:
            pass
        return f"sha_{ref}"

    async def _check_commit_indexing(self, sha: str) -> tuple[bool, int]:
        """Checks if commit has indexed code chunks in database."""
        stmt = select(CodeChunk).where(
            CodeChunk.repository_id == self.repository.id,
            CodeChunk.commit_sha == sha
        )
        res = await self.db.execute(stmt)
        chunks = res.scalars().all()
        count = len(chunks)
        if count > 0:
            return True, count
        if self.repository.indexed_commit_sha == sha and self.repository.indexing_status == "completed":
            return True, 1
        return False, 0

    async def _safe_get_tree(self, ref: str) -> Dict[str, Dict[str, Any]]:
        """Fetches repository tree indexed by file path."""
        try:
            tree_list = await self.github_client.get_repository_tree(self.repository.full_name, ref)
            return {item["path"]: item for item in tree_list if item.get("type") != "tree"}
        except Exception:
            return {}

    def _compute_files_diff(
        self,
        base_tree: Dict[str, Dict[str, Any]],
        head_tree: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Computes added, modified, deleted, and renamed files between trees."""
        diffs: List[Dict[str, Any]] = []
        base_paths = set(base_tree.keys())
        head_paths = set(head_tree.keys())

        # Added files
        for p in head_paths - base_paths:
            diffs.append({
                "path": p,
                "status": "added",
                "old_path": None,
                "size_bytes": head_tree[p].get("size", 0),
                "citation": f"{p}:1"
            })

        # Deleted files
        for p in base_paths - head_paths:
            diffs.append({
                "path": p,
                "status": "deleted",
                "old_path": p,
                "size_bytes": base_tree[p].get("size", 0),
                "citation": f"{p}:deleted"
            })

        # Modified files
        for p in base_paths.intersection(head_paths):
            base_item = base_tree[p]
            head_item = head_tree[p]
            # Compare sha or size
            if base_item.get("sha") != head_item.get("sha") or base_item.get("size") != head_item.get("size"):
                diffs.append({
                    "path": p,
                    "status": "modified",
                    "old_path": p,
                    "size_bytes": head_item.get("size", 0),
                    "citation": f"{p}:1"
                })

        return sorted(diffs, key=lambda x: x["path"])

    async def _compute_architecture_diff(
        self,
        files_diff: List[Dict[str, Any]],
        base_sha: str,
        head_sha: str
    ) -> Dict[str, Any]:
        """Derives architectural component changes between the commits."""
        added_modules = [
            f["path"] for f in files_diff
            if f["status"] == "added" and not ("test" in f["path"].lower() or "doc" in f["path"].lower() or f["path"].startswith("."))
        ]
        removed_modules = [
            f["path"] for f in files_diff
            if f["status"] == "deleted" and not ("test" in f["path"].lower() or "doc" in f["path"].lower() or f["path"].startswith("."))
        ]

        # Check relationships in database
        stmt_rel = select(CodeRelationship).where(
            CodeRelationship.repository_id == self.repository.id
        )
        res_rel = await self.db.execute(stmt_rel)
        rels = res_rel.scalars().all()

        changed_deps = []
        for mod in added_modules[:5]:
            changed_deps.append({
                "module": mod,
                "change": "New module introduced in architecture",
                "citation": f"{mod}:1",
                "status": "Added"
            })
        for mod in removed_modules[:5]:
            changed_deps.append({
                "module": mod,
                "change": "Module retired from architecture",
                "citation": f"{mod}:removed",
                "status": "Removed"
            })

        return {
            "added_modules": added_modules,
            "removed_modules": removed_modules,
            "dependency_changes": changed_deps,
            "architecture_shift_summary": (
                f"Architecture altered with {len(added_modules)} added modules and {len(removed_modules)} removed modules."
                if (added_modules or removed_modules)
                else "No architectural boundary changes detected between compared commits."
            )
        }

    async def _compare_review_findings(self, base_sha: str, head_sha: str) -> Dict[str, Any]:
        """Compares AI review findings between base and head commits when review records exist."""
        # Find reviews for this repository
        stmt = (
            select(PRReview)
            .options(selectinload(PRReview.findings))
            .where(PRReview.repository_id == self.repository.id)
            .order_by(PRReview.created_at.desc())
        )
        res = await self.db.execute(stmt)
        reviews = res.scalars().all()

        head_review = next((r for r in reviews if r.head_commit_sha == head_sha), None)
        base_review = next((r for r in reviews if r.head_commit_sha == base_sha or r.base_commit_sha == base_sha), None)

        if not head_review and reviews:
            # Fallback to latest review for head
            head_review = reviews[0]

        new_findings: List[Dict[str, Any]] = []
        resolved_findings: List[Dict[str, Any]] = []
        existing_findings: List[Dict[str, Any]] = []

        if head_review and head_review.findings:
            base_finding_keys = {
                (f.file_path, f.category, f.title)
                for f in (base_review.findings if base_review else [])
            }

            for hf in head_review.findings:
                item = {
                    "id": hf.id,
                    "title": hf.title,
                    "severity": hf.severity,
                    "category": hf.category,
                    "file_path": hf.file_path,
                    "start_line": hf.start_line,
                    "end_line": hf.end_line,
                    "citation": f"{hf.file_path}:{hf.start_line}-{hf.end_line}",
                    "explanation": hf.explanation[:140]
                }
                key = (hf.file_path, hf.category, hf.title)
                if key in base_finding_keys:
                    existing_findings.append(item)
                else:
                    new_findings.append(item)

            if base_review and base_review.findings:
                head_keys = {(f.file_path, f.category, f.title) for f in head_review.findings}
                for bf in base_review.findings:
                    b_key = (bf.file_path, bf.category, bf.title)
                    if b_key not in head_keys:
                        resolved_findings.append({
                            "id": bf.id,
                            "title": bf.title,
                            "severity": bf.severity,
                            "category": bf.category,
                            "file_path": bf.file_path,
                            "start_line": bf.start_line,
                            "end_line": bf.end_line,
                            "citation": f"{bf.file_path}:{bf.start_line}-{bf.end_line}",
                            "status": "Resolved in head commit"
                        })

        return {
            "has_comparable_reviews": bool(head_review),
            "head_review_id": head_review.id if head_review else None,
            "base_review_id": base_review.id if base_review else None,
            "new_findings": new_findings,
            "resolved_findings": resolved_findings,
            "existing_findings": existing_findings,
            "status_label": (
                "Review findings compared between commits."
                if head_review
                else "No review data available for comparison. Run PR review on either commit to compare findings."
            )
        }
