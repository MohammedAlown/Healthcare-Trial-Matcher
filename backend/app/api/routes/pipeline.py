"""
pipeline.py — Pipeline API Endpoints

Trigger and monitor the full data pipeline from the API.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.connection import get_db
from backend.app.core.logger import logger

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.post(
    "/run",
    summary="Run Full Pipeline",
    description="Execute: Fetch → Contract → Kafka → Bronze → Silver → Gold → Embed → GE → Lineage",
)
async def run_pipeline():
    """Run the complete end-to-end pipeline."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    from pipeline.run_pipeline import run_full_pipeline
    result = run_full_pipeline()
    return result


@router.get(
    "/stats",
    summary="Pipeline Statistics",
)
async def pipeline_stats():
    """Get Delta lakehouse and pipeline stats."""
    from pipeline.lakehouse.delta_tables import get_delta_stats
    from rag.vector_store import get_collection_stats
    from pipeline.kafka.producer import InMemoryBus
    return {
        "delta_lakehouse": get_delta_stats(),
        "vector_store": get_collection_stats(),
        "kafka_topics": InMemoryBus.get_stats(),
    }
