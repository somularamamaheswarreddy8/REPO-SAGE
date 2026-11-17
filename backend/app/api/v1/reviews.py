from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.core.database import get_db
from app.models.repository import Repository, RepositorySettings
from app.models.review import PRReview, ReviewFinding
from app.models.code_chunk import CodeChunk
from app.models.relationship import CodeRelationship
from app.models.user import User
from app.core.auth import get_current_user_optional, verify_repository_access
from app.schemas.review import (
    PRReviewCreateRequest,
    PRReviewResponse,
    PublishCommentsRequest,
    PublishCommentsResponse,
    PRImpactResponse,
)
from app.services.reviewer.engine import PRReviewEngine
from app.services.reviewer.impact_analyzer import PRImpactAnalyzer
from app.services.reviewer.exporter import (
    export_as_markdown,
    export_as_json,
    export_as_sarif
)
from app.services.github.factory import get_github_client

router = APIRouter(prefix="/repositories/{id}/reviews", tags=["PR Reviews"])


@router.post("", response_model=PRReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_pr_review(
    id: int,
    payload: PRReviewCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates and executes a structured AI code review of a pull request diff.
    Findings are verified, deduplicated, and presented for developer review.
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    engine = PRReviewEngine(db)
    review = await engine.review_pull_request(
        repository=repo,
        pr_number=payload.pr_number,
        title=payload.title,
        head_commit_sha=payload.head_commit_sha,
        base_commit_sha=payload.base_commit_sha,
        custom_diff=payload.custom_diff
    )

    # Reload with findings
    stmt = select(PRReview).options(selectinload(PRReview.findings)).where(PRReview.id == review.id)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.get("", response_model=List[PRReviewResponse])
async def list_reviews(id: int, db: AsyncSession = Depends(get_db)):
    """Lists all reviews performed on this repository."""
    stmt = (
        select(PRReview)
        .options(selectinload(PRReview.findings))
        .where(PRReview.repository_id == id)
        .order_by(PRReview.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{review_id}", response_model=PRReviewResponse)
async def get_review_details(id: int, review_id: int, db: AsyncSession = Depends(get_db)):
    """Fetches complete review details and structured findings."""
    stmt = (
        select(PRReview)
        .options(selectinload(PRReview.findings))
        .where(PRReview.id == review_id, PRReview.repository_id == id)
    )
    res = await db.execute(stmt)
    review = res.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review


@router.get("/{review_id}/export")
async def export_review(
    id: int,
    review_id: int,
    format: str = Query(default="markdown", pattern="^(markdown|json|sarif)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exports PR review results in standard formats:
    - Markdown (.md)
    - JSON (.json)
    - OASIS SARIF v2.1.0 (.sarif) for GitHub Code Scanning / CI security pipelines
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    stmt = (
        select(PRReview)
        .options(selectinload(PRReview.findings))
        .where(PRReview.id == review_id, PRReview.repository_id == id)
    )
    res = await db.execute(stmt)
    review = res.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    fmt = format.lower()
    if fmt == "markdown":
        md_text = export_as_markdown(review, repo)
        return PlainTextResponse(
            content=md_text,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="reposage_review_pr{review.pr_number}.md"'}
        )
    elif fmt == "sarif":
        sarif_data = export_as_sarif(review, repo)
        return JSONResponse(
            content=sarif_data,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="reposage_review_pr{review.pr_number}.sarif"'}
        )
    else:  # json
        json_data = export_as_json(review, repo)
        return JSONResponse(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="reposage_review_pr{review.pr_number}.json"'}
        )


@router.post("/{review_id}/publish", response_model=PublishCommentsResponse)
async def publish_selected_review_comments(
    id: int,
    review_id: int,
    payload: PublishCommentsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Publishes user-selected review comments to GitHub.
    CRITICAL: Requires explicit developer approval flag (`explicit_user_approval: true`).
    Never publishes comments automatically without user consent.
    """
    if not payload.explicit_user_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit user approval is required to publish review comments."
        )

    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    review = await db.get(PRReview, review_id)
    if not review or review.repository_id != id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    engine = PRReviewEngine(db)
    result = await engine.publish_approved_comments(
        repository=repo,
        pr_review=review,
        finding_ids=payload.finding_ids,
        user_identifier=payload.user_identifier
    )

    return PublishCommentsResponse(**result)


@router.post("/{review_id}/ci-check", status_code=status.HTTP_200_OK)
async def trigger_ci_check_summary(
    id: int,
    review_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Publishes an advisory GitHub Check summary for the pull request.
    Allowed ONLY if repository owner has enabled optional CI in repository settings.
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    # Verify settings
    settings_stmt = select(RepositorySettings).where(RepositorySettings.repository_id == id)
    settings_res = await db.execute(settings_stmt)
    settings_obj = settings_res.scalar_one_or_none()

    if not settings_obj or not settings_obj.optional_ci_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advisory CI Check is disabled for this repository. A repository owner must explicitly enable it in Settings."
        )

    stmt = select(PRReview).options(selectinload(PRReview.findings)).where(PRReview.id == review_id, PRReview.repository_id == id)
    res = await db.execute(stmt)
    review = res.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    engine = PRReviewEngine(db)
    await engine.publish_advisory_ci_check(repo, review)

    return {"message": "Advisory GitHub Check summary successfully published.", "review_id": review.id}


@router.get("/{review_id}/impact", response_model=PRImpactResponse)
async def get_pr_change_impact_analysis(
    id: int,
    review_id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Static PR change impact analysis and test-gap advisor:
    - Identifies changed files and key functions/symbols
    - Traces downstream modules importing or calling changed code
    - Finds potentially affected tests
    - Marks untraced dynamic areas as uncertain
    - Suggests specific test cases with reasons and line citations
    Never executes repository code.
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    stmt = select(PRReview).options(selectinload(PRReview.findings)).where(PRReview.id == review_id, PRReview.repository_id == id)
    res = await db.execute(stmt)
    review = res.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    # Fetch PR diff
    gh = get_github_client(is_demo=repo.is_demo)
    try:
        diff_text = await gh.get_pull_request_diff(repo.full_name, review.pr_number)
    except Exception:
        diff_text = ""

    # Fetch chunks
    stmt_chunks = select(CodeChunk).where(CodeChunk.repository_id == id)
    res_chunks = await db.execute(stmt_chunks)
    chunks = res_chunks.scalars().all()

    # Fetch relationships
    stmt_rels = select(CodeRelationship).where(CodeRelationship.repository_id == id)
    res_rels = await db.execute(stmt_rels)
    relationships = res_rels.scalars().all()

    analyzer = PRImpactAnalyzer(repo, review.pr_number, diff_text, chunks, relationships)
    return analyzer.analyze()

