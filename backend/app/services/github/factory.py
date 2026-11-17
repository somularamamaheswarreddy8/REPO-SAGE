from typing import Optional
from app.core.config import settings
from app.services.github.base import BaseGitHubClient
from app.services.github.mock import MockGitHubClient
from app.services.github.client import GitHubAppClient


def get_github_client(is_demo: bool = False) -> BaseGitHubClient:
    """
    Returns GitHub client.
    Defaults to MockGitHubClient if is_demo is True or if real credentials are missing.
    """
    if not is_demo and settings.GITHUB_APP_ID and settings.GITHUB_PRIVATE_KEY:
        return GitHubAppClient(
            app_id=settings.GITHUB_APP_ID,
            private_key=settings.GITHUB_PRIVATE_KEY
        )
    return MockGitHubClient()
