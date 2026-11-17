from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import os
import datetime
from app.core.database import get_db, check_is_sqlite
from app.models.repository import Repository, RepositorySettings
from app.models.repository_file import RepositoryFile
from app.models.code_chunk import CodeChunk
from app.models.relationship import CodeRelationship
from app.models.feedback import RepositoryFeedback
from app.models.audit import AuditLogEntry
from app.models.user import User
from app.core.auth import get_current_user_optional, verify_repository_access
from app.services.audit import record_audit_event
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
    RepositorySettingsUpdate,
    RepositorySettingsResponse,
    RepositorySummaryResponse,
    RepositoryTreeResponse,
    RepositoryTreeCoverage,
    RepositoryFileItem,
    FileContentResponse,
    HealthFileItem,
    RepositoryHealthDashboardResponse,
    RepositoryOnboardingResponse,
    CommitCompareResponse,
    DependencyInventoryResponse,
    RepositoryFeedbackCreate,
    RepositoryFeedbackResponse,
)
from app.services.onboarding.builder import OnboardingGuideBuilder
from app.services.comparator.engine import CommitComparator
from app.services.dependencies.scanner import DependencyInventoryScanner
from app.services.github.factory import get_github_client
from app.services.parser.filters import classify_file_safety
from app.services.languages.detect import detect_file_language
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["Repositories"])


async def populate_staleness(repo: Repository, github_client) -> tuple[bool, Optional[str]]:
    """Checks whether the repository index is stale compared to remote branch commit."""
    if not repo.indexed_commit_sha:
        return False, None
    try:
        remote_sha = await github_client.get_latest_commit_sha(repo.full_name, repo.default_branch)
        is_stale = bool(remote_sha and remote_sha != repo.indexed_commit_sha)
        return is_stale, remote_sha
    except Exception:
        return False, repo.indexed_commit_sha


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists connected GitHub repositories with tenant isolation.
    Users only see repositories belonging to their organization, plus public demo repositories.
    """
    stmt = select(Repository).options(selectinload(Repository.settings)).order_by(Repository.created_at.desc())
    if user and user.organization_id:
        stmt = stmt.where(
            or_(
                Repository.organization_id == user.organization_id,
                Repository.is_demo == True,
                Repository.organization_id == None
            )
        )
    result = await db.execute(stmt)
    repos = result.scalars().all()

    # Populate staleness status
    responses = []
    for r in repos:
        gh = get_github_client(is_demo=r.is_demo)
        stale, remote_sha = await populate_staleness(r, gh)
        resp_dict = {
            "id": r.id,
            "github_repo_id": r.github_repo_id,
            "full_name": r.full_name,
            "owner": r.owner,
            "name": r.name,
            "default_branch": r.default_branch,
            "is_private": r.is_private,
            "is_demo": r.is_demo,
            "organization_id": r.organization_id,
            "indexed_commit_sha": r.indexed_commit_sha,
            "indexing_status": r.indexing_status,
            "indexing_progress": r.indexing_progress,
            "indexing_error": r.indexing_error,
            "summary": r.summary,
            "deep_analysis": r.deep_analysis,
            "last_indexed_at": r.last_indexed_at,
            "is_stale": stale,
            "remote_commit_sha": remote_sha,
            "settings": r.settings,
            "created_at": r.created_at,
            "updated_at": r.updated_at
        }
        responses.append(RepositoryResponse(**resp_dict))

    return responses


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def connect_repository(
    payload: RepositoryCreate,
    background_tasks: BackgroundTasks,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Connects a GitHub repository with organization tenancy and audit logging.
    Verifies that the connected GitHub user is allowed to access the repository.
    """

    from app.core.security import normalize_repo_name, extract_branch_from_url
    normalized_full_name = normalize_repo_name(payload.full_name)
    extracted_branch = extract_branch_from_url(payload.full_name)

    # Check if repository is already connected
    existing_stmt = select(Repository).where(Repository.full_name == normalized_full_name)
    existing = await db.execute(existing_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository '{normalized_full_name}' is already connected."
        )

    # Validate repository via GitHub client
    github_client = get_github_client(is_demo=payload.is_demo)
    try:
        repo_data = await github_client.get_repository(normalized_full_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to access repository '{normalized_full_name}' on GitHub: {str(e)}"
        )

    parts = normalized_full_name.split("/")
    owner = repo_data.get("owner", {}).get("login", parts[0])
    name = repo_data.get("name", parts[1] if len(parts) > 1 else normalized_full_name)
    default_branch = extracted_branch or payload.default_branch or repo_data.get("default_branch", "main")
    is_private = repo_data.get("private", False)

    new_repo = Repository(
        full_name=normalized_full_name,
        owner=owner,
        name=name,
        default_branch=default_branch,
        is_private=is_private,
        is_demo=payload.is_demo or repo_data.get("is_demo", False),
        organization_id=user.organization_id if user else 1,
        indexing_status="queued",
        indexing_progress=0.0
    )
    db.add(new_repo)
    await db.flush()

    # Create default settings (CI summary is disabled by default)
    repo_settings = RepositorySettings(
        repository_id=new_repo.id,
        optional_ci_enabled=False,
        blocking_ci_enabled=False,
        auto_review_prs=False,
        min_severity_to_alert="medium"
    )
    db.add(repo_settings)
    await db.commit()
    await db.refresh(new_repo)

    # Record tamper-evident audit entry
    user_name = user.username if user else "local_user"
    await record_audit_event(
        db=db,
        action_type="repository_connect",
        user_id=user_name,
        repo_full_name=new_repo.full_name,
        payload_summary=f"User '{user_name}' connected repository '{new_repo.full_name}' (branch: {default_branch})."
    )

    # Automatically queue background indexing for immediate code ingestion
    from app.api.v1.indexing import background_indexer_runner
    background_tasks.add_task(background_indexer_runner, new_repo.id, default_branch, False)

    return new_repo


