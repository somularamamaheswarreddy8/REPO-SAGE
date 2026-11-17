from pydantic import BaseModel, Field
from typing import List, Optional


class EvidenceCitation(BaseModel):
    file_path: str = Field(..., description="Repository-relative file path")
    start_line: int = Field(..., description="1-indexed starting line")
    end_line: int = Field(..., description="1-indexed ending line")
    symbol_name: Optional[str] = Field(default=None, description="Enclosing function or class name")
    snippet: str = Field(..., description="Code snippet evidence")
    commit_sha: str = Field(..., description="Indexed commit SHA of this evidence")
    relevance_reason: Optional[str] = Field(default=None, description="Why this source snippet was considered relevant")


class CodeQuestionRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="Question about the repository code")
    max_citations: int = Field(default=5, ge=1, le=10, description="Maximum number of evidence citations")


class CodeQuestionResponse(BaseModel):
    repository_id: int
    query: str
    answer: str = Field(..., description="Evidence-grounded answer or explanation")
    supported_by_evidence: bool = Field(
        ...,
        description="False if retrieved code does not contain sufficient evidence to answer truthfully"
    )
    commit_sha: Optional[str] = Field(None, description="Indexed commit SHA used for context")
    citations: List[EvidenceCitation] = Field(default_factory=list, description="Grounding source citations")
    clarification_prompt: Optional[str] = Field(None, description="Short clarifying question if question was ambiguous")
