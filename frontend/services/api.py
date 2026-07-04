"""
api.py — API Client Service

All communication between Streamlit and FastAPI goes through here.
The frontend NEVER accesses the database directly.
Every function maps to a FastAPI endpoint.
"""

import requests
from typing import Optional

# FastAPI backend URL
API_BASE = "http://localhost:8000"
TIMEOUT = 60  # seconds


def check_health() -> dict:
    """GET /health — Check if the API is running."""
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        return resp.json()
    except Exception:
        return {"status": "offline", "database": "unknown"}


def get_stats() -> dict:
    """GET /trials/stats — Get database statistics."""
    try:
        resp = requests.get(f"{API_BASE}/trials/stats", timeout=10)
        return resp.json()
    except Exception:
        return {"clinical_trials": 0, "pubmed_articles": 0, "documents": 0, "document_chunks": 0}


def match_trials(condition: str, age: int = None, gender: str = None,
                 location: str = None, keywords: list = None) -> dict:
    """POST /trials/match — Match patient to clinical trials."""
    payload = {"condition": condition}
    if age:
        payload["age"] = age
    if gender:
        payload["gender"] = gender
    if location:
        payload["location"] = location
    if keywords:
        payload["keywords"] = keywords
    try:
        resp = requests.post(f"{API_BASE}/trials/match", json=payload, timeout=TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "matches": [], "total_matches": 0}


def list_trials(skip: int = 0, limit: int = 20, status: str = None) -> dict:
    """GET /trials/list — List trials from database."""
    params = {"skip": skip, "limit": limit}
    if status:
        params["status"] = status
    try:
        resp = requests.get(f"{API_BASE}/trials/list", params=params, timeout=10)
        return resp.json()
    except Exception:
        return {"trials": [], "total": 0}


def get_trial(trial_id: str) -> dict:
    """GET /trials/{trial_id} — Get trial details."""
    try:
        resp = requests.get(f"{API_BASE}/trials/{trial_id}", timeout=10)
        return resp.json()
    except Exception:
        return {"error": "Not found"}


def ingest_trials(condition: str, max_results: int = 50) -> dict:
    """POST /ingest/trials — Ingest from ClinicalTrials.gov."""
    try:
        resp = requests.post(f"{API_BASE}/ingest/trials",
                             params={"condition": condition, "max_results": max_results},
                             timeout=TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def ingest_pubmed(query: str, max_results: int = 20) -> dict:
    """POST /ingest/pubmed — Ingest from PubMed."""
    try:
        resp = requests.post(f"{API_BASE}/ingest/pubmed",
                             params={"query": query, "max_results": max_results},
                             timeout=TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def run_pipeline() -> dict:
    """POST /pipeline/run — Run the full data pipeline."""
    try:
        resp = requests.post(f"{API_BASE}/pipeline/run", timeout=120)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def get_pipeline_stats() -> dict:
    """GET /pipeline/stats — Get pipeline statistics."""
    try:
        resp = requests.get(f"{API_BASE}/pipeline/stats", timeout=10)
        return resp.json()
    except Exception:
        return {}
