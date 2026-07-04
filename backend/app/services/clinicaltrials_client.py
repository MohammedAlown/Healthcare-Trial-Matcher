"""
clinicaltrials_client.py - ClinicalTrials.gov API v2 Client

ClinicalTrials.gov provides a free public API to search and download
clinical study data. We use their v2 API which returns JSON.

API Docs: https://clinicaltrials.gov/data-api/api

How it works:
  1. We send a search query (e.g. "lung cancer") to their API
  2. They return a paginated list of studies in JSON format
  3. We parse each study into our database format
  4. We store them in PostgreSQL

No API key is needed — it's completely free and public.
"""

import httpx
from typing import Optional
from backend.app.core.logger import logger


# Base URL for ClinicalTrials.gov API v2
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


async def fetch_trials(
    condition: str,
    max_results: int = 50,
    page_token: Optional[str] = None,
) -> dict:
    """
    Search ClinicalTrials.gov for studies matching a condition.

    Args:
        condition: Medical condition to search (e.g. "lung cancer")
        max_results: Maximum number of studies to return (1-1000)
        page_token: Token for pagination (from previous response)

    Returns:
        Raw JSON response from the API containing study data

    Example API URL:
        https://clinicaltrials.gov/api/v2/studies?query.cond=lung+cancer&pageSize=10
    """
    params = {
        "query.cond": condition,          # Search by condition
        "pageSize": min(max_results, 50), # API max per page is 50
        "format": "json",
    }

    # Add fields we want returned (reduces response size)
    params["fields"] = ",".join([
        "NCTId",
        "BriefTitle",
        "BriefSummary",
        "DetailedDescription",
        "OverallStatus",
        "Phase",
        "Condition",
        "InterventionName",
        "InterventionType",
        "EligibilityCriteria",
        "LeadSponsorName",
        "EnrollmentCount",
        "StartDate",
        "CompletionDate",
        "LocationCity",
        "LocationCountry",
        "LocationFacility",
        "StudyFirstPostDate",
        "LastUpdatePostDate",
    ])

    if page_token:
        params["pageToken"] = page_token

    logger.info(f"Fetching trials for condition: '{condition}' (max: {max_results})")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

    num_studies = len(data.get("studies", []))
    logger.info(f"Received {num_studies} studies from ClinicalTrials.gov")

    return data


async def fetch_trial_by_nct_id(nct_id: str) -> dict:
    """
    Fetch a single study by its NCT ID.

    Args:
        nct_id: The NCT identifier (e.g. "NCT04012345")

    Returns:
        Raw JSON for a single study
    """
    url = f"{BASE_URL}/{nct_id}"
    logger.info(f"Fetching single trial: {nct_id}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params={"format": "json"})
        response.raise_for_status()

    return response.json()
