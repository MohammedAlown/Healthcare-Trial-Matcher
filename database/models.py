"""
models.py - SQLAlchemy Database Models

Each class here maps to a PostgreSQL table.
Columns are defined as class attributes using SQLAlchemy's Column() type.

These are different from Pydantic models (schemas.py):
  - Pydantic models = shape of API requests/responses (JSON)
  - SQLAlchemy models = shape of database tables (SQL rows)
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float,
    DateTime, Boolean, JSON, Enum
)
from sqlalchemy.sql import func
import enum

from database.connection import Base


class TrialStatus(str, enum.Enum):
    """Possible statuses for a clinical trial."""
    RECRUITING = "Recruiting"
    ACTIVE = "Active, not recruiting"
    COMPLETED = "Completed"
    WITHDRAWN = "Withdrawn"
    SUSPENDED = "Suspended"
    TERMINATED = "Terminated"
    UNKNOWN = "Unknown"


class ClinicalTrial(Base):
    """
    Stores clinical trial data from ClinicalTrials.gov.

    Each row = one clinical trial.
    The nct_id is the unique identifier from ClinicalTrials.gov (e.g. NCT04012345).
    """
    __tablename__ = "clinical_trials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nct_id = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    brief_summary = Column(Text)
    detailed_description = Column(Text)
    status = Column(String(50), default="Unknown")
    phase = Column(String(50))
    conditions = Column(JSON)           # List of conditions (stored as JSON array)
    interventions = Column(JSON)        # List of interventions
    eligibility_criteria = Column(Text)
    sponsor = Column(String(500))
    enrollment = Column(Integer)
    start_date = Column(String(50))
    completion_date = Column(String(50))
    locations = Column(JSON)            # List of study locations
    url = Column(String(500))
    last_updated = Column(String(50))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_embedded = Column(Boolean, default=False)  # True after vector embedding is generated

    def __repr__(self):
        return f"<ClinicalTrial(nct_id='{self.nct_id}', title='{self.title[:50]}...')>"


class PubMedArticle(Base):
    """
    Stores research articles from PubMed.

    Each row = one published paper.
    The pmid is PubMed's unique article identifier.
    """
    __tablename__ = "pubmed_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pmid = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    authors = Column(JSON)              # List of author names
    journal = Column(String(500))
    publication_date = Column(String(50))
    doi = Column(String(200))
    keywords = Column(JSON)             # List of keywords
    mesh_terms = Column(JSON)           # Medical Subject Headings
    url = Column(String(500))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_embedded = Column(Boolean, default=False)

    def __repr__(self):
        return f"<PubMedArticle(pmid='{self.pmid}', title='{self.title[:50]}...')>"


class AuditLog(Base):
    """
    Tracks all important actions for governance and compliance.

    Every search, data ingestion, and system event gets logged here.
    This supports the project's governance requirement.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(100), nullable=False, index=True)   # e.g. "search", "ingest", "embed"
    entity_type = Column(String(50))     # e.g. "clinical_trial", "pubmed_article"
    entity_id = Column(String(50))       # e.g. NCT ID or PMID
    details = Column(JSON)               # Any extra info about the action
    user_id = Column(String(100))        # Who performed the action
    ip_address = Column(String(50))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', entity='{self.entity_type}:{self.entity_id}')>"
