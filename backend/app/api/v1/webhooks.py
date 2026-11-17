import json
import logging
from fastapi import APIRouter, Request, Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_github_signature
from app.models.repository import Repository, RepositorySettings
from app.services.indexing.pipeline import run_indexing_pipeline
from app.services.reviewer.engine import PRReviewEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/github/webhooks", tags=["GitHub Webhooks"])


@router.post("", status_code=status.HTTP_200_OK)
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Receives and processes GitHub App webhooks.
    Validates HMAC SHA-256 signature against GITHUB_WEBHOOK_SECRET.
    """
    payload_bytes = await request.body()

    # Validate HMAC signature if secret is configured
    if settings.GITHUB_WEBHOOK_SECRET:
        if not verify_github_signature(payload_bytes, settings.GITHUB_WEBHOOK_SECRET, x_hub_signature_256):
            logger.warning("Rejected webhook with invalid HMAC signature.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook HMAC SHA-256 signature."
            )

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload")

    event = x_github_event or request.headers.get("X-GitHub-Event", "ping")
    logger.info(f"Received GitHub webhook event: '{event}'")

    if event == "ping":
        return {"message": "pong"}

    # Handle Push Event -> Incremental Indexing
    if event == "push":
        repo_data = payload.get("repository", {})
        repo_full_name = repo_data.get("full_name")
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else "main"

        stmt = select(Repository).where(Repository.full_name == repo_full_name)
        res = await db.execute(stmt)
        repo = res.scalar_one_or_none()
        if repo:
            logger.info(f"Push event triggered incremental indexing for {repo.full_name} on branch {branch}")
            # Run incremental indexing pipeline
            await run_indexing_pipeline(db, repo.id, branch=branch, force_full_reindex=False)
            return {"status": "indexed", "repository": repo.full_name}

    # Handle Pull Request Event
    elif event == "pull_request":
        action = payload.get("action")
        if action in {"opened", "synchronize", "reopened"}:
            repo_data = payload.get("repository", {})
            repo_full_name = repo_data.get("full_name")
            pr_data = payload.get("pull_request", {})
            pr_number = pr_data.get("number")

            stmt = select(Repository).where(Repository.full_name == repo_full_name)
            res = await db.execute(stmt)
            repo = res.scalar_one_or_none()

            if repo and pr_number:
                settings_stmt = select(RepositorySettings).where(RepositorySettings.repository_id == repo.id)
                settings_res = await db.execute(settings_stmt)
                repo_settings = settings_res.scalar_one_or_none()

                if repo_settings and repo_settings.auto_review_prs:
                    logger.info(f"PR #{pr_number} opened/updated in {repo.full_name}; queuing auto-review.")
                    engine = PRReviewEngine(db)
                    await engine.review_pull_request(
                        repository=repo,
                        pr_number=pr_number,
                        title=pr_data.get("title"),
                        head_commit_sha=pr_data.get("head", {}).get("sha"),
                        base_commit_sha=pr_data.get("base", {}).get("sha")
                    )
                    return {"status": "reviewed", "pr_number": pr_number}

    return {"status": "received", "event": event}