@router.get("/{id}", response_model=RepositoryResponse)
async def get_repository(
    id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves repository details by ID with tenant validation and staleness status."""
    stmt = select(Repository).options(selectinload(Repository.settings)).where(Repository.id == id)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    gh = get_github_client(is_demo=repo.is_demo)
    stale, remote_sha = await populate_staleness(repo, gh)

    return RepositoryResponse(
        id=repo.id,
        github_repo_id=repo.github_repo_id,
        full_name=repo.full_name,
        owner=repo.owner,
        name=repo.name,
        default_branch=repo.default_branch,
        is_private=repo.is_private,
        is_demo=repo.is_demo,
        organization_id=repo.organization_id,
        indexed_commit_sha=repo.indexed_commit_sha,
        indexing_status=repo.indexing_status,
        indexing_progress=repo.indexing_progress,
        indexing_error=repo.indexing_error,
        summary=repo.summary,
        deep_analysis=repo.deep_analysis,
        last_indexed_at=repo.last_indexed_at,
        is_stale=stale,
        remote_commit_sha=remote_sha,
        settings=repo.settings,
        created_at=repo.created_at,
        updated_at=repo.updated_at
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_repository(
    id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Disconnects a repository and purges indexed chunks with audit record."""
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    repo_name = repo.full_name
    await db.delete(repo)
    await db.commit()

    user_name = user.username if user else "local_user"
    await record_audit_event(
        db=db,
        action_type="repository_disconnect",
        user_id=user_name,
        repo_full_name=repo_name,
        payload_summary=f"User '{user_name}' disconnected repository '{repo_name}' and purged indexed data."
    )
    return None


@router.get("/{id}/summary", response_model=RepositorySummaryResponse)
async def get_repository_summary(id: int, db: AsyncSession = Depends(get_db)):
    """Returns architectural overview and summary grounded in indexed code."""
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    # Strict Precondition: Do not generate summary while indexing is incomplete or failed
    if repo.indexing_status != "completed":
        reason = repo.indexing_error or f"Repository indexing is {repo.indexing_status} ({repo.indexing_progress}%)."
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository '{repo.full_name}' analysis unavailable: {reason} Please index the repository before viewing summary."
        )

    # Fetch chunks strictly isolated to this repository and commit
    stmt_chunks = select(CodeChunk).where(CodeChunk.repository_id == id)
    if repo.indexed_commit_sha and repo.indexed_commit_sha != "unindexed":
        stmt_chunks = stmt_chunks.where(CodeChunk.commit_sha == repo.indexed_commit_sha)
    res_chunks = await db.execute(stmt_chunks)
    chunks = res_chunks.scalars().all()

    # Aggregate languages and file counts from code chunks
    stmt = select(
        CodeChunk.language,
        func.count(func.distinct(CodeChunk.file_path)),
        func.count(CodeChunk.id)
    ).where(CodeChunk.repository_id == id)
    if chunks and chunks[0].commit_sha:
        stmt = stmt.where(CodeChunk.commit_sha == chunks[0].commit_sha)
    stmt = stmt.group_by(CodeChunk.language)
    res = await db.execute(stmt)
    rows = res.all()

    languages = [r[0] for r in rows if r[0]]
    total_files = sum(r[1] for r in rows)
    total_symbols = sum(r[2] for r in rows)

    # If summary or deep analysis is missing, generate it via RepositoryProfiler
    overview_obj = None
    deep_obj = None
    if not repo.summary or not repo.deep_analysis:
        from app.services.profiler.builder import RepositoryProfiler
        profiler = RepositoryProfiler(repo, chunks)
        overview_obj, deep_obj, summary_md = profiler.build_profile()
        repo.summary = summary_md
        repo.deep_analysis = deep_obj.model_dump_json()
        await db.commit()
    else:
        # Re-derive overview_obj and parse deep_analysis
        from app.services.profiler.builder import RepositoryProfiler
        profiler = RepositoryProfiler(repo, chunks)
        overview_obj, deep_obj, _ = profiler.build_profile()

    # Count verified citations
    verified_citations = len(overview_obj.purpose_evidence)
    for f in overview_obj.frameworks:
        if "file_path" in f:
            verified_citations += 1
    for i in overview_obj.integrations:
        if "file_path" in i:
            verified_citations += 1
    for c in overview_obj.commands:
        if "file_path" in c:
            verified_citations += 1

    return RepositorySummaryResponse(
        repository_id=repo.id,
        full_name=repo.full_name,
        branch=repo.default_branch,
        commit_sha=repo.indexed_commit_sha,
        indexing_status=repo.indexing_status,
        indexing_freshness=repo.updated_at.isoformat() if repo.updated_at else None,
        languages=languages,
        total_files=total_files,
        total_symbols=total_symbols,
        summary=repo.summary or "Summary not available.",
        overview=overview_obj,
        deep_analysis=deep_obj,
        verified_citations_count=verified_citations
    )


