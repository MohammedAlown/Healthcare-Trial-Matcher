"""
trials.py - Clinical Trial Matching Endpoints

Now connected to PostgreSQL via SQLAlchemy.
Supports creating trials, fetching by ID, listing, and matching.
"""

import time
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.app.models.schemas import PatientQuery, MatchResponse, TrialMatch
from backend.app.core.logger import logger
from database.connection import get_db
from database import crud

router = APIRouter(prefix="/trials", tags=["Trials"])


@router.post(
    "/match",
    response_model=MatchResponse,
    summary="Match Patient to Clinical Trials",
)
async def match_trials(query: PatientQuery, db: Session = Depends(get_db)):
    """
    Accepts a patient query and returns matching clinical trials.
    Currently returns mock data — connected to RAG in Milestone 9.
    """
    start_time = time.time()
    logger.info(f"Received match request: condition='{query.condition}'")

    # Log the search action for audit/governance
    crud.create_audit_log(
        db=db,
        action="search",
        entity_type="patient_query",
        details={"condition": query.condition, "age": query.age, "gender": query.gender},
    )

    # Mock results (will be replaced by real vector search)
    mock_matches = [
        TrialMatch(
            trial_id="NCT04012345",
            title="A Phase 3 Study of Immunotherapy in Advanced NSCLC",
            relevance_score=0.95,
            match_explanation=(
                f"This trial targets {query.condition} and is currently "
                "recruiting patients matching the specified criteria."
            ),
            status="Recruiting",
        ),
        TrialMatch(
            trial_id="NCT04067890",
            title="Combination Therapy for Solid Tumors",
            relevance_score=0.82,
            match_explanation=(
                "This trial includes patients with similar conditions "
                "and accepts a broad age range."
            ),
            status="Recruiting",
        ),
    ]

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"Returning {len(mock_matches)} matches in {elapsed_ms:.1f}ms")

    return MatchResponse(
        query=query.condition,
        matches=mock_matches,
        total_matches=len(mock_matches),
        search_time_ms=round(elapsed_ms, 2),
    )


@router.get(
    "/list",
    summary="List Clinical Trials",
    description="Retrieve trials from the database with optional filtering.",
)
async def list_trials(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    status: str = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """List trials from PostgreSQL with pagination."""
    trials = crud.get_trials(db, skip=skip, limit=limit, status=status)
    total = crud.count_trials(db)
    return {
        "trials": [
            {
                "nct_id": t.nct_id,
                "title": t.title,
                "status": t.status,
                "phase": t.phase,
                "conditions": t.conditions,
            }
            for t in trials
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/stats",
    summary="Database Statistics",
    description="Get counts of trials and articles in the database.",
)
async def get_stats(db: Session = Depends(get_db)):
    """Return database statistics."""
    return {
        "clinical_trials": crud.count_trials(db),
        "pubmed_articles": crud.count_articles(db),
    }


@router.get(
    "/{trial_id}",
    summary="Get Trial Details",
)
async def get_trial(trial_id: str, db: Session = Depends(get_db)):
    """Fetch a single trial by NCT ID from PostgreSQL."""
    logger.info(f"Fetching trial: {trial_id}")

    trial = crud.get_trial_by_nct_id(db, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial {trial_id} not found")

    return {
        "nct_id": trial.nct_id,
        "title": trial.title,
        "brief_summary": trial.brief_summary,
        "status": trial.status,
        "phase": trial.phase,
        "conditions": trial.conditions,
        "interventions": trial.interventions,
        "eligibility_criteria": trial.eligibility_criteria,
        "sponsor": trial.sponsor,
        "url": trial.url,
        "created_at": trial.created_at,
    }
