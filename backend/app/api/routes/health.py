"""
health.py - Health Check Endpoint

Every production API needs a health check endpoint.
Monitoring tools (Docker, Kubernetes, load balancers) hit this
endpoint to verify the service is alive and responding.
"""

from fastapi import APIRouter
from datetime import datetime

from backend.app.core.config import settings
from backend.app.models.schemas import HealthResponse

# APIRouter groups related endpoints together
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the current status of the API service.",
)
async def health_check():
    """
    Returns service status, app name, version, and server timestamp.
    Used by monitoring tools to verify the API is running.
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
    )
