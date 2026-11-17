import re
import math
from typing import Tuple, Optional

# Regular expression patterns for high-confidence secrets
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE), "Private cryptographic key header"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"(?:aws_secret_access_key|aws_access_key_id)\s*[:=]\s*['\"][A-Za-z0-9/+=]{20,}['\"]", re.IGNORECASE), "AWS Secret Key configuration"),
    (re.compile(r"ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"gho_[0-9a-zA-Z]{36}"), "GitHub OAuth Access Token"),
    (re.compile(r"github_pat_[0-9a-zA-Z_]{60,}"), "Fine-grained GitHub Personal Access Token"),
    (re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"), "Slack API Token"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "Google API Key"),
    (re.compile(r"sk_live_[0-9a-zA-Z]{24}"), "Stripe Live Secret Key"),
    (re.compile(r"(?:password|passwd|secret|api_key|apikey|access_token|bearer_token)\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]", re.IGNORECASE), "Hardcoded credential assignment"),
]


def shannon_entropy(data: str) -> float:
    """Calculates the Shannon entropy of a string."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    for x in set(data):
        p_x = float(data.count(x)) / length
        if p_x > 0:
            entropy += - p_x * math.log2(p_x)
    return entropy


def scan_content_for_secrets(content: str) -> Tuple[bool, Optional[str]]:
    """
    Scans source code / text content for embedded secrets, private keys, and high-entropy credentials.
    Returns:
        is_secret (bool): True if content contains an identified secret.
        reason (str): Description of the detected secret pattern.
    """
    if not content or not isinstance(content, str):
        return False, None

    # Check high-confidence regex patterns
    for pattern, description in SECRET_PATTERNS:
        match = pattern.search(content)
        if match:
            matched_snippet = match.group(0)
            redacted = matched_snippet[:4] + "***" + matched_snippet[-2:] if len(matched_snippet) > 6 else "***"
            return True, f"Detected {description} ('{redacted}')"

    # High-entropy token detection on suspicious lines
    for line in content.splitlines():
        line_clean = line.strip()
        if len(line_clean) > 200:
            continue
        # Look for tokens in assignments or credentials
        lower_line = line_clean.lower()
        if any(keyword in lower_line for keyword in ["token", "secret", "key", "auth", "credential", "private"]):
            tokens = re.findall(r"['\"]([A-Za-z0-9_\-+/=]{24,})['\"]", line_clean)
            for token in tokens:
                if shannon_entropy(token) > 4.2:
                    return True, "Detected high-entropy credential or token in configuration"

    return False, None
