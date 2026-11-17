import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db, AsyncSessionLocal
from app.models.repository import Repository
from app.models.code_chunk import CodeChunk
from app.schemas.indexing import IndexingTriggerRequest, IndexingStatusResponse
from app.services.indexing.pipeline import run_indexing_pipeline
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repositories/{id}/index", tags=["Indexing"])


async def background_indexer_runner(repo_id: int, branch: str, force: bool):
    """Fallback runner for background indexing when Celery/Redis daemon is not running."""
    async with AsyncSessionLocal() as db:
        try:
            await run_indexing_pipeline(db, repo_id, branch, force)
        except Exception as e:
            logger.error(f"Background indexing runner failed for repo {repo_id}: {e}", exc_info=True)
            try:
                repo = await db.get(Repository, repo_id)
                if repo:
                    repo.indexing_status = "failed"
                    repo.indexing_error = str(e)
                    await db.commit()
            except Exception as commit_err:
                logger.error(f"Failed to record indexing failure for repo {repo_id}: {commit_err}")


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def trigger_indexing(
    id: int,
    payload: IndexingTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Queues asynchronous repository code indexing."""
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    repo.indexing_status = "queued"
    repo.indexing_progress = 0.0
    repo.indexing_error = None
    await db.commit()

    # When eager or standalone, dispatch via BackgroundTasks so HTTP response returns immediately (202 Accepted)
    dispatched_to_celery = False
    if not settings.CELERY_TASK_ALWAYS_EAGER:
        try:
            from app.tasks.workers import task_index_repository
            task_index_repository.delay(
                repository_id=id,
                branch=payload.branch,
                force_full_reindex=payload.force_full_reindex
            )
            dispatched_to_celery = True
        except Exception as e:
            logger.warning(f"Could not dispatch to Celery broker: {e}. Executing via internal background task runner.")
            background_tasks.add_task(background_indexer_runner, id, payload.branch, payload.force_full_reindex)
    else:
        background_tasks.add_task(background_indexer_runner, id, payload.branch, payload.force_full_reindex)

    return {
        "message": "Repository indexing queued successfully.",
        "repository_id": id,
        "dispatched_to_celery": dispatched_to_celery,
        "status": "queued"
    }


@router.get("/status", response_model=IndexingStatusResponse)
async def get_indexing_status(id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves current repository indexing status and progress."""
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    count_stmt = select(func.count(CodeChunk.id)).where(CodeChunk.repository_id == id)
    count_res = await db.execute(count_stmt)
    total_chunks = count_res.scalar_one()

    return IndexingStatusResponse(
        repository_id=repo.id,
        full_name=repo.full_name,
        status=repo.indexing_status,
        progress=repo.indexing_progress,
        indexed_commit_sha=repo.indexed_commit_sha,
        total_chunks=total_chunks,
        error=repo.indexing_error,
        updated_at=repo.updated_at
    )
