import hashlib
import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.audit import AuditLogEntry


def compute_entry_hash(
    previous_hash: str,
    action_type: str,
    user_id: str,
    repo_full_name: str,
    payload_summary: str,
    timestamp_iso: str
) -> str:
    """Computes a SHA-256 tamper-evident hash for an audit log entry."""
    data = f"{previous_hash}|{action_type}|{user_id}|{repo_full_name}|{payload_summary}|{timestamp_iso}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


async def record_audit_event(
    db: AsyncSession,
    action_type: str,
    user_id: str,
    repo_full_name: str,
    payload_summary: str,
    pr_number: Optional[int] = None,
    target_file: Optional[str] = None,
    target_lines: Optional[str] = None,
    model_name: Optional[str] = None,
    prompt_version: Optional[str] = None,
    index_commit_sha: Optional[str] = None,
    eval_version: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None
) -> AuditLogEntry:
    """
    Appends a new cryptographically chained, tamper-evident audit record.
    """
    # 1. Fetch latest audit entry to get previous_hash
    stmt = select(AuditLogEntry).order_by(desc(AuditLogEntry.id)).limit(1)
    res = await db.execute(stmt)
    latest_entry = res.scalar_one_or_none()

    previous_hash = latest_entry.entry_hash if (latest_entry and latest_entry.entry_hash) else "GENESIS_REPOSAGE_AUDIT_BLOCK_00000000"

    now = datetime.datetime.utcnow()
    now_iso = now.isoformat()

    entry_hash = compute_entry_hash(
        previous_hash=previous_hash,
        action_type=action_type,
        user_id=user_id,
        repo_full_name=repo_full_name,
        payload_summary=payload_summary,
        timestamp_iso=now_iso
    )

    entry = AuditLogEntry(
        action_type=action_type,
        user_id=user_id,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        target_file=target_file,
        target_lines=target_lines,
        payload_summary=payload_summary,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
        model_name=model_name,
        prompt_version=prompt_version,
        index_commit_sha=index_commit_sha,
        eval_version=eval_version,
        status=status,
        error_message=error_message,
        ip_address=ip_address,
        created_at=now
    )

    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def verify_audit_trail_integrity(db: AsyncSession) -> Dict[str, Any]:
    """
    Verifies that the entire audit trail log is cryptographically untampered.
    Returns audit status, total entries checked, and any broken chain links.
    """
    stmt = select(AuditLogEntry).order_by(AuditLogEntry.id.asc())
    res = await db.execute(stmt)
    entries = res.scalars().all()

    if not entries:
        return {
            "is_valid": True,
            "total_entries": 0,
            "tampered_entry_id": None,
            "message": "Audit log is empty; chain is valid."
        }

    expected_previous = "GENESIS_REPOSAGE_AUDIT_BLOCK_00000000"
    for entry in entries:
        # Check chain link
        if entry.previous_hash and entry.previous_hash != expected_previous:
            return {
                "is_valid": False,
                "total_entries": len(entries),
                "tampered_entry_id": entry.id,
                "message": f"Tampering detected at entry #{entry.id}: previous_hash mismatch."
            }

        # Verify entry_hash
        computed = compute_entry_hash(
            previous_hash=entry.previous_hash or expected_previous,
            action_type=entry.action_type,
            user_id=entry.user_id,
            repo_full_name=entry.repo_full_name,
            payload_summary=entry.payload_summary,
            timestamp_iso=entry.created_at.isoformat()
        )

        if entry.entry_hash and entry.entry_hash != computed:
            return {
                "is_valid": False,
                "total_entries": len(entries),
                "tampered_entry_id": entry.id,
                "message": f"Tampering detected at entry #{entry.id}: hash signature mismatch."
            }

        expected_previous = entry.entry_hash or computed

    return {
        "is_valid": True,
        "total_entries": len(entries),
        "tampered_entry_id": None,
        "latest_block_hash": expected_previous,
        "message": f"All {len(entries)} audit log entries verified against cryptographic chain."
    }
