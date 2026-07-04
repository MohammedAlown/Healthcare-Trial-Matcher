"""
Vector Store — Qdrant integration for semantic search.

Qdrant stores our embedding vectors and enables:
  - Semantic similarity search (find similar medical concepts)
  - Hybrid search (combine vector + keyword matching)
  - Filtered search (by status, phase, etc.)
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue,
)
from typing import Optional
from backend.app.core.logger import logger
from backend.app.core.config import settings

COLLECTION_NAME = "clinical_data"
VECTOR_SIZE = 384  # Matches all-MiniLM-L6-v2

_client = None

def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        try:
            _client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            logger.info("Connected to Qdrant")
        except Exception:
            _client = QdrantClient(":memory:")
            logger.warning("Qdrant not available, using in-memory mode")
    return _client


def init_collection():
    """Create the vector collection if it doesn't exist."""
    client = get_qdrant()
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Created collection: {COLLECTION_NAME}")


def upsert_vectors(points: list[dict]):
    """Insert or update vectors in Qdrant."""
    client = get_qdrant()
    init_collection()
    qdrant_points = [
        PointStruct(
            id=p["id"],
            vector=p["vector"],
            payload=p["payload"],
        )
        for p in points
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=qdrant_points)
    logger.info(f"Upserted {len(qdrant_points)} vectors")


def search_vectors(
    query_vector: list[float],
    limit: int = 10,
    score_threshold: float = 0.3,
    entity_type: Optional[str] = None,
) -> list[dict]:
    """
    Semantic search in Qdrant.

    Returns top matches ranked by cosine similarity.
    """
    client = get_qdrant()
    init_collection()

    query_filter = None
    if entity_type:
        query_filter = Filter(
            must=[FieldCondition(key="entity_type", match=MatchValue(value=entity_type))]
        )

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=limit,
        score_threshold=score_threshold,
        query_filter=query_filter,
    )

    return [
        {
            "id": r.id,
            "score": r.score,
            "payload": r.payload,
        }
        for r in results
    ]


def get_collection_stats() -> dict:
    """Get vector collection statistics."""
    client = get_qdrant()
    try:
        info = client.get_collection(COLLECTION_NAME)
        return {
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
        }
    except Exception:
        return {"vectors_count": 0, "points_count": 0}
