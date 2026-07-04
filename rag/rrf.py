"""
rrf.py — Reciprocal Rank Fusion (RRF)

RRF combines results from multiple search methods
(BM25 + vector search) into a single ranked list.

Formula: RRF_score(d) = Σ 1 / (k + rank_i(d))

Where:
  - d = document
  - k = constant (typically 60)
  - rank_i(d) = rank of document d in the i-th result list

Why RRF over simple score averaging?
  - Scores from different systems aren't comparable (BM25 vs cosine)
  - RRF uses RANKS instead of scores, making it system-agnostic
  - Proven to outperform score-based fusion in IR research
"""

from backend.app.core.logger import logger


def reciprocal_rank_fusion(
    result_lists: list[list[dict]],
    k: int = 60,
    top_n: int = 20,
    id_key: str = "id",
) -> list[dict]:
    """
    Fuse multiple ranked result lists using RRF.

    Args:
        result_lists: List of ranked result lists
                      (e.g., [bm25_results, vector_results])
        k: RRF constant (default 60, per original paper)
        top_n: Number of results to return
        id_key: Key used to identify unique documents

    Returns:
        Fused and re-ranked results with RRF scores
    """
    # Calculate RRF scores
    rrf_scores: dict[str, float] = {}
    doc_data: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, doc in enumerate(result_list, start=1):
            doc_id = doc.get(id_key, str(rank))

            # RRF formula: 1 / (k + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

            # Keep the richest version of the document data
            if doc_id not in doc_data or len(str(doc)) > len(str(doc_data[doc_id])):
                doc_data[doc_id] = doc.copy()

    # Build final ranked list
    fused_results = []
    for doc_id, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        doc = doc_data[doc_id]
        doc["rrf_score"] = round(score, 6)
        doc["id"] = doc_id

        # Collect which sources contributed
        sources = set(doc.get("sources", []))
        if "source" in doc:
            sources.add(doc["source"])
        doc["sources"] = list(sources)

        fused_results.append(doc)

    logger.info(
        f"RRF fusion: {len(result_lists)} lists → "
        f"{len(fused_results)} unique docs → returning top {top_n}"
    )

    return fused_results[:top_n]
