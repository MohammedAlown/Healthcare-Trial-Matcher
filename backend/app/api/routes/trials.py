"""
trials.py - Clinical Trial Matching Endpoints

These are placeholder endpoints that will be connected to the
RAG engine in later milestones. For now they return mock data
so we can verify the API structure works end-to-end.
"""

import time
from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import PatientQuery, MatchResponse, TrialMatch
from backend.app.core.logger import logger

router = APIRouter(prefix="/trials", tags=["Trials"])


@router.post(
    "/match",
    response_model=MatchResponse,
    summary="Match Patient to Clinical Trials",
    description="Send a patient query and receive matching clinical trials.",
)
async def match_trials(query: PatientQuery):
    """
    Accepts a patient query and returns matching clinical trials.

    Currently returns mock data. Will be connected to:
    - Qdrant vector search (Milestone 8)
    - RAG engine with LangChain (Milestone 9)
    - Cross-Encoder reranking (Milestone 10)
    """
    start_time = time.time()
    logger.info(f"Received match request: condition='{query.condition}'")

    # --- Mock results (replaced with real search in Milestone 9) ---
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
    "/{trial_id}",
    summary="Get Trial Details",
    description="Retrieve details of a specific clinical trial by its NCT ID.",
)
async def get_trial(trial_id: str):
    """
    Fetch a single trial by NCT ID.
    Will be connected to PostgreSQL in Milestone 3.
    """
    logger.info(f"Fetching trial: {trial_id}")

    # Placeholder — will query PostgreSQL in Milestone 3
    return {
        "trial_id": trial_id,
        "title": f"Trial {trial_id} (placeholder)",
        "status": "Recruiting",
        "message": "Full data available after Milestone 3 (PostgreSQL)",
    }
