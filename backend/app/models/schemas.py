"""
schemas.py - Pydantic Models (Request/Response Schemas)

Pydantic models define the SHAPE of data going in and out of the API.
FastAPI uses these to:
  1. Validate incoming request data automatically
  2. Serialize outgoing responses to JSON
  3. Generate OpenAPI documentation
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ============================================================
# Health Check
# ============================================================

class HealthResponse(BaseModel):
    """Response for the /health endpoint."""
    status: str = Field(
        ..., 
        description="Service status", 
        examples=["healthy"]
    )
    app_name: str = Field(
        ..., 
        description="Application name"
    )
    version: str = Field(
        ..., 
        description="Application version"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Server timestamp"
    )


# ============================================================
# Patient / Query
# ============================================================

class PatientQuery(BaseModel):
    """
    Input from a user describing a patient's condition.
    This is what gets sent to the RAG engine to find matching trials.
    """
    condition: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Patient medical condition or diagnosis",
        examples=["Stage 3 non-small cell lung cancer"]
    )
    age: Optional[int] = Field(
        None,
        ge=0,
        le=120,
        description="Patient age in years"
    )
    gender: Optional[str] = Field(
        None,
        description="Patient gender",
        examples=["male", "female"]
    )
    location: Optional[str] = Field(
        None,
        description="Patient location / preferred trial region",
        examples=["Riyadh, Saudi Arabia"]
    )
    keywords: Optional[list[str]] = Field(
        None,
        description="Additional search keywords",
        examples=[["immunotherapy", "pembrolizumab"]]
    )


# ============================================================
# Trial Match Result
# ============================================================

class TrialMatch(BaseModel):
    """A single clinical trial that matched the patient query."""
    trial_id: str = Field(
        ...,
        description="ClinicalTrials.gov NCT ID",
        examples=["NCT04012345"]
    )
    title: str = Field(
        ...,
        description="Trial title"
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Match relevance score (0 to 1)"
    )
    match_explanation: str = Field(
        ...,
        description="Why this trial matched the patient"
    )
    status: Optional[str] = Field(
        None,
        description="Trial recruitment status",
        examples=["Recruiting"]
    )


class MatchResponse(BaseModel):
    """Response containing all matched trials for a patient query."""
    query: str = Field(
        ...,
        description="Original patient condition query"
    )
    matches: list[TrialMatch] = Field(
        default_factory=list,
        description="List of matched clinical trials"
    )
    total_matches: int = Field(
        ...,
        ge=0,
        description="Total number of matches found"
    )
    search_time_ms: float = Field(
        ...,
        description="Search duration in milliseconds"
    )
