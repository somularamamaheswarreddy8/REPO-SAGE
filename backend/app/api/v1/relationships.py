from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.repository import Repository
from app.models.relationship import CodeRelationship
from app.schemas.relationship import (
    CodeRelationshipResponse,
    RelationshipGraphResponse,
    Node,
    Edge
)

router = APIRouter(prefix="/repositories/{id}/relationships", tags=["Code Relationships"])


@router.get("", response_model=List[CodeRelationshipResponse])
async def list_relationships(id: int, db: AsyncSession = Depends(get_db)):
    """Lists code relationships (imports, calls, inheritance) extracted from repository code."""
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    stmt = select(CodeRelationship).where(CodeRelationship.repository_id == id).limit(200)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/graph", response_model=RelationshipGraphResponse)
async def get_relationship_graph(id: int, db: AsyncSession = Depends(get_db)):
    """Returns nodes and edges representing code module and symbol dependencies."""
    repo = await db.get(Repository, id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    stmt = select(CodeRelationship).where(CodeRelationship.repository_id == id).limit(150)
    res = await db.execute(stmt)
    relationships = res.scalars().all()

    nodes_dict = {}
    edges = []

    for r in relationships:
        # Source node
        src_id = f"file:{r.source_file}"
        if src_id not in nodes_dict:
            nodes_dict[src_id] = Node(
                id=src_id,
                label=r.source_file,
                file_path=r.source_file,
                type="module"
            )

        # Target node
        tgt_label = r.target_file or r.target_symbol
        tgt_id = f"target:{tgt_label}"
        if tgt_id not in nodes_dict:
            nodes_dict[tgt_id] = Node(
                id=tgt_id,
                label=tgt_label,
                file_path=r.target_file or r.source_file,
                type="symbol" if not r.target_file else "module"
            )

        edges.append(
            Edge(
                source=src_id,
                target=tgt_id,
                type=r.relationship_type,
                line_number=r.line_number,
                evidence=r.evidence_snippet
            )
        )

    return RelationshipGraphResponse(
        repository_id=repo.id,
        commit_sha=repo.indexed_commit_sha,
        nodes=list(nodes_dict.values()),
        edges=edges
    )
