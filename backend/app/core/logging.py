import logging
import json
import re
from datetime import datetime
from typing import Any, Dict
from contextvars import ContextVar

# Context variables for correlation IDs
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
job_id_ctx: ContextVar[str] = ContextVar("job_id", default="")

SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE),
    re.compile(r"(?i)(token\s*[:=]\s*['\"])[^'\"]{8,}['\"]", re.IGNORECASE),
    re.compile(r"(?i)(password\s*[:=]\s*['\"])[^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"])[^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"(?i)(secret\s*[:=]\s*['\"])[^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
]


def mask_sensitive_text(text: str) -> str:
    """Masks secrets and tokens from log messages."""
    if not isinstance(text, str):
        return text
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(r"\1[REDACTED]" if r"\1" in pattern.pattern else "[REDACTED]", result)
    return result


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as JSON with correlation IDs and masked secrets."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_text(record.getMessage()),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }

        # Add correlation IDs if present
        req_id = request_id_ctx.get()
        if req_id:
            log_entry["request_id"] = req_id

        job_id = job_id_ctx.get()
        if job_id:
            log_entry["job_id"] = job_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Merge extra fields
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            for k, v in record.extra.items():
                if k not in log_entry:
                    log_entry[k] = mask_sensitive_text(str(v)) if isinstance(v, str) else v

        return json.dumps(log_entry)


def setup_logging(level: str = "INFO") -> None:
    """Configures structured JSON logging for the application."""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers = [handler]

    # Silence overly verbose loggers
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.access").propagate = False
