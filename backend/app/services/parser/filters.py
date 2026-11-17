import os
import fnmatch
from typing import Tuple, Optional
from app.core.config import settings
from app.services.parser.secret_scanner import scan_content_for_secrets


def classify_file_safety(
    file_path: str,
    file_size_bytes: int,
    content: Optional[str] = None
) -> Tuple[bool, Optional[str], str, bool, bool]:
    """
    Classifies a file's safety, category, and eligibility for indexing and preview.
    Returns:
        allowed: bool (True if allowed for text ingestion and preview)
        exclusion_reason: Optional[str]
        category: str ("secret" | "binary" | "vendor" | "oversized" | "hidden" | "allowed")
        is_secret: bool (True if sensitive credential pattern)
        is_binary: bool (True if non-text binary/media)
    """
    clean_path = file_path.replace("\\", "/").strip("/")
    filename = os.path.basename(clean_path)
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    # 1. Check sensitive filename patterns (secrets, keys, tokens)
    for pattern in settings.SENSITIVE_PATTERNS:
        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
            reason = f"Matches sensitive credential pattern '{pattern}' (excluded for zero-leakage security)"
            return False, reason, "secret", True, False

    # 2. Check excluded binary / media extensions
    if ext in settings.EXCLUDED_EXTENSIONS:
        reason = f"Excluded file extension '{ext}'"
        return False, reason, "binary", False, True

    # 3. Check excluded directories (vendor, node_modules, .git, venv)
    parts = clean_path.split("/")
    for part in parts[:-1]:
        if part in settings.EXCLUDED_DIRS:
            reason = f"Inside excluded directory '{part}'"
            return False, reason, "vendor", False, False

    # 4. Check file size
    if file_size_bytes > settings.MAX_FILE_SIZE_BYTES:
        reason = f"File exceeds maximum allowed size ({file_size_bytes} > {settings.MAX_FILE_SIZE_BYTES} bytes)"
        return False, reason, "oversized", False, False

    # 5. Hidden dotfile check (e.g. .DS_Store)
    if filename.startswith(".") and not ext and filename not in {
        ".dockerignore", ".editorconfig", ".gitattributes", ".npmrc", ".env.example"
    }:
        reason = f"Hidden system file '{filename}'"
        return False, reason, "hidden", False, False

    # 6. Deep Content Secret Scan (if file content is provided)
    if content:
        has_secret, secret_desc = scan_content_for_secrets(content)
        if has_secret:
            return False, f"Embedded secret detected: {secret_desc}", "secret", True, False

    return True, None, "allowed", False, False


def should_index_file(file_path: str, file_size_bytes: int) -> Tuple[bool, str]:
    """
    Evaluates whether a file should be indexed based on safety, size, and type limits.
    Returns (should_index, reason). Preserves existing contract.
    """
    allowed, reason, _, _, _ = classify_file_safety(file_path, file_size_bytes)
    if not allowed:
        return False, reason or "Excluded file"
    return True, "OK"
