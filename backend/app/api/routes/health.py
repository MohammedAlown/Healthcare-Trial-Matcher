"""
health.py - Health Check Endpoint

Now includes database connectivity check.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from backend.app.core.config import settings
from backend.app.models.schemas import HealthResponse
from database.connection import get_db

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health Check",
    description="Returns API and database status.",
)
async def health_check(db: Session = Depends(get_db)):
    """Check API and database health."""
    # Test database connection
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow(),
        "database": db_status,
    }
