from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    action_type: str
    user_id: str
    repo_full_name: str
    pr_number: Optional[int]
    target_file: Optional[str]
    target_lines: Optional[str]
    payload_summary: str
    status: str
    previous_hash: Optional[str] = None
    entry_hash: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    index_commit_sha: Optional[str] = None
    eval_version: Optional[str] = None
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
