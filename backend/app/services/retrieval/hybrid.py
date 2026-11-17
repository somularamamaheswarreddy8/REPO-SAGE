import math
import logging
import re
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.code_chunk import CodeChunk
from app.services.ai.base import BaseEmbeddingProvider
from app.services.parser.filters import classify_file_safety
from app.core.config import settings

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def deduplicate_chunks(chunks: List[CodeChunk]) -> List[CodeChunk]:
    """
    Deduplicates code chunks by content hash and overlapping line ranges
    within the same source file.
    """
    seen_hashes: Set[str] = set()
    deduped: List[CodeChunk] = []

    for c in chunks:
        if c.content_hash in seen_hashes:
            continue
        seen_hashes.add(c.content_hash)

        # Skip chunks that are completely enclosed within an already-selected chunk from the same file
        is_subsumed = False
        for existing in deduped:
            if existing.file_path == c.file_path:
                if existing.start_line <= c.start_line and existing.end_line >= c.end_line:
                    is_subsumed = True
                    break
        if not is_subsumed:
            deduped.append(c)

    return deduped


class HybridRetriever:
    """
    Secure Hybrid Code Retriever with repository and commit SHA isolation.
    Combines semantic vector search with keyword/lexical ranking,
    filters secrets and binaries, deduplicates chunks, and enforces relevance cutoffs.
    """

    def __init__(self, db: AsyncSession, embedding_provider: BaseEmbeddingProvider):
        self.db = db
        self.embedding_provider = embedding_provider

    async def retrieve(
        self,
        repository_id: int,
        query: str,
        commit_sha: Optional[str] = None,
        top_k: int = 5,
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        # 1. Fetch chunks strictly isolated to this repository ID
        base_query = select(CodeChunk).where(CodeChunk.repository_id == repository_id)
        if commit_sha and commit_sha != "unindexed":
            base_query = base_query.where(CodeChunk.commit_sha == commit_sha)

        result = await self.db.execute(base_query)
        all_chunks = result.scalars().all()

        if not all_chunks:
            return []

        # Strict isolation check: enforce that every chunk belongs ONLY to the requested repository
        all_chunks = [c for c in all_chunks if c.repository_id == repository_id]

        # 2. Exclude secrets, credentials, and binary files
        safe_chunks: List[CodeChunk] = []
        for c in all_chunks:
            size_bytes = len(c.content.encode("utf-8")) if c.content else 0
            allowed, _, _, is_sec, is_bin = classify_file_safety(c.file_path, size_bytes)
            if allowed and not is_sec and not is_bin:
                safe_chunks.append(c)

        if not safe_chunks:
            return []

        # 3. Deduplicate overlapping chunks
        deduped_chunks = deduplicate_chunks(safe_chunks)

        # 4. Keyword / Lexical Scoring
        STOP_WORDS = {
            "what", "where", "how", "when", "why", "who", "whom", "which", "whose",
            "does", "did", "do", "done", "the", "and", "or", "for", "with", "from",
            "this", "that", "these", "those", "show", "explain", "tell", "are", "is",
            "was", "were", "be", "been", "being", "have", "has", "had", "any", "all",
            "can", "could", "would", "should", "code", "file", "files", "function",
            "class", "method", "module", "please", "about", "in", "on", "at", "by",
            "to", "of", "an", "a", "as", "it", "its", "if", "so", "than", "then",
            "there", "here", "their", "them", "they", "we", "us", "our", "you", "your",
            "my", "me", "into", "also", "just", "like", "up", "out", "no", "not"
        }
        tokens = re.findall(r"[a-zA-Z0-9_\-\.]+", query.lower())
        keywords = [t for t in tokens if len(t) >= 2 and t not in STOP_WORDS]

        import os
        keyword_scores: Dict[int, float] = {}
        max_kw_score = 0.0

        for chunk in deduped_chunks:
            score = 0.0
            content_lower = chunk.content.lower()
            file_lower = chunk.file_path.lower()
            file_basename = os.path.basename(file_lower)
            file_stem = os.path.splitext(file_basename)[0]
            symbol_lower = (chunk.symbol_name or "").lower()

            for kw in keywords:
                # File path and file name matching gets the highest priority
                if kw == file_lower or kw == file_basename:
                    score += 50.0
                elif kw == file_stem:
                    score += 35.0
                elif kw in file_lower:
                    score += 15.0

                # Symbol matching
                if symbol_lower:
                    if symbol_lower == kw:
                        score += 40.0
                    elif kw in symbol_lower:
                        score += 20.0

                # Content occurrences
                count = content_lower.count(kw)
                if count > 0:
                    score += min(15.0, count * 2.0)

            keyword_scores[chunk.id] = score
            if score > max_kw_score:
                max_kw_score = score

        # 5. Vector Semantic Scoring
        query_vector = await self.embedding_provider.get_embedding(query)
        vector_scores: Dict[int, float] = {}

        for chunk in deduped_chunks:
            if chunk.embedding:
                sim = cosine_similarity(query_vector, chunk.embedding)
                vector_scores[chunk.id] = max(0.0, sim)
            else:
                vector_scores[chunk.id] = 0.0

        # 6. Strict Relevance Filtering:
        # If the query contains meaningful keywords, require at least one keyword match
        # OR a strong semantic vector similarity (>= 0.40).
        relevant_candidates: List[CodeChunk] = []
        for chunk in deduped_chunks:
            kw_score = keyword_scores.get(chunk.id, 0.0)
            vec_score = vector_scores.get(chunk.id, 0.0)

            if keywords:
                if kw_score > 0.0 or vec_score >= 0.40:
                    relevant_candidates.append(chunk)
            else:
                if vec_score >= 0.25:
                    relevant_candidates.append(chunk)

        if not relevant_candidates:
            return []

        # 7. Reciprocal Rank Fusion (RRF) & Combined Ranking
        # If strong keyword signals were detected, bias heavily towards keyword ranking
        eff_kw_weight = 0.8 if max_kw_score >= 20.0 else keyword_weight
        eff_vec_weight = 0.2 if max_kw_score >= 20.0 else vector_weight

        k_const = 60
        fused_scores: Dict[int, float] = {}

        vector_ranked = sorted(relevant_candidates, key=lambda c: vector_scores.get(c.id, 0.0), reverse=True)
        keyword_ranked = sorted(relevant_candidates, key=lambda c: keyword_scores.get(c.id, 0.0), reverse=True)

        for rank, chunk in enumerate(vector_ranked):
            v_rank = rank + 1
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (eff_vec_weight / (k_const + v_rank))

        for rank, chunk in enumerate(keyword_ranked):
            kw_rank = rank + 1
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (eff_kw_weight / (k_const + kw_rank))

        sorted_chunks = sorted(relevant_candidates, key=lambda c: fused_scores.get(c.id, 0.0), reverse=True)
        top_chunks = sorted_chunks[:top_k]

        return [
            {
                "chunk_id": c.id,
                "file_path": c.file_path,
                "language": c.language,
                "symbol_name": c.symbol_name,
                "symbol_type": c.symbol_type,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "content": c.content,
                "commit_sha": c.commit_sha,
                "score": fused_scores.get(c.id, 0.0)
            }
            for c in top_chunks
        ]
