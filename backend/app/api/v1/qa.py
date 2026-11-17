from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.repository import Repository
from app.schemas.qa import CodeQuestionRequest, CodeQuestionResponse
from app.services.qa.service import CodeQAService

router = APIRouter(prefix="/repositories/{id}/qa", tags=["Code Q&A"])


@router.post("", response_model=CodeQuestionResponse)
async def ask_codebase_question(
    id: int,
    payload: CodeQuestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Answers questions grounded in the indexed repository code.
    Cites specific file paths and line ranges. If evidence is lacking or index is incomplete,
    explicitly explains it using 'Not confirmed from indexed files.'
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if repo.indexing_status != "completed":
        reason = repo.indexing_error or f"Repository indexing is {repo.indexing_status} ({repo.indexing_progress}%)."
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository '{repo.full_name}' cannot be queried: {reason} Please index the repository before asking questions."
        )

    qa_service = CodeQAService(db)
    response = await qa_service.answer_question(
        repository=repo,
        query=payload.query,
        max_citations=payload.max_citations
    )
    return response