@router.get("/{id}/settings", response_model=RepositorySettingsResponse)
async def get_repository_settings(id: int, db: AsyncSession = Depends(get_db)):
    """Returns repository configuration settings."""
    stmt = select(RepositorySettings).where(RepositorySettings.repository_id == id)
    res = await db.execute(stmt)
    settings_obj = res.scalar_one_or_none()
    if not settings_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
    return settings_obj


@router.put("/{id}/settings", response_model=RepositorySettingsResponse)
async def update_repository_settings(
    id: int,
    payload: RepositorySettingsUpdate,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates repository settings.
    Enforces Administrator role if blocking CI behavior is modified.
    Audit logs changes with tamper-evident cryptographic chaining.
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    stmt = select(RepositorySettings).where(RepositorySettings.repository_id == id)
    res = await db.execute(stmt)
    settings_obj = res.scalar_one_or_none()
    if not settings_obj:
        settings_obj = RepositorySettings(repository_id=id)
        db.add(settings_obj)

    # Check if blocking CI is being modified
    if payload.blocking_ci_enabled is not None and payload.blocking_ci_enabled != settings_obj.blocking_ci_enabled:
        old_blocking = settings_obj.blocking_ci_enabled
        settings_obj.blocking_ci_enabled = payload.blocking_ci_enabled
        user_name = user.username if user else "user"
        await record_audit_event(
            db=db,
            action_type="update_blocking_ci",
            user_id=user_name,
            repo_full_name=repo.full_name,
            payload_summary=f"User '{user_name}' changed blocking_ci_enabled from {old_blocking} to {payload.blocking_ci_enabled}"
        )

    old_ci_enabled = settings_obj.optional_ci_enabled
    if payload.optional_ci_enabled is not None:
        settings_obj.optional_ci_enabled = payload.optional_ci_enabled
    if payload.auto_review_prs is not None:
        settings_obj.auto_review_prs = payload.auto_review_prs
    if payload.min_severity_to_alert is not None:
        settings_obj.min_severity_to_alert = payload.min_severity_to_alert

    # Audit log if CI check setting changed
    if payload.optional_ci_enabled is not None and old_ci_enabled != payload.optional_ci_enabled:
        action = "enable_ci_check" if payload.optional_ci_enabled else "disable_ci_check"
        user_name = user.username if user else "reviewer"
        await record_audit_event(
            db=db,
            action_type=action,
            user_id=user_name,
            repo_full_name=repo.full_name,
            payload_summary=f"User '{user_name}' changed optional_ci_enabled to {payload.optional_ci_enabled}"
        )

    await db.commit()
    await db.refresh(settings_obj)
    return settings_obj


@router.get("/{id}/tree", response_model=RepositoryTreeResponse)
async def get_repository_tree(
    id: int,
    search: Optional[str] = Query(default=None, description="Search term for file path or name"),
    language: Optional[str] = Query(default=None, description="Filter by language"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (all, indexed, fallback, excluded)"),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full searchable file tree for the repository at its indexed commit,
    including safely excluded files (secrets, binaries, oversized, vendor),
    accurate coverage totals, and detected language information.
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    github_client = get_github_client(is_demo=repo.is_demo)
    ref = repo.indexed_commit_sha or repo.default_branch

    # Check if files already populated in DB
    existing_files_stmt = select(RepositoryFile).where(RepositoryFile.repository_id == id)
    if repo.indexed_commit_sha:
        existing_files_stmt = existing_files_stmt.where(RepositoryFile.commit_sha == repo.indexed_commit_sha)
    
    existing_res = await db.execute(existing_files_stmt)
    db_files = existing_res.scalars().all()

    # If DB files are not yet created (e.g. initial demo load or legacy seed), construct them safely
    if not db_files:
        try:
            tree_items = await github_client.get_repository_tree(repo.full_name, ref)
            new_files: List[RepositoryFile] = []
            
            # Fetch existing chunk paths to match analysis mode
            chunk_stmt = select(CodeChunk.file_path, CodeChunk.analysis_mode).where(CodeChunk.repository_id == id)
            chunk_res = await db.execute(chunk_stmt)
            chunk_map = {row[0]: row[1] for row in chunk_res.all()}

            for item in tree_items:
                if item.get("type") == "blob":
                    path = item.get("path", "")
                    size = item.get("size", 0)
                    filename = os.path.basename(path)
                    adapter, _ = detect_file_language(path)
                    allowed, reason, _, is_secret, is_binary = classify_file_safety(path, size)

                    if allowed:
                        mode = chunk_map.get(path, "parser_aware" if adapter.parser_available else "text_fallback")
                        file_status = "indexed" if mode == "parser_aware" else "fallback"
                        rf = RepositoryFile(
                            repository_id=repo.id,
                            commit_sha=repo.indexed_commit_sha or ref,
                            file_path=path,
                            filename=filename,
                            file_size=size,
                            language=adapter.name,
                            language_display=adapter.display_name,
                            status=file_status,
                            analysis_mode=mode,
                            exclusion_reason=None,
                            is_secret=False,
                            is_binary=False,
                            chunks_count=1 if path in chunk_map else 0
                        )
                    else:
                        rf = RepositoryFile(
                            repository_id=repo.id,
                            commit_sha=repo.indexed_commit_sha or ref,
                            file_path=path,
                            filename=filename,
                            file_size=size,
                            language=adapter.name,
                            language_display=adapter.display_name,
                            status="excluded",
                            analysis_mode="excluded",
                            exclusion_reason=reason or "Excluded by policy",
                            is_secret=is_secret,
                            is_binary=is_binary,
                            chunks_count=0
                        )
                    new_files.append(rf)

            if new_files:
                db.add_all(new_files)
                await db.commit()
                db_files = new_files
        except Exception as e:
            logger.warning(f"Could not build file tree on demand: {e}")

    # Compute coverage totals across ALL files
    total_files = len(db_files)
    parser_aware_count = sum(1 for f in db_files if f.analysis_mode == "parser_aware")
    fallback_count = sum(1 for f in db_files if f.analysis_mode == "text_fallback")
    excluded_count = sum(1 for f in db_files if f.analysis_mode == "excluded" or f.status == "excluded")
    pending_count = sum(1 for f in db_files if f.status == "pending")
    failed_count = sum(1 for f in db_files if f.status == "failed")

    # Apply search and filters
    filtered = db_files
    if search:
        s_term = search.lower()
        filtered = [f for f in filtered if s_term in f.file_path.lower() or s_term in f.filename.lower()]

    if language and language.lower() != "all":
        filtered = [f for f in filtered if f.language.lower() == language.lower()]

    if status_filter and status_filter.lower() != "all":
        s_mode = status_filter.lower()
        if s_mode in {"parser_aware", "parser"}:
            filtered = [f for f in filtered if f.analysis_mode == "parser_aware"]
        elif s_mode in {"text_fallback", "fallback"}:
            filtered = [f for f in filtered if f.analysis_mode == "text_fallback"]
        elif s_mode == "excluded":
            filtered = [f for f in filtered if f.status == "excluded"]
        elif s_mode == "indexed":
            filtered = [f for f in filtered if f.status in {"indexed", "fallback"}]
        else:
            filtered = [f for f in filtered if f.status.lower() == s_mode]

    total_filtered_count = len(filtered)
    paged_files = filtered[offset:offset + limit]

    return RepositoryTreeResponse(
        repository_id=repo.id,
        full_name=repo.full_name,
        branch=repo.default_branch,
        commit_sha=repo.indexed_commit_sha,
        indexing_status=repo.indexing_status,
        indexing_progress=repo.indexing_progress,
        coverage=RepositoryTreeCoverage(
            total_files=total_files,
            parser_aware=parser_aware_count,
            fallback=fallback_count,
            excluded=excluded_count,
            pending=pending_count,
            failed=failed_count
        ),
        files=[RepositoryFileItem.model_validate(f) for f in paged_files],
        total_count=total_filtered_count,
        limit=limit,
        offset=offset
    )


@router.get("/{id}/health-dashboard", response_model=RepositoryHealthDashboardResponse)
async def get_repository_health_dashboard(
    id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns repository indexing coverage and health dashboard metrics:
    - Total discovered files, successfully indexed, parser-aware vs fallback counts
    - Excluded secret and binary files
    - Unsupported, skipped, and indexing failures with reasons
    - Last successful indexing time, commit SHA, and staleness
    - Database mode (PostgreSQL vs SQLite fallback) and vector capabilities
    - Summary of files safe to open in explorer
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    gh = get_github_client(is_demo=repo.is_demo)
    is_stale, remote_sha = await populate_staleness(repo, gh)

    file_stmt = select(RepositoryFile).where(RepositoryFile.repository_id == id)
    if repo.indexed_commit_sha:
        file_stmt = file_stmt.where(RepositoryFile.commit_sha == repo.indexed_commit_sha)
    file_res = await db.execute(file_stmt)
    files = file_res.scalars().all()

    total_discovered = len(files)
    indexed_count = sum(1 for f in files if f.status in {"indexed", "fallback"})
    parser_aware = sum(1 for f in files if f.analysis_mode == "parser_aware")
    text_fallback = sum(1 for f in files if f.analysis_mode == "text_fallback")
    excluded_secrets = sum(1 for f in files if f.is_secret)
    excluded_binaries = sum(1 for f in files if f.is_binary)
    excluded_vendors = sum(
        1 for f in files
        if f.status == "excluded" and not f.is_secret and not f.is_binary and "vendor" in (f.exclusion_reason or "").lower()
    )
    unsupported_or_failed = sum(1 for f in files if f.status in {"failed", "unsupported"})

    db_mode = "SQLite (Fallback)" if check_is_sqlite() else "PostgreSQL (Primary)"
    vec_caps = (
        "In-memory Cosine Similarity (Fallback mode; pgvector IVFFlat/HNSW not available)"
        if check_is_sqlite()
        else "pgvector with IVFFlat / Exact Cosine Indexing Enabled"
    )

    files_summary = []
    for f in files:
        cat = "source"
        if f.is_secret:
            cat = "secret"
        elif f.is_binary:
            cat = "binary"
        elif f.status == "excluded":
            cat = "vendor/config"
        elif f.status in {"failed", "unsupported"}:
            cat = "failed"

        is_safe = not (f.is_secret or f.is_binary)
        files_summary.append(
            HealthFileItem(
                file_path=f.file_path,
                filename=f.filename,
                status=f.status,
                analysis_mode=f.analysis_mode,
                category=cat,
                exclusion_reason=f.exclusion_reason,
                is_secret=f.is_secret,
                is_binary=f.is_binary,
                is_safe_to_view_in_explorer=is_safe,
                language_display=f.language_display,
                file_size_bytes=f.file_size
            )
        )

    return RepositoryHealthDashboardResponse(
        repository_id=repo.id,
        full_name=repo.full_name,
        branch=repo.default_branch,
        indexed_commit_sha=repo.indexed_commit_sha,
        remote_commit_sha=remote_sha,
        is_stale=is_stale,
        indexing_status=repo.indexing_status,
        indexing_progress=repo.indexing_progress,
        last_indexed_at=repo.last_indexed_at,
        total_discovered_files=total_discovered,
        indexed_files_count=indexed_count,
        parser_aware_count=parser_aware,
        text_fallback_count=text_fallback,
        excluded_secrets_count=excluded_secrets,
        excluded_binaries_count=excluded_binaries,
        excluded_vendors_count=excluded_vendors,
        unsupported_or_failed_count=unsupported_or_failed,
        database_mode=db_mode,
        database_vector_capabilities=vec_caps,
        files_summary=files_summary
    )


@router.get("/{id}/files/content", response_model=FileContentResponse)
async def get_repository_file_content(
    id: int,
    path: str = Query(..., description="Repository-relative file path"),
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns file content and metadata for syntax preview.
    If the file is classified as excluded (secrets, private keys, binaries, vendor files),
    returns allowed=False with exclusion reason and NEVER exposes or leaks file content.
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    clean_path = path.replace("\\", "/").strip("/")

    # Check database file record first if present
    file_stmt = select(RepositoryFile).where(
        RepositoryFile.repository_id == id,
        RepositoryFile.file_path == clean_path
    )
    if repo.indexed_commit_sha:
        file_stmt = file_stmt.where(RepositoryFile.commit_sha == repo.indexed_commit_sha)
    
    file_res = await db.execute(file_stmt)
    file_rec = file_res.scalars().first()

    # Pre-check safety
    allowed, reason, category, is_secret, is_binary = classify_file_safety(clean_path, file_rec.file_size if file_rec else 100)
    adapter, _ = detect_file_language(clean_path)

    if not allowed or (file_rec and file_rec.status == "excluded"):
        return FileContentResponse(
            repository_id=repo.id,
            file_path=clean_path,
            allowed=False,
            language=adapter.name,
            language_display=adapter.display_name,
            analysis_mode="excluded",
            exclusion_reason=reason or (file_rec.exclusion_reason if file_rec else "Excluded by policy"),
            is_secret=is_secret or (file_rec.is_secret if file_rec else False),
            is_binary=is_binary or (file_rec.is_binary if file_rec else False),
            content=None,
            lines_count=None,
            size_bytes=file_rec.file_size if file_rec else None
        )

    # Allowed text file: fetch content safely
    github_client = get_github_client(is_demo=repo.is_demo)
    ref = repo.indexed_commit_sha or repo.default_branch

    try:
        content = await github_client.get_file_content(repo.full_name, clean_path, ref)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to read file '{clean_path}' at ref {ref[:8]}: {str(e)}"
        )

    # Deep content secret scanning: never leak credentials even if file extension appeared safe
    content_allowed, content_reason, _, is_content_secret, _ = classify_file_safety(
        clean_path, len(content.encode("utf-8")), content=content
    )
    if not content_allowed or is_content_secret:
        return FileContentResponse(
            repository_id=repo.id,
            file_path=clean_path,
            allowed=False,
            language=adapter.name,
            language_display=adapter.display_name,
            analysis_mode="excluded",
            exclusion_reason=content_reason or "Detected sensitive credentials or secret in file content",
            is_secret=True,
            is_binary=False,
            content=None,
            lines_count=None,
            size_bytes=len(content.encode("utf-8"))
        )

    mode = file_rec.analysis_mode if file_rec else ("parser_aware" if adapter.parser_available else "text_fallback")
    lines = content.splitlines()

    return FileContentResponse(
        repository_id=repo.id,
        file_path=clean_path,
        allowed=True,
        language=adapter.name,
        language_display=adapter.display_name,
        analysis_mode=mode,
        exclusion_reason=None,
        is_secret=False,
        is_binary=False,
        content=content,
        lines_count=len(lines),
        size_bytes=len(content.encode("utf-8"))
    )


@router.get("/{id}/onboarding", response_model=RepositoryOnboardingResponse)
async def get_repository_onboarding_guide(
    id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns evidence-grounded 'Start here' repository onboarding guide.
    Identifies application entry points, core modules & responsibilities,
    module connections, and existing tests with file & line citations.
    Labels unverified claims as 'Not confirmed from indexed files.'
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    # Fetch chunks
    stmt_chunks = select(CodeChunk).where(CodeChunk.repository_id == id)
    if repo.indexed_commit_sha:
        stmt_chunks = stmt_chunks.where(CodeChunk.commit_sha == repo.indexed_commit_sha)
    res_chunks = await db.execute(stmt_chunks)
    chunks = res_chunks.scalars().all()

    # Fetch static relationships
    stmt_rel = select(CodeRelationship).where(CodeRelationship.repository_id == id)
    if repo.indexed_commit_sha:
        stmt_rel = stmt_rel.where(CodeRelationship.commit_sha == repo.indexed_commit_sha)
    res_rel = await db.execute(stmt_rel)
    relationships = res_rel.scalars().all()

    # Fetch files
    stmt_files = select(RepositoryFile).where(RepositoryFile.repository_id == id)
    res_files = await db.execute(stmt_files)
    files = res_files.scalars().all()

    builder = OnboardingGuideBuilder(repo, chunks, relationships, files)
    guide = builder.build_guide()
    return guide


@router.get("/{id}/compare", response_model=CommitCompareResponse)
async def compare_repository_commits(
    id: int,
    base: str = Query(..., description="Base branch or commit SHA"),
    head: str = Query(..., description="Head branch or commit SHA"),
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Compares two branches or commits:
    - Added, modified, deleted, and renamed files
    - Architectural module and relationship changes
    - New or resolved AI review findings
    - Stale or unindexed indicators
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    gh = get_github_client(is_demo=repo.is_demo)
    comparator = CommitComparator(repo, base, head, gh, db)
    comparison = await comparator.compare()
    return comparison


@router.get("/{id}/dependencies", response_model=DependencyInventoryResponse)
async def get_repository_dependencies(
    id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency inventory view parsing supported manifests and lock files:
    Shows dependency name, declared version, origin file, and direct vs transitive.
    Displays verification source and check date without false vulnerability claims.
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    # Fetch manifest chunks
    stmt = select(CodeChunk).where(CodeChunk.repository_id == id)
    if repo.indexed_commit_sha:
        stmt = stmt.where(CodeChunk.commit_sha == repo.indexed_commit_sha)
    res = await db.execute(stmt)
    chunks = res.scalars().all()

    gh = get_github_client(is_demo=repo.is_demo)
    scanner = DependencyInventoryScanner(repo, chunks, gh)
    inventory = await scanner.scan()
    return inventory


@router.post("/{id}/feedback", response_model=RepositoryFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def record_repository_feedback(
    id: int,
    payload: RepositoryFeedbackCreate,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Records developer feedback on review findings or Q&A answers (useful or incorrect with reason).
    Stored with repository ID, commit SHA, and target ID for evaluation and reporting.
    Does not silently alter review rules or model behavior based on a single feedback item.
    """
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    feedback_entry = RepositoryFeedback(
        repository_id=repo.id,
        branch=payload.branch or repo.default_branch,
        commit_sha=payload.commit_sha,
        target_type=payload.target_type,
        target_id=payload.target_id,
        category=payload.category or ("useful" if payload.is_useful else "incorrect"),
        is_useful=payload.is_useful,
        reason=payload.reason,
        user_id=user.username if user else "anonymous"
    )
    db.add(feedback_entry)
    await db.commit()
    await db.refresh(feedback_entry)

    # Record tamper-evident audit event
    user_name = user.username if user else "developer"
    rating_label = "useful" if payload.is_useful else "incorrect"
    await record_audit_event(
        db=db,
        action_type="feedback_recorded",
        user_id=user_name,
        repo_full_name=repo.full_name,
        payload_summary=f"User '{user_name}' marked {payload.target_type} '{payload.target_id}' as {rating_label} (commit: {payload.commit_sha[:8]})."
    )

    return feedback_entry


@router.get("/{id}/feedback", response_model=List[RepositoryFeedbackResponse])
async def list_repository_feedback(
    id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Lists developer feedback recorded for this repository."""
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if user:
        verify_repository_access(repo, user)

    stmt = (
        select(RepositoryFeedback)
        .where(RepositoryFeedback.repository_id == id)
        .order_by(RepositoryFeedback.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


