from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


class CodeRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_file: str
    target_file: Optional[str]
    relationship_type: str
    source_symbol: str
    target_symbol: str
    line_number: int
    evidence_snippet: str
    commit_sha: str
    created_at: datetime


class Node(BaseModel):
    id: str
    label: str
    file_path: str
    type: str  # module, class, function


class Edge(BaseModel):
    source: str
    target: str
    type: str  # imports, calls, inherits
    line_number: int
    evidence: str


class RelationshipGraphResponse(BaseModel):
    repository_id: int
    commit_sha: Optional[str]
    nodes: List[Node]
    edges: List[Edge]
