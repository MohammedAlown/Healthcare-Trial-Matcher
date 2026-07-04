"""
Cross-Encoder Reranker — Second-stage ranking for better precision.

Two-stage search pipeline:
  Stage 1: Hybrid search (fast, retrieves candidates)
  Stage 2: Cross-encoder reranking (slow but accurate, reorders candidates)

Cross-encoders are more accurate than bi-encoders because they
see the query AND document together, not separately.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
"""

from sentence_transformers import CrossEncoder
from backend.app.core.logger import logger

_reranker = None

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logger.info("Cross-encoder reranker loaded")
    return _reranker


def rerank(query: str, results: list[dict], top_k: int = 10) -> list[dict]:
    """
    Rerank search results using a cross-encoder.

    Args:
        query: Original search query
        results: Candidate results from hybrid search
        top_k: Number of top results to return

    Returns:
        Reranked results with updated scores
    """
    if not results:
        return []

    reranker = get_reranker()

    # Build query-document pairs for the cross-encoder
    pairs = []
    for r in results:
        doc_text = r.get("title", "") + " " + r.get("brief_summary", r.get("abstract", ""))
        pairs.append([query, doc_text[:512]])  # Truncate to model max

    # Get cross-encoder scores
    scores = reranker.predict(pairs)

    # Attach reranker scores
    for i, r in enumerate(results):
        r["rerank_score"] = float(scores[i])

    # Sort by reranker score
    reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
    logger.info(f"Reranked {len(results)} results, returning top {top_k}")

    return reranked[:top_k]
