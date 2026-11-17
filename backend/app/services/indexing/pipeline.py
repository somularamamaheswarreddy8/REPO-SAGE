import logging
import datetime
import os
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.code_chunk import CodeChunk
from app.models.relationship import CodeRelationship
from app.services.github.factory import get_github_client
from app.services.parser.filters import classify_file_safety
from app.services.parser.chunker import chunk_file
from app.services.languages.detect import detect_file_language
from app.services.ai.factory import get_embedding_provider, get_llm_provider
from app.core.config import settings

logger = logging.getLogger(__name__)


async def run_indexing_pipeline(
    db: AsyncSession,
    repository_id: int,
    branch: Optional[str] = None,
    force_full_reindex: bool = False
) -> Dict[str, Any]:
    """
    Executes repository code indexing.
    Supports broad language support, parser-aware chunking, text fallback chunking,
    safe file exclusion tracking (secrets, binaries, vendors), and tree generation.
    """
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise ValueError(f"Repository with ID {repository_id} not found")

    target_branch = branch or repo.default_branch
    github_client = get_github_client(is_demo=repo.is_demo)
    embedding_provider = get_embedding_provider()
    llm_provider = get_llm_provider()

    try:
        # Mark status as running
        repo.indexing_status = "running"
        repo.indexing_progress = 5.0
        repo.indexing_error = None
        await db.commit()

        # Fetch latest commit SHA
        commit_sha = await github_client.get_latest_commit_sha(repo.full_name, target_branch)
        logger.info(f"Starting indexing for {repo.full_name} at commit {commit_sha[:8]}")

        # Idempotency check: if already indexed at this commit and not forced, return immediately
        if not force_full_reindex and repo.indexing_status == "completed" and repo.indexed_commit_sha == commit_sha:
            logger.info(f"Repository {repo.full_name} already indexed at commit {commit_sha[:8]}. Idempotent skip.")
            if not repo.last_indexed_at:
                repo.last_indexed_at = datetime.datetime.utcnow()
                await db.commit()
            return {
                "status": "completed",
                "commit_sha": commit_sha,
                "is_incremental": True,
                "message": "Repository is up to date."
            }

        # Fetch repository tree
        tree = await github_client.get_repository_tree(repo.full_name, commit_sha)
        repo.indexing_progress = 15.0
        await db.commit()

        # Classify all tree items into indexable files and safely excluded files
        all_repo_files: List[RepositoryFile] = []
        files_to_index: List[Dict[str, Any]] = []

        for item in tree:
            if item.get("type") == "blob":
                path = item.get("path", "")
                size = item.get("size", 0)
                filename = os.path.basename(path)
                
                adapter, _ = detect_file_language(path)
                allowed, reason, category, is_secret, is_binary = classify_file_safety(path, size)

                if allowed:
                    files_to_index.append(item)
                else:
                    # Record excluded file metadata without exposing contents
                    all_repo_files.append(
                        RepositoryFile(
                            repository_id=repo.id,
                            commit_sha=commit_sha,
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
                    )

        # Enforce max index files limit
        if len(files_to_index) > settings.MAX_INDEX_FILES:
            overflow = files_to_index[settings.MAX_INDEX_FILES:]
            files_to_index = files_to_index[:settings.MAX_INDEX_FILES]
            for item in overflow:
                path = item.get("path", "")
                size = item.get("size", 0)
                filename = os.path.basename(path)
                adapter, _ = detect_file_language(path)
                all_repo_files.append(
                    RepositoryFile(
                        repository_id=repo.id,
                        commit_sha=commit_sha,
                        file_path=path,
                        filename=filename,
                        file_size=size,
                        language=adapter.name,
                        language_display=adapter.display_name,
                        status="excluded",
                        analysis_mode="excluded",
                        exclusion_reason=f"Exceeded max indexed files limit ({settings.MAX_INDEX_FILES})",
                        is_secret=False,
                        is_binary=False,
                        chunks_count=0
                    )
                )

        total_files = len(files_to_index)
        logger.info(f"Found {total_files} indexable files in {repo.full_name} ({len(all_repo_files)} excluded)")

        # Check existing chunks for incremental indexing
        existing_chunks_stmt = select(CodeChunk).where(
            CodeChunk.repository_id == repo.id
        )
        existing_res = await db.execute(existing_chunks_stmt)
        existing_chunks = existing_res.scalars().all()
        existing_hashes = {c.content_hash: c for c in existing_chunks}

        new_chunks: List[CodeChunk] = []
        new_relationships: List[CodeRelationship] = []

        for idx, file_item in enumerate(files_to_index):
            file_path = file_item["path"]
            file_size = file_item.get("size", 0)
            filename = os.path.basename(file_path)

            try:
                content = await github_client.get_file_content(repo.full_name, file_path, commit_sha)
            except Exception as e:
                logger.warning(f"Failed to fetch content for {file_path}: {e}")
                adapter, _ = detect_file_language(file_path)
                all_repo_files.append(
                    RepositoryFile(
                        repository_id=repo.id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        filename=filename,
                        file_size=file_size,
                        language=adapter.name,
                        language_display=adapter.display_name,
                        status="failed",
                        analysis_mode="failed",
                        exclusion_reason=f"Failed to fetch content: {str(e)}",
                        is_secret=False,
                        is_binary=False,
                        chunks_count=0
                    )
                )
                continue

            # Deep secret scanning on fetched content
            content_allowed, content_reason, _, is_sec, _ = classify_file_safety(file_path, file_size, content=content)
            if not content_allowed:
                logger.info(f"File {file_path} safely excluded due to detected content secrets.")
                adapter, _ = detect_file_language(file_path, content)
                all_repo_files.append(
                    RepositoryFile(
                        repository_id=repo.id,
                        commit_sha=commit_sha,
                        file_path=file_path,
                        filename=filename,
                        file_size=file_size,
                        language=adapter.name,
                        language_display=adapter.display_name,
                        status="excluded",
                        analysis_mode="excluded",
                        exclusion_reason=content_reason or "Contained sensitive credentials",
                        is_secret=is_sec,
                        is_binary=False,
                        chunks_count=0
                    )
                )
                continue

            parsed_chunks, parsed_rels = chunk_file(content, file_path)
            adapter, _ = detect_file_language(file_path, content)

            file_mode = "text_fallback"
            if any(c.analysis_mode == "parser_aware" for c in parsed_chunks):
                file_mode = "parser_aware"

            file_status = "indexed" if file_mode == "parser_aware" else "fallback"

            all_repo_files.append(
                RepositoryFile(
                    repository_id=repo.id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    filename=filename,
                    file_size=file_size,
                    language=adapter.name,
                    language_display=adapter.display_name,
                    status=file_status,
                    analysis_mode=file_mode,
                    exclusion_reason=None,
                    is_secret=False,
                    is_binary=False,
                    chunks_count=len(parsed_chunks)
                )
            )

            for chunk_data in parsed_chunks:
                chunk_obj = CodeChunk(
                    repository_id=repo.id,
                    commit_sha=commit_sha,
                    file_path=chunk_data.file_path,
                    language=chunk_data.language,
                    analysis_mode=chunk_data.analysis_mode,
                    symbol_name=chunk_data.symbol_name,
                    symbol_type=chunk_data.symbol_type,
                    start_line=chunk_data.start_line,
                    end_line=chunk_data.end_line,
                    content=chunk_data.content,
                    content_hash=chunk_data.content_hash,
                    embedding=existing_hashes[chunk_data.content_hash].embedding if chunk_data.content_hash in existing_hashes else None
                )
                new_chunks.append(chunk_obj)

            for rel in parsed_rels:
                rel_obj = CodeRelationship(
                    repository_id=repo.id,
                    commit_sha=commit_sha,
                    source_file=file_path,
                    target_file=rel.target_file,
                    relationship_type=rel.relationship_type,
                    source_symbol=rel.source_symbol,
                    target_symbol=rel.target_symbol,
                    line_number=rel.line_number,
                    evidence_snippet=rel.evidence_snippet
                )
                new_relationships.append(rel_obj)

            # Update progress
            progress = 15.0 + (idx + 1) / max(1, total_files) * 60.0
            repo.indexing_progress = round(progress, 1)
            if idx % 10 == 0:
                await db.commit()

        # Compute embeddings for new chunks that lack embeddings
        chunks_needing_embeddings = [c for c in new_chunks if c.embedding is None]
        if chunks_needing_embeddings:
            batch_size = 20
            for b in range(0, len(chunks_needing_embeddings), batch_size):
                batch = chunks_needing_embeddings[b:b + batch_size]
                texts = [f"{c.file_path} {c.symbol_name or ''}\n{c.content}" for c in batch]
                embeddings = await embedding_provider.get_embeddings(texts)
                for chunk_item, emb in zip(batch, embeddings):
                    chunk_item.embedding = emb

        # Atomic swap: Delete old chunks, files, and relationships for this repository
        await db.execute(delete(CodeChunk).where(CodeChunk.repository_id == repo.id))
        await db.execute(delete(CodeRelationship).where(CodeRelationship.repository_id == repo.id))
        await db.execute(delete(RepositoryFile).where(RepositoryFile.repository_id == repo.id))

        db.add_all(all_repo_files)
        db.add_all(new_chunks)
        db.add_all(new_relationships)

        # Build evidence-grounded repository profile and deep analysis from indexed chunks
        repo.indexing_progress = 90.0
        await db.commit()
        
        try:
            from app.services.profiler.builder import RepositoryProfiler
            profiler = RepositoryProfiler(repo, new_chunks)
            overview, deep, summary_md = profiler.build_profile()
            repo.summary = summary_md
            repo.deep_analysis = deep.model_dump_json()
        except Exception as e:
            logger.warning(f"Could not build profile: {e}")
            repo.summary = f"Repository {repo.full_name} indexed at commit {commit_sha[:8]}."
            repo.deep_analysis = None

        # Mark completed
        repo.indexed_commit_sha = commit_sha
        repo.indexing_status = "completed"
        repo.indexing_progress = 100.0
        repo.indexing_error = None
        repo.last_indexed_at = datetime.datetime.utcnow()
        repo.updated_at = datetime.datetime.utcnow()
        await db.commit()

        logger.info(
            f"Indexing completed for {repo.full_name}. "
            f"Total files: {len(all_repo_files)}, chunks: {len(new_chunks)}, relationships: {len(new_relationships)}"
        )
        return {
            "status": "completed",
            "commit_sha": commit_sha,
            "total_files": len(all_repo_files),
            "total_chunks": len(new_chunks),
            "total_relationships": len(new_relationships)
        }

    except Exception as exc:
        logger.error(f"Indexing failed for repository {repo.full_name}: {exc}", exc_info=True)
        repo.indexing_status = "failed"
        repo.indexing_error = str(exc)
        repo.indexing_progress = 0.0
        await db.commit()
        raise
