"""
ingestion.py - Data Ingestion API Endpoints

These endpoints let you trigger data ingestion from ClinicalTrials.gov
through the Swagger UI or any HTTP client.

Endpoints:
  POST /ingest/trials          - Ingest trials for a single condition
  POST /ingest/trials/batch    - Ingest trials for multiple conditions
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database.connection import get_db
from backend.app.services.ingestion_service import (
    ingest_trials,
    ingest_multiple_conditions,
)
from backend.app.core.logger import logger

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])


class BatchIngestionRequest(BaseModel):
    """Request body for batch ingestion."""
    conditions: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of medical conditions to ingest",
        examples=[["lung cancer", "diabetes", "breast cancer"]],
    )
    max_per_condition: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum trials to fetch per condition",
    )


@router.post(
    "/trials",
    summary="Ingest Clinical Trials",
    description="Fetch and store clinical trials from ClinicalTrials.gov for a condition.",
)
async def ingest_trials_endpoint(
    condition: str = Query(
        ...,
        min_length=2,
        description="Medical condition to search",
        examples=["lung cancer"],
    ),
    max_results: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of trials to fetch",
    ),
    db: Session = Depends(get_db),
):
    """
    Fetches trials from ClinicalTrials.gov API, parses them,
    and stores them in PostgreSQL.
    """
    logger.info(f"API request: ingest trials for '{condition}'")
    stats = await ingest_trials(db, condition, max_results)
    return stats


@router.post(
    "/trials/batch",
    summary="Batch Ingest Clinical Trials",
    description="Ingest trials for multiple conditions at once.",
)
async def batch_ingest_endpoint(
    request: BatchIngestionRequest,
    db: Session = Depends(get_db),
):
    """
    Fetches trials for multiple conditions in sequence.
    Useful for populating the database with diverse trial data.
    """
    logger.info(f"API request: batch ingest for {len(request.conditions)} conditions")
    all_stats = await ingest_multiple_conditions(
        db, request.conditions, request.max_per_condition
    )
    return {
        "conditions_processed": len(all_stats),
        "results": all_stats,
    }
