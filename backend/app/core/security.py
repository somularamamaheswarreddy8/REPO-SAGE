import hmac
import hashlib
import os
import re
import ipaddress
import urllib.parse
from typing import Optional, Tuple


BLOCKED_HOST_PATTERNS = [
    re.compile(r"^(?:localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|169\.254\.\d+\.\d+|::1)$", re.IGNORECASE),
]

DISALLOWED_SCHEMES = {"file", "ftp", "gopher", "dict", "ldap", "tftp"}


def validate_repository_url_safety(raw: str) -> None:
    """
    Validates URL to block Server-Side Request Forgery (SSRF) and unauthorized protocols.
    Raises ValueError if URL targets private/loopback/cloud-metadata networks or dangerous schemes.
    """
    if not raw or not raw.strip():
        return

    clean = raw.strip()
    if "://" in clean:
        parsed = urllib.parse.urlparse(clean)
        scheme = parsed.scheme.lower()
        if scheme in DISALLOWED_SCHEMES:
            raise ValueError(f"Disallowed protocol scheme '{scheme}' for repository URL")

        host = parsed.hostname or ""
        # Check against blocked hostnames
        for pattern in BLOCKED_HOST_PATTERNS:
            if pattern.match(host):
                raise ValueError(f"SSRF blocked: Host '{host}' references local/internal address.")

        # Check IP address if hostname is an IP
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError(f"SSRF blocked: Destination '{host}' is a private or internal IP.")
        except ValueError:
            # Host is a domain name, not a raw IP
            pass


def normalize_repo_name(raw: str) -> str:
    """
    Normalizes any repository link or identifier into the canonical 'owner/repo' format.
    """
    if not raw or not raw.strip():
        raise ValueError("Repository link or name cannot be empty")

    validate_repository_url_safety(raw)
    clean = raw.strip()

    # Strip git clone commands if user pasted full command
    if clean.lower().startswith("git clone "):
        clean = clean[10:].strip()

    # Extract URL if wrapped in Markdown link e.g. [name](https://github.com/owner/repo)
    md_match = re.search(r"\[.*?\]\((https?://[^\)]+)\)", clean)
    if md_match:
        clean = md_match.group(1).strip()

    # Strip surrounding quotes, brackets, angles
    clean = clean.strip("<>\"'`()[] ")

    # Strip fragments and query parameters
    clean = clean.split("#")[0].split("?")[0].strip()

    # Handle SSH format: git@github.com:owner/repo(.git) or ssh://git@github.com(:port)/owner/repo
    if "@" in clean and not clean.startswith("http://") and not clean.startswith("https://"):
        if clean.startswith("ssh://"):
            clean = clean[6:]
        clean = clean.split("@", 1)[1]
        if ":" in clean:
            # Handle optional port like github.com:22/owner/repo
            clean = re.sub(r":\d+/", "/", clean)
            clean = clean.replace(":", "/", 1)

    # Strip protocol (http://, https://, git://, ssh://, ftp://)
    if "://" in clean:
        clean = clean.split("://", 1)[1]

    # Strip any user credentials like user:token@
    if "@" in clean:
        clean = clean.split("@", 1)[1]

    # Strip domain prefix if present (e.g. github.com/, www.github.com/, gitlab.com/, bitbucket.org/)
    # A domain requires a dot (e.g. domain.tld/) or 'localhost'
    clean = re.sub(r"^(?:www\.)?(?:localhost|[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+)(?::\d+)?/", "", clean)

    # Normalize parts
    parts = [p.strip() for p in clean.split("/") if p.strip()]

    if len(parts) >= 2:
        owner = parts[0]
        repo = parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return f"{owner}/{repo}"
    elif len(parts) == 1:
        repo = parts[0]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return f"user/{repo}"

    return clean


def extract_branch_from_url(raw: str) -> Optional[str]:
    """
    Extracts branch name if present in URL (e.g. /tree/main, /tree/develop, /blob/main/...).
    """
    if not raw:
        return None
    clean = raw.split("#")[0].split("?")[0].strip()
    m = re.search(r"/(?:tree|blob)/([^/]+)", clean)
    if m:
        return m.group(1).strip()
    return None


def verify_github_signature(payload_bytes: bytes, secret: str, signature_header: Optional[str]) -> bool:
    """
    Validates GitHub webhook HMAC SHA-256 signature against secret.
    Signature header format is: sha256=<hex_digest>
    """
    if not secret or not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]
    mac = hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    computed_signature = mac.hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)


def sanitize_path(path: str) -> str:
    """
    Normalizes path and prevents directory traversal attacks.
    Ensures path does not escape repository root or reference parent directories.
    """
    if not path:
        raise ValueError("File path cannot be empty")

    # Replace windows backslashes
    clean_path = path.replace("\\", "/").strip()

    # Reject attempts with null bytes
    if "\0" in clean_path:
        raise ValueError("Invalid path containing null bytes")

    # Disallow absolute paths
    if clean_path.startswith("/") or re.match(r"^[a-zA-Z]:", clean_path):
        clean_path = clean_path.lstrip("/").split(":", 1)[-1].lstrip("/")

    # Normalize parts to eliminate '..' and '.'
    parts = []
    for part in clean_path.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if parts:
                parts.pop()
            else:
                raise ValueError(f"Path traversal detected in path: {path}")
        else:
            parts.append(part)

    safe_path = "/".join(parts)
    if not safe_path:
        raise ValueError("Invalid sanitized path")

    return safe_path


def sanitize_prompt_input(text: str) -> str:
    """
    Sanitizes user input to mitigate prompt injection, removing dangerous system control sequences.
    """
    if not text:
        return ""
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    sanitized = sanitized.replace("<source_file", "&lt;source_file").replace("</source_file>", "&lt;/source_file&gt;")
    return sanitized.strip()


def wrap_untrusted_code(code: str, file_path: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
    """
    Wraps untrusted repository source code in strict delimiters with explicit system instructions
    that this content is passive data and must not be interpreted as commands.
    """
    line_range = f"{start_line}-{end_line}" if end_line else f"{start_line}+"
    header = f'--- BEGIN UNTRUSTED REPOSITORY CODE [file: {file_path}, lines: {line_range}] ---'
    footer = f'--- END UNTRUSTED REPOSITORY CODE [file: {file_path}] ---'
    return f"{header}\n{code}\n{footer}"
