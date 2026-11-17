import asyncio
import logging
import concurrent.futures
from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.logging import job_id_ctx
from app.services.indexing.pipeline import run_indexing_pipeline
from app.services.reviewer.engine import PRReviewEngine
from app.models.repository import Repository

logger = logging.getLogger(__name__)


def _run_async_in_worker(coro_fn):
    """Executes an async function safely, even if an event loop is running in the caller."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(coro_fn()))
            return future.result()
    else:
        return asyncio.run(coro_fn())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def task_index_repository(self, repository_id: int, branch: str = None, force_full_reindex: bool = False):
    """Celery background task for repository indexing with safe retries."""
    job_id_ctx.set(self.request.id)
    logger.info(f"[JOB {self.request.id}] Starting repository indexing for repo_id={repository_id}")

    async def _run():
        async with AsyncSessionLocal() as db:
            return await run_indexing_pipeline(
                db=db,
                repository_id=repository_id,
                branch=branch,
                force_full_reindex=force_full_reindex
            )

    try:
        return _run_async_in_worker(_run)
    except Exception as exc:
        logger.error(f"[JOB {self.request.id}] Error in task_index_repository: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def task_review_pull_request(
    self,
    repository_id: int,
    pr_number: int,
    title: str = None,
    head_commit_sha: str = None,
    base_commit_sha: str = None,
    custom_diff: str = None
):
    """Celery background task for PR review."""
    job_id_ctx.set(self.request.id)
    logger.info(f"[JOB {self.request.id}] Starting PR review for repo_id={repository_id}, pr={pr_number}")

    async def _run():
        async with AsyncSessionLocal() as db:
            repo = await db.get(Repository, repository_id)
            if not repo:
                raise ValueError(f"Repository {repository_id} not found")
            engine = PRReviewEngine(db)
            review = await engine.review_pull_request(
                repository=repo,
                pr_number=pr_number,
                title=title,
                head_commit_sha=head_commit_sha,
                base_commit_sha=base_commit_sha,
                custom_diff=custom_diff
            )
            return {"review_id": review.id, "status": review.status, "findings_count": len(review.findings)}

    try:
        return _run_async_in_worker(_run)
    except Exception as exc:
        logger.error(f"[JOB {self.request.id}] Error in task_review_pull_request: {exc}", exc_info=True)
        raise self.retry(exc=exc)
