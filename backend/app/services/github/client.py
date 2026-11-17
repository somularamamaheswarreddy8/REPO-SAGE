import time
import logging
from typing import List, Dict, Any, Optional
import httpx
import jwt
from app.services.github.base import BaseGitHubClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubAppClient(BaseGitHubClient):
    """
    Production GitHub App client.
    
    Required Least-Privilege Permissions:
    - Repository metadata: Read-only (to verify repository identity and default branch)
    - Repository contents: Read-only (to fetch source code for indexing and diff inspection)
    - Pull requests: Read & write (to read diffs and publish review comments upon explicit approval)
    - Checks: Read & write (to create advisory check run summaries when enabled by repository owner)
    
    Security:
    - Private key and installation tokens are held strictly in server memory.
    - Never leaked to client browser or logged.
    """

    def __init__(self, app_id: str, private_key: str):
        self.app_id = app_id
        self.private_key = private_key
        self._installation_tokens: Dict[str, Dict[str, Any]] = {}

    def _generate_jwt(self) -> str:
        """Generates GitHub App RS256 JWT valid for 10 minutes."""
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": self.app_id
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def _get_installation_token(self, repo_full_name: str) -> str:
        """Gets or refreshes an installation access token for the repository."""
        cached = self._installation_tokens.get(repo_full_name)
        if cached and cached["expires_at"] > time.time() + 60:
            return cached["token"]

        app_jwt = self._generate_jwt()
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # First find installation ID for this repo
            resp = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/installation",
                headers=headers
            )
            resp.raise_for_status()
            installation_id = resp.json()["id"]

            # Exchange for installation access token
            token_resp = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers=headers
            )
            token_resp.raise_for_status()
            data = token_resp.json()
            token = data["token"]
            
            # Store in cache
            self._installation_tokens[repo_full_name] = {
                "token": token,
                "expires_at": time.time() + 3500
            }
            return token

    async def _request(
        self,
        method: str,
        path: str,
        repo_full_name: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        accept: str = "application/vnd.github+json"
    ) -> httpx.Response:
        token = await self._get_installation_token(repo_full_name)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28"
        }
        url = f"https://api.github.com{path}"
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.request(method, url, headers=headers, params=params, json=json_data)
            resp.raise_for_status()
            return resp

    async def get_repository(self, repo_full_name: str) -> Dict[str, Any]:
        resp = await self._request("GET", f"/repos/{repo_full_name}", repo_full_name)
        return resp.json()

    async def get_repository_tree(self, repo_full_name: str, ref: str) -> List[Dict[str, Any]]:
        resp = await self._request("GET", f"/repos/{repo_full_name}/git/trees/{ref}?recursive=1", repo_full_name)
        data = resp.json()
        return data.get("tree", [])

    async def get_file_content(self, repo_full_name: str, file_path: str, ref: str) -> str:
        resp = await self._request(
            "GET",
            f"/repos/{repo_full_name}/contents/{file_path}",
            repo_full_name,
            params={"ref": ref},
            accept="application/vnd.github.raw+json"
        )
        return resp.text

    async def get_latest_commit_sha(self, repo_full_name: str, branch: str) -> str:
        resp = await self._request("GET", f"/repos/{repo_full_name}/commits/{branch}", repo_full_name)
        return resp.json()["sha"]

    async def get_pull_request(self, repo_full_name: str, pr_number: int) -> Dict[str, Any]:
        resp = await self._request("GET", f"/repos/{repo_full_name}/pulls/{pr_number}", repo_full_name)
        return resp.json()

    async def get_pull_request_diff(self, repo_full_name: str, pr_number: int) -> str:
        resp = await self._request(
            "GET",
            f"/repos/{repo_full_name}/pulls/{pr_number}",
            repo_full_name,
            accept="application/vnd.github.v3.diff"
        )
        return resp.text

    async def publish_review_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_sha: str,
        comments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        # Post review with comments
        payload = {
            "commit_id": commit_sha,
            "body": "RepoSage AI Code Review Findings (Approved by developer)",
            "event": "COMMENT",
            "comments": comments
        }
        resp = await self._request(
            "POST",
            f"/repos/{repo_full_name}/pulls/{pr_number}/reviews",
            repo_full_name,
            json_data=payload
        )
        return resp.json()

    async def publish_advisory_check(
        self,
        repo_full_name: str,
        head_sha: str,
        title: str,
        summary: str,
        conclusion: str = "neutral"
    ) -> Dict[str, Any]:
        payload = {
            "name": "RepoSage / Advisory Review",
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": conclusion,
            "output": {
                "title": title,
                "summary": summary
            }
        }
        resp = await self._request(
            "POST",
            f"/repos/{repo_full_name}/check-runs",
            repo_full_name,
            json_data=payload
        )
        return resp.json()
