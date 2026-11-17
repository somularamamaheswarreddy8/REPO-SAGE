from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AnalysisMode(str, Enum):
    PARSER_AWARE = "parser_aware"
    TEXT_FALLBACK = "text_fallback"
    EXCLUDED = "excluded"
    PENDING = "pending"
    FAILED = "failed"


class LanguageCategory(str, Enum):
    PROGRAMMING = "programming"
    MARKUP = "markup"
    CONFIG = "config"
    DATA = "data"
    PROSE = "prose"
    UNKNOWN = "unknown"


class LanguageAdapter(BaseModel):
    name: str = Field(..., description="Canonical lowercase language identifier")
    display_name: str = Field(..., description="Human-readable language display name")
    extensions: List[str] = Field(default_factory=list, description="Associated file extensions including dot (e.g. .py)")
    filenames: List[str] = Field(default_factory=list, description="Specific matching filenames (e.g. Dockerfile, Makefile)")
    aliases: List[str] = Field(default_factory=list, description="Alternative names or aliases")
    category: LanguageCategory = Field(default=LanguageCategory.PROGRAMMING)
    parser_available: bool = Field(default=False, description="True if a maintained structural symbol parser is available")
    chunking_strategy: str = Field(default="line_window", description="Strategy: ast, symbol_regex, or line_window")
    doc_link: Optional[str] = None
