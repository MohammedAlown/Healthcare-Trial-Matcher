"""
clinicaltrials_parser.py - Parse ClinicalTrials.gov API Responses

The API returns deeply nested JSON. This module extracts the fields
we need and flattens them into simple dictionaries that match our
database model (ClinicalTrial table).

The API v2 response structure looks like:
{
  "studies": [
    {
      "protocolSection": {
        "identificationModule": { "nctId": "NCT...", "briefTitle": "..." },
        "statusModule": { "overallStatus": "Recruiting" },
        "descriptionModule": { "briefSummary": "..." },
        ...
      }
    }
  ]
}
"""

from typing import Optional
from backend.app.core.logger import logger


def _safe_get(data: dict, *keys, default=None):
    """
    Safely navigate nested dictionaries.

    Example:
        _safe_get(study, "protocolSection", "statusModule", "overallStatus")
        Instead of: study["protocolSection"]["statusModule"]["overallStatus"]

    If any key is missing, returns default instead of crashing.
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def parse_study(study: dict) -> Optional[dict]:
    """
    Parse a single study from the API response into a flat dictionary
    matching our ClinicalTrial database model.

    Args:
        study: Raw study JSON from the API

    Returns:
        Dictionary ready to insert into the database, or None if parsing fails
    """
    try:
        protocol = study.get("protocolSection", {})

        # --- Identification ---
        id_module = protocol.get("identificationModule", {})
        nct_id = id_module.get("nctId")

        if not nct_id:
            logger.warning("Study missing NCT ID, skipping")
            return None

        # --- Status ---
        status_module = protocol.get("statusModule", {})

        # --- Description ---
        desc_module = protocol.get("descriptionModule", {})

        # --- Design ---
        design_module = protocol.get("designModule", {})
        phases = design_module.get("phases", [])
        phase = ", ".join(phases) if phases else None

        # --- Conditions ---
        conditions_module = protocol.get("conditionsModule", {})
        conditions = conditions_module.get("conditions", [])

        # --- Interventions ---
        arms_module = protocol.get("armsInterventionsModule", {})
        interventions_raw = arms_module.get("interventions", [])
        interventions = [
            {
                "name": i.get("name", ""),
                "type": i.get("type", ""),
            }
            for i in interventions_raw
        ]

        # --- Eligibility ---
        eligibility_module = protocol.get("eligibilityModule", {})

        # --- Sponsor ---
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        lead_sponsor = _safe_get(
            sponsor_module, "leadSponsor", "name", default=""
        )

        # --- Enrollment ---
        enrollment_info = design_module.get("enrollmentInfo", {})
        enrollment = enrollment_info.get("count")

        # --- Dates ---
        start_date = _safe_get(
            status_module, "startDateStruct", "date", default=""
        )
        completion_date = _safe_get(
            status_module, "completionDateStruct", "date", default=""
        )
        last_updated = _safe_get(
            status_module, "lastUpdatePostDateStruct", "date", default=""
        )

        # --- Locations ---
        contacts_module = protocol.get("contactsLocationsModule", {})
        locations_raw = contacts_module.get("locations", [])
        locations = [
            {
                "facility": loc.get("facility", ""),
                "city": loc.get("city", ""),
                "country": loc.get("country", ""),
            }
            for loc in locations_raw[:10]  # Limit to 10 locations
        ]

        # --- Build the result ---
        return {
            "nct_id": nct_id,
            "title": id_module.get("briefTitle", "Untitled"),
            "brief_summary": desc_module.get("briefSummary", ""),
            "detailed_description": desc_module.get("detailedDescription", ""),
            "status": status_module.get("overallStatus", "Unknown"),
            "phase": phase,
            "conditions": conditions,
            "interventions": interventions,
            "eligibility_criteria": eligibility_module.get(
                "eligibilityCriteria", ""
            ),
            "sponsor": lead_sponsor,
            "enrollment": enrollment,
            "start_date": start_date,
            "completion_date": completion_date,
            "locations": locations,
            "url": f"https://clinicaltrials.gov/study/{nct_id}",
            "last_updated": last_updated,
        }

    except Exception as e:
        logger.error(f"Error parsing study: {e}")
        return None


def parse_api_response(api_response: dict) -> list[dict]:
    """
    Parse the full API response containing multiple studies.

    Args:
        api_response: Raw JSON from the ClinicalTrials.gov API

    Returns:
        List of parsed study dictionaries ready for database insertion
    """
    studies = api_response.get("studies", [])
    parsed = []

    for study in studies:
        result = parse_study(study)
        if result:
            parsed.append(result)

    logger.info(f"Successfully parsed {len(parsed)}/{len(studies)} studies")
    return parsed
