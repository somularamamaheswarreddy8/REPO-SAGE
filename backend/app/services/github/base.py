from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseGitHubClient(ABC):
    @abstractmethod
    async def get_repository(self, repo_full_name: str) -> Dict[str, Any]:
        """Fetches repository metadata."""
        pass

    @abstractmethod
    async def get_repository_tree(self, repo_full_name: str, ref: str) -> List[Dict[str, Any]]:
        """Returns flat list of file metadata {path, size, type, sha}."""
        pass

    @abstractmethod
    async def get_file_content(self, repo_full_name: str, file_path: str, ref: str) -> str:
        """Retrieves raw content of a file at a specific commit/ref."""
        pass

    @abstractmethod
    async def get_latest_commit_sha(self, repo_full_name: str, branch: str) -> str:
        """Returns the latest commit SHA for a branch."""
        pass

    @abstractmethod
    async def get_pull_request(self, repo_full_name: str, pr_number: int) -> Dict[str, Any]:
        """Fetches pull request details."""
        pass

    @abstractmethod
    async def get_pull_request_diff(self, repo_full_name: str, pr_number: int) -> str:
        """Fetches raw unified diff of a pull request."""
        pass

    @abstractmethod
    async def publish_review_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_sha: str,
        comments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Publishes user-approved review comments to the PR.
        Requires explicit human approval prior to invocation.
        """
        pass

    @abstractmethod
    async def publish_advisory_check(
        self,
        repo_full_name: str,
        head_sha: str,
        title: str,
        summary: str,
        conclusion: str = "neutral"
    ) -> Dict[str, Any]:
        """
        Publishes an advisory GitHub Check summary on PR head commit.
        Must only run when explicitly enabled by repository owner in settings.
        Does not block merges by default (conclusion: neutral or success).
        """
        pass
