"""
contracts.py — Pydantic Contracts for Schema Validation

These enforce data shape at EVERY layer boundary:
  - Ingestion: validates raw API data before storage
  - Bronze: validates raw records
  - Silver: validates cleaned records
  - Gold: validates enriched records
  - API: validates request/response payloads

If data doesn't match the contract, it's rejected with
a clear validation error — not silently stored broken.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


# ============================================================
# Bronze Layer Contracts (Raw Data)
# ============================================================

class BronzeTrialContract(BaseModel):
    """Schema contract for raw clinical trial data entering bronze layer."""
    nct_id: str = Field(..., min_length=3, pattern=r"^NCT\d+$")
    title: str = Field(..., min_length=1)
    brief_summary: Optional[str] = None
    detailed_description: Optional[str] = None
    status: Optional[str] = None
    phase: Optional[str] = None
    conditions: Optional[list] = None
    interventions: Optional[list] = None
    eligibility_criteria: Optional[str] = None
    sponsor: Optional[str] = None
    enrollment: Optional[int] = None
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    locations: Optional[list] = None
    url: Optional[str] = None
    last_updated: Optional[str] = None

    class Config:
        extra = "allow"  # Allow extra fields in raw data


class BronzeArticleContract(BaseModel):
    """Schema contract for raw PubMed article data entering bronze layer."""
    pmid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    abstract: Optional[str] = None
    authors: Optional[list] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    keywords: Optional[list] = None
    mesh_terms: Optional[list] = None
    url: Optional[str] = None

    class Config:
        extra = "allow"


# ============================================================
# Silver Layer Contracts (Cleaned Data)
# ============================================================

VALID_STATUSES = [
    "Recruiting", "Completed", "Active, not recruiting",
    "Withdrawn", "Terminated", "Suspended", "Unknown",
    "Not yet recruiting", "Enrolling by invitation",
]

class SilverTrialContract(BaseModel):
    """Schema contract for cleaned trial data in silver layer."""
    nct_id: str = Field(..., pattern=r"^NCT\d+$")
    title: str = Field(..., min_length=1, max_length=2000)
    brief_summary: str = Field(default="")
    status: str = Field(default="Unknown")
    phase: Optional[str] = None
    conditions: list[str] = Field(default_factory=list)
    sponsor: str = Field(default="")
    enrollment: Optional[int] = Field(default=None, ge=0)
    url: str = Field(default="")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            return "Unknown"
        return v

    @field_validator("title")
    @classmethod
    def clean_title(cls, v):
        return " ".join(v.strip().split())


class SilverArticleContract(BaseModel):
    """Schema contract for cleaned PubMed article in silver layer."""
    pmid: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=2000)
    abstract: str = Field(default="")
    authors: list[str] = Field(default_factory=list)
    journal: str = Field(default="")
    publication_date: str = Field(default="")
    doi: str = Field(default="")
    keywords: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    url: str = Field(default="")

    @field_validator("title")
    @classmethod
    def clean_title(cls, v):
        return " ".join(v.strip().split())


# ============================================================
# Gold Layer Contracts (Enriched Data)
# ============================================================

class GoldRecordContract(BaseModel):
    """Schema contract for gold layer records ready for RAG."""
    source_id: str = Field(..., description="NCT ID or PMID")
    entity_type: str = Field(..., description="clinical_trial or pubmed_article")
    title: str = Field(..., min_length=1)
    search_text: str = Field(..., min_length=10, description="Combined searchable text")
    enriched_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = Field(default_factory=dict)

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v):
        allowed = ["clinical_trial", "pubmed_article", "document"]
        if v not in allowed:
            raise ValueError(f"entity_type must be one of {allowed}")
        return v


# ============================================================
# Kafka Message Contract
# ============================================================

class KafkaMessageContract(BaseModel):
    """Schema contract for Kafka messages."""
    topic: str = Field(...)
    key: str = Field(...)
    value: dict = Field(...)
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())


# ============================================================
# Validation Helpers
# ============================================================

def validate_bronze_trial(data: dict) -> tuple[bool, Optional[str]]:
    """Validate a trial record against bronze contract."""
    try:
        BronzeTrialContract(**data)
        return True, None
    except Exception as e:
        return False, str(e)


def validate_bronze_article(data: dict) -> tuple[bool, Optional[str]]:
    """Validate an article record against bronze contract."""
    try:
        BronzeArticleContract(**data)
        return True, None
    except Exception as e:
        return False, str(e)


def validate_silver_trial(data: dict) -> tuple[bool, Optional[str]]:
    """Validate a trial against silver contract."""
    try:
        SilverTrialContract(**data)
        return True, None
    except Exception as e:
        return False, str(e)


def validate_silver_article(data: dict) -> tuple[bool, Optional[str]]:
    """Validate an article against silver contract."""
    try:
        SilverArticleContract(**data)
        return True, None
    except Exception as e:
        return False, str(e)


def validate_gold_record(data: dict) -> tuple[bool, Optional[str]]:
    """Validate a record against gold contract."""
    try:
        GoldRecordContract(**data)
        return True, None
    except Exception as e:
        return False, str(e)
