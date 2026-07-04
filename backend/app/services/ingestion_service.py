"""
ingestion_service.py - Orchestrates the Data Ingestion Pipeline

This is the main service that ties everything together:
  1. Calls the ClinicalTrials.gov API client to fetch raw data
  2. Calls the parser to transform it
  3. Calls the CRUD layer to store it in PostgreSQL
  4. Logs everything for audit/governance

It supports:
  - Single condition ingestion
  - Multi-condition batch ingestion
  - Pagination for large result sets
"""

import time
from sqlalchemy.orm import Session

from backend.app.services.clinicaltrials_client import fetch_trials
from backend.app.services.clinicaltrials_parser import parse_api_response
from backend.app.core.logger import logger
from database import crud


async def ingest_trials(
    db: Session,
    condition: str,
    max_results: int = 50,
) -> dict:
    """
    Fetch, parse, and store clinical trials for a given condition.

    Args:
        db: Database session
        condition: Medical condition to search (e.g. "diabetes")
        max_results: Maximum number of trials to fetch

    Returns:
        Summary dict with counts of created/updated/failed records
    """
    start_time = time.time()
    logger.info(f"Starting ingestion for condition: '{condition}'")

    # Track results
    stats = {
        "condition": condition,
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "failed": 0,
    }

    try:
        # Step 1: Fetch from API
        api_response = await fetch_trials(condition, max_results=max_results)
        parsed_trials = parse_api_response(api_response)
        stats["fetched"] = len(parsed_trials)

        # Step 2: Store each trial in the database
        for trial_data in parsed_trials:
            try:
                # Check if trial already exists
                existing = crud.get_trial_by_nct_id(db, trial_data["nct_id"])

                if existing:
                    # Update existing trial
                    crud.upsert_trial(db, trial_data)
                    stats["updated"] += 1
                else:
                    # Create new trial
                    crud.create_trial(db, trial_data)
                    stats["created"] += 1

            except Exception as e:
                logger.error(f"Failed to store trial {trial_data.get('nct_id')}: {e}")
                stats["failed"] += 1

        # Step 3: Log the ingestion for audit
        crud.create_audit_log(
            db=db,
            action="ingest_trials",
            entity_type="clinical_trial",
            details=stats,
            user_id="system",
        )

    except Exception as e:
        logger.error(f"Ingestion failed for '{condition}': {e}")
        stats["error"] = str(e)

    elapsed = time.time() - start_time
    stats["elapsed_seconds"] = round(elapsed, 2)

    logger.info(
        f"Ingestion complete: {stats['created']} created, "
        f"{stats['updated']} updated, {stats['failed']} failed "
        f"in {elapsed:.2f}s"
    )

    return stats


async def ingest_multiple_conditions(
    db: Session,
    conditions: list[str],
    max_per_condition: int = 50,
) -> list[dict]:
    """
    Ingest trials for multiple conditions.

    Args:
        db: Database session
        conditions: List of conditions to search
        max_per_condition: Max trials per condition

    Returns:
        List of stats dicts, one per condition
    """
    logger.info(f"Starting batch ingestion for {len(conditions)} conditions")
    all_stats = []

    for condition in conditions:
        stats = await ingest_trials(db, condition, max_per_condition)
        all_stats.append(stats)

    total_created = sum(s["created"] for s in all_stats)
    total_updated = sum(s["updated"] for s in all_stats)
    logger.info(
        f"Batch ingestion complete: {total_created} created, "
        f"{total_updated} updated across {len(conditions)} conditions"
    )

    return all_stats
