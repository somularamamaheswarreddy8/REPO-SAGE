import os
import re
from typing import Optional, Tuple
from app.services.languages.models import LanguageAdapter, AnalysisMode
from app.services.languages.registry import language_registry


def detect_file_language(
    file_path: str,
    content: Optional[str] = None
) -> Tuple[LanguageAdapter, str]:
    """
    Detects language adapter and appropriate analysis mode.
    Returns (LanguageAdapter, AnalysisMode string: 'parser_aware' | 'text_fallback').
    
    Detection order:
    1. Recognized filenames (e.g. Dockerfile, Makefile, Gemfile, Cargo.toml)
    2. File extensions (e.g. .py, .go, .rs, .ts, .sol)
    3. Shebang line (#/usr/bin/env python, #!/bin/bash, etc.)
    4. Safe content inspection (e.g. <?php, <!DOCTYPE html)
    5. Fallback to generic_code adapter (never silently skipped!)
    
    Safety:
    - Never executes repository code.
    - Inspects at most the first 500 characters / first few lines.
    """
    clean_path = file_path.replace("\\", "/").strip("/")
    filename = os.path.basename(clean_path).lower()
    _, ext = os.path.splitext(filename)

    # 1. Recognized filenames
    by_filename = language_registry.get_by_filename(filename)
    if by_filename:
        mode = AnalysisMode.PARSER_AWARE if by_filename.parser_available else AnalysisMode.TEXT_FALLBACK
        return by_filename, mode.value

    # Check for filenames like Dockerfile.prod or Makefile.inc
    if filename.startswith("dockerfile."):
        adapter = language_registry.get_by_name("dockerfile")
        if adapter:
            return adapter, AnalysisMode.TEXT_FALLBACK.value

    # 2. File extension
    if ext:
        by_ext = language_registry.get_by_extension(ext)
        if by_ext:
            mode = AnalysisMode.PARSER_AWARE if by_ext.parser_available else AnalysisMode.TEXT_FALLBACK
            return by_ext, mode.value

    # 3. Shebang & safe content inspection (if content is provided)
    if content:
        lines = content.splitlines()
        first_line = lines[0].strip() if lines else ""

        # Check shebang
        if first_line.startswith("#!"):
            shebang_lower = first_line.lower()
            if "python" in shebang_lower:
                ad = language_registry.get_by_name("python")
                return ad, AnalysisMode.PARSER_AWARE.value
            elif "bash" in shebang_lower or "sh" in shebang_lower or "zsh" in shebang_lower:
                ad = language_registry.get_by_name("bash")
                return ad, AnalysisMode.TEXT_FALLBACK.value
            elif "node" in shebang_lower:
                ad = language_registry.get_by_name("javascript")
                return ad, AnalysisMode.PARSER_AWARE.value
            elif "ruby" in shebang_lower:
                ad = language_registry.get_by_name("ruby")
                return ad, AnalysisMode.PARSER_AWARE.value
            elif "perl" in shebang_lower:
                ad = language_registry.get_by_name("perl")
                return ad, AnalysisMode.TEXT_FALLBACK.value
            elif "pwsh" in shebang_lower or "powershell" in shebang_lower:
                ad = language_registry.get_by_name("powershell")
                return ad, AnalysisMode.TEXT_FALLBACK.value

        # Safe content inspection
        preview = content[:500].strip()
        if preview.startswith("<?php") or "<?php" in preview:
            ad = language_registry.get_by_name("php")
            return ad, AnalysisMode.PARSER_AWARE.value
        elif preview.startswith("<!DOCTYPE html") or preview.startswith("<html"):
            ad = language_registry.get_by_name("html")
            return ad, AnalysisMode.TEXT_FALLBACK.value
        elif preview.startswith("{") and preview.endswith("}"):
            try:
                import json
                json.loads(preview)
                ad = language_registry.get_by_name("json")
                return ad, AnalysisMode.TEXT_FALLBACK.value
            except Exception:
                pass
        elif preview.startswith("---"):
            ad = language_registry.get_by_name("yaml")
            return ad, AnalysisMode.TEXT_FALLBACK.value

    # 5. Generic Code/Text Fallback
    fallback_adapter = language_registry.get_by_name("generic_code")
    return fallback_adapter, AnalysisMode.TEXT_FALLBACK.value
