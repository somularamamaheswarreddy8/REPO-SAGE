from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
import redis.asyncio as aioredis

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check endpoint: verifies DB and Redis connectivity."""
    db_ok = False
    redis_ok = False
    details = {}

    # Check Database
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        details["database"] = "connected"
    except Exception as e:
        details["database"] = f"unreachable: {str(e)}"

    # Check Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
        await r.ping()
        await r.aclose()
        redis_ok = True
        details["redis"] = "connected"
    except Exception as e:
        details["redis"] = f"unreachable: {str(e)}"

    # In development/demo mode, if database is connected, service is ready
    if not db_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "details": details}
        )

    return {
        "status": "ready",
        "database": db_ok,
        "redis": redis_ok,
        "details": details
    }
