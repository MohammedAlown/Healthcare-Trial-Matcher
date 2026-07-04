"""
ingestion.py - Data Ingestion API Endpoints

Supports ingestion from:
  - ClinicalTrials.gov (clinical trial data)
  - PubMed (research articles)

Both single-condition and batch ingestion are supported.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database.connection import get_db
from backend.app.services.ingestion_service import (
    ingest_trials,
    ingest_multiple_conditions,
)
from backend.app.services.pubmed_ingestion_service import (
    ingest_pubmed_articles,
    ingest_pubmed_batch,
)
from backend.app.core.logger import logger

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])


# ============================================================
# Request Models
# ============================================================

class BatchTrialRequest(BaseModel):
    """Request body for batch trial ingestion."""
    conditions: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of medical conditions to ingest",
        examples=[["lung cancer", "diabetes", "breast cancer"]],
    )
    max_per_condition: int = Field(
        default=50, ge=1, le=200,
        description="Maximum trials per condition",
    )


class BatchPubMedRequest(BaseModel):
    """Request body for batch PubMed ingestion."""
    queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of search queries",
        examples=[["lung cancer treatment", "diabetes clinical trial"]],
    )
    max_per_query: int = Field(
        default=20, ge=1, le=100,
        description="Maximum articles per query",
    )


# ============================================================
# ClinicalTrials.gov Endpoints
# ============================================================

@router.post(
    "/trials",
    summary="Ingest Clinical Trials",
    description="Fetch and store trials from ClinicalTrials.gov.",
)
async def ingest_trials_endpoint(
    condition: str = Query(..., min_length=2, examples=["lung cancer"]),
    max_results: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Fetch trials for a single condition."""
    stats = await ingest_trials(db, condition, max_results)
    return stats


@router.post(
    "/trials/batch",
    summary="Batch Ingest Clinical Trials",
)
async def batch_ingest_trials(
    request: BatchTrialRequest,
    db: Session = Depends(get_db),
):
    """Fetch trials for multiple conditions."""
    all_stats = await ingest_multiple_conditions(
        db, request.conditions, request.max_per_condition
    )
    return {"conditions_processed": len(all_stats), "results": all_stats}


# ============================================================
# PubMed Endpoints
# ============================================================

@router.post(
    "/pubmed",
    summary="Ingest PubMed Articles",
    description="Fetch and store research articles from PubMed.",
)
async def ingest_pubmed_endpoint(
    query: str = Query(
        ...,
        min_length=2,
        description="Search query for PubMed",
        examples=["lung cancer immunotherapy"],
    ),
    max_results: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Fetch PubMed articles for a single query."""
    stats = await ingest_pubmed_articles(db, query, max_results)
    return stats


@router.post(
    "/pubmed/batch",
    summary="Batch Ingest PubMed Articles",
)
async def batch_ingest_pubmed(
    request: BatchPubMedRequest,
    db: Session = Depends(get_db),
):
    """Fetch PubMed articles for multiple queries."""
    all_stats = await ingest_pubmed_batch(
        db, request.queries, request.max_per_query
    )
    return {"queries_processed": len(all_stats), "results": all_stats}


# ============================================================
# Combined Ingestion
# ============================================================

@router.post(
    "/all",
    summary="Ingest Trials + PubMed",
    description="Ingest both clinical trials and PubMed articles for a condition.",
)
async def ingest_all(
    condition: str = Query(..., min_length=2, examples=["breast cancer"]),
    max_trials: int = Query(default=50, ge=1, le=200),
    max_articles: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    One-click ingestion: fetches both trials and PubMed articles
    for the same condition.
    """
    logger.info(f"Combined ingestion for: '{condition}'")

    trial_stats = await ingest_trials(db, condition, max_trials)
    pubmed_stats = await ingest_pubmed_articles(db, condition, max_articles)

    return {
        "condition": condition,
        "trials": trial_stats,
        "pubmed": pubmed_stats,
    }
