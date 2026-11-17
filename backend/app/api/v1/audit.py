from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.audit import AuditLogEntry
from app.schemas.audit import AuditLogResponse
from app.services.audit import verify_audit_trail_integrity

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Returns immutable audit log records of user-approved write actions:
    publishing comments, updating security settings, or applying code patches.
    """
    stmt = select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/verify")
async def verify_audit_log_chain(db: AsyncSession = Depends(get_db)):
    """
    Cryptographically verifies the append-only, tamper-evident hash chain across all audit log records.
    """
    result = await verify_audit_trail_integrity(db)
    return result
