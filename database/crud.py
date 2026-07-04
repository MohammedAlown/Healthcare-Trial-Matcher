"""
crud.py - Database CRUD Operations

CRUD = Create, Read, Update, Delete — the four basic database operations.
Each function takes a database session and performs one operation.

This layer sits BETWEEN the API routes and the raw database,
keeping the route code clean and the database logic reusable.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from database.models import ClinicalTrial, PubMedArticle, AuditLog
from backend.app.core.logger import logger


# ============================================================
# Clinical Trials
# ============================================================

def create_trial(db: Session, trial_data: dict) -> ClinicalTrial:
    """
    Insert a new clinical trial into the database.

    Args:
        db: Database session
        trial_data: Dictionary of trial fields

    Returns:
        The created ClinicalTrial object
    """
    trial = ClinicalTrial(**trial_data)
    db.add(trial)
    db.commit()
    db.refresh(trial)  # Reload from DB to get auto-generated fields (id, created_at)
    logger.info(f"Created trial: {trial.nct_id}")
    return trial


def get_trial_by_nct_id(db: Session, nct_id: str) -> Optional[ClinicalTrial]:
    """Fetch a single trial by its NCT ID."""
    return db.query(ClinicalTrial).filter(ClinicalTrial.nct_id == nct_id).first()


def get_trials(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
) -> list[ClinicalTrial]:
    """
    Fetch multiple trials with optional filtering.

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum records to return
        status: Filter by trial status (e.g. "Recruiting")
    """
    query = db.query(ClinicalTrial)
    if status:
        query = query.filter(ClinicalTrial.status == status)
    return query.offset(skip).limit(limit).all()


def count_trials(db: Session) -> int:
    """Return total number of trials in the database."""
    return db.query(func.count(ClinicalTrial.id)).scalar()


def upsert_trial(db: Session, trial_data: dict) -> ClinicalTrial:
    """
    Insert or update a trial. If nct_id already exists, update it.
    'Upsert' = Update + Insert.
    """
    existing = get_trial_by_nct_id(db, trial_data.get("nct_id", ""))
    if existing:
        for key, value in trial_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        logger.info(f"Updated trial: {existing.nct_id}")
        return existing
    return create_trial(db, trial_data)


# ============================================================
# PubMed Articles
# ============================================================

def create_article(db: Session, article_data: dict) -> PubMedArticle:
    """Insert a new PubMed article."""
    article = PubMedArticle(**article_data)
    db.add(article)
    db.commit()
    db.refresh(article)
    logger.info(f"Created article: {article.pmid}")
    return article


def get_article_by_pmid(db: Session, pmid: str) -> Optional[PubMedArticle]:
    """Fetch a single article by PubMed ID."""
    return db.query(PubMedArticle).filter(PubMedArticle.pmid == pmid).first()


def get_articles(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> list[PubMedArticle]:
    """Fetch multiple articles with pagination."""
    return db.query(PubMedArticle).offset(skip).limit(limit).all()


def count_articles(db: Session) -> int:
    """Return total number of articles in the database."""
    return db.query(func.count(PubMedArticle.id)).scalar()


# ============================================================
# Audit Logs
# ============================================================

def create_audit_log(
    db: Session,
    action: str,
    entity_type: str = None,
    entity_id: str = None,
    details: dict = None,
    user_id: str = "system",
) -> AuditLog:
    """
    Record an action in the audit log.
    Used for governance — tracking who did what and when.
    """
    log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        user_id=user_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_audit_logs(
    db: Session,
    action: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[AuditLog]:
    """Fetch audit logs with optional action filter."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
