import hashlib
import os
from typing import List, Dict, Any, Tuple
from app.services.parser.ast_visitor import parse_python_ast, parse_js_ts_symbols, ParsedRelationship
from app.services.languages.detect import detect_file_language
from app.services.languages.symbol_parsers import extract_regex_symbols


class CodeChunkData:
    def __init__(
        self,
        file_path: str,
        language: str,
        symbol_name: str | None,
        symbol_type: str | None,
        start_line: int,
        end_line: int,
        content: str,
        content_hash: str,
        analysis_mode: str = "text_fallback",
        language_display: str = ""
    ):
        self.file_path = file_path
        self.language = language
        self.symbol_name = symbol_name
        self.symbol_type = symbol_type
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.content_hash = content_hash
        self.analysis_mode = analysis_mode
        self.language_display = language_display or language.capitalize()


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def detect_language(file_path: str) -> str:
    """Helper preserving compatibility with existing callers and tests."""
    adapter, _ = detect_file_language(file_path)
    return adapter.name


def line_based_fallback_chunks(
    code: str,
    file_path: str,
    language: str,
    language_display: str = "",
    chunk_size: int = 50,
    overlap: int = 10
) -> List[CodeChunkData]:
    """
    Sliding window line-based fallback chunker.
    Preserves exact 1-indexed start_line and end_line and original file path.
    Used for languages without dedicated structural parsers or when parsing fails.
    """
    lines = code.splitlines(keepends=True)
    if not lines:
        return []

    chunks: List[CodeChunkData] = []
    total_lines = len(lines)
    step = max(1, chunk_size - overlap)

    for i in range(0, total_lines, step):
        start_line = i + 1
        end_line = min(total_lines, i + chunk_size)
        chunk_lines = lines[i:end_line]
        chunk_content = "".join(chunk_lines)

        chunks.append(
            CodeChunkData(
                file_path=file_path,
                language=language,
                symbol_name=None,
                symbol_type="block",
                start_line=start_line,
                end_line=end_line,
                content=chunk_content,
                content_hash=compute_hash(chunk_content),
                analysis_mode="text_fallback",
                language_display=language_display or language.capitalize()
            )
        )
        if end_line == total_lines:
            break

    return chunks


def chunk_file(code: str, file_path: str) -> Tuple[List[CodeChunkData], List[ParsedRelationship]]:
    """
    Parses a source file into semantic AST-aware code chunks and relationships.
    Uses parser-aware chunks with symbol names and line ranges when a compatible parser is available.
    For languages without a dedicated parser, uses a generic text/code chunker that preserves
    the original file path and exact line ranges. Never silently skips readable source files.
    """
    adapter, initial_mode = detect_file_language(file_path, code)
    language = adapter.name
    language_display = adapter.display_name

    chunks: List[CodeChunkData] = []
    relationships: List[ParsedRelationship] = []

    if language == "python":
        ast_result = parse_python_ast(code, file_path)
        symbols = ast_result.get("symbols", [])
        relationships = ast_result.get("relationships", [])

        if symbols:
            for sym in symbols:
                chunks.append(
                    CodeChunkData(
                        file_path=file_path,
                        language=language,
                        symbol_name=sym.name,
                        symbol_type=sym.symbol_type,
                        start_line=sym.start_line,
                        end_line=sym.end_line,
                        content=sym.content,
                        content_hash=compute_hash(sym.content),
                        analysis_mode="parser_aware",
                        language_display=language_display
                    )
                )

            # Prepend module preamble if symbols start later than line 5
            lines = code.splitlines(keepends=True)
            first_sym_start = min(s.start_line for s in symbols) if symbols else len(lines)
            if first_sym_start > 5:
                preamble_content = "".join(lines[0:first_sym_start - 1])
                chunks.insert(
                    0,
                    CodeChunkData(
                        file_path=file_path,
                        language=language,
                        symbol_name="<module_preamble>",
                        symbol_type="module",
                        start_line=1,
                        end_line=first_sym_start - 1,
                        content=preamble_content,
                        content_hash=compute_hash(preamble_content),
                        analysis_mode="parser_aware",
                        language_display=language_display
                    )
                )
        else:
            chunks = line_based_fallback_chunks(code, file_path, language, language_display)

    elif language in {"javascript", "typescript"}:
        js_result = parse_js_ts_symbols(code, file_path)
        symbols = js_result.get("symbols", [])
        relationships = js_result.get("relationships", [])

        if symbols:
            for sym in symbols:
                chunks.append(
                    CodeChunkData(
                        file_path=file_path,
                        language=language,
                        symbol_name=sym.name,
                        symbol_type=sym.symbol_type,
                        start_line=sym.start_line,
                        end_line=sym.end_line,
                        content=sym.content,
                        content_hash=compute_hash(sym.content),
                        analysis_mode="parser_aware",
                        language_display=language_display
                    )
                )
        else:
            chunks = line_based_fallback_chunks(code, file_path, language, language_display)

    elif adapter.parser_available:
        # Languages with regex/structural symbol parsers: Java, Go, Rust, C, C++, C#, Ruby, PHP, Kotlin, Swift, Scala, Dart
        symbols = extract_regex_symbols(code, file_path, language)
        if symbols:
            for sym in symbols:
                chunks.append(
                    CodeChunkData(
                        file_path=file_path,
                        language=language,
                        symbol_name=sym.name,
                        symbol_type=sym.symbol_type,
                        start_line=sym.start_line,
                        end_line=sym.end_line,
                        content=sym.content,
                        content_hash=compute_hash(sym.content),
                        analysis_mode="parser_aware",
                        language_display=language_display
                    )
                )
        else:
            chunks = line_based_fallback_chunks(code, file_path, language, language_display)

    else:
        # Generic text/code chunker fallback
        chunks = line_based_fallback_chunks(code, file_path, language, language_display)

    return chunks, relationships
