"""
hybrid_search.py — Hybrid Search using BM25 + Vector + RRF

Two-stage retrieval:
  Stage 1a: BM25 keyword search (exact term matching)
  Stage 1b: Vector semantic search (meaning matching)
  Stage 2:  Reciprocal Rank Fusion to combine both

This is the proper hybrid search pipeline:
  BM25 results ──┐
                  ├── RRF Fusion → Ranked Results
  Vector results ─┘
"""

from sqlalchemy.orm import Session
from embeddings.embedding_service import generate_embedding
from rag.vector_store import search_vectors
from rag.bm25_search import bm25_index, BM25Index
from rag.rrf import reciprocal_rank_fusion
from backend.app.core.logger import logger


def hybrid_search(
    db: Session,
    query: str,
    limit: int = 20,
    rrf_k: int = 60,
) -> list[dict]:
    """
    Hybrid search combining BM25 + vector search + RRF fusion.

    Args:
        db: Database session
        query: Search query
        limit: Max results to return
        rrf_k: RRF constant

    Returns:
        Fused and ranked results
    """
    logger.info(f"Hybrid search: '{query}'")

    # --- BM25 keyword search ---
    bm25_index.build_from_db(db)
    bm25_results = bm25_index.search(query, top_k=limit)

    # --- Vector semantic search ---
    try:
        query_vector = generate_embedding(query)
        vector_results = search_vectors(query_vector, limit=limit)
        vector_results = [
            {
                "id": r["payload"].get("source_id", str(r["id"])),
                "entity_type": r["payload"].get("entity_type", "unknown"),
                "title": r["payload"].get("title", ""),
                "score": r["score"],
                "source": "vector",
                "brief_summary": r["payload"].get("brief_summary", ""),
                **{k: v for k, v in r["payload"].items()
                   if k not in ["title", "entity_type", "brief_summary"]},
            }
            for r in vector_results
        ]
    except Exception as e:
        logger.warning(f"Vector search failed: {e}")
        vector_results = []

    # --- RRF Fusion ---
    if bm25_results and vector_results:
        fused = reciprocal_rank_fusion(
            [bm25_results, vector_results],
            k=rrf_k,
            top_n=limit,
        )
    elif bm25_results:
        fused = bm25_results[:limit]
    elif vector_results:
        fused = vector_results[:limit]
    else:
        fused = []

    logger.info(
        f"Hybrid search: BM25={len(bm25_results)}, "
        f"Vector={len(vector_results)}, Fused={len(fused)}"
    )

    return fused
