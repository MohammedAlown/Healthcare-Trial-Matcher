"""
Hybrid Search — Combines vector (semantic) + keyword search.

Why hybrid?
  - Vector search: finds semantically similar content
    ("lung cancer" matches "NSCLC", "pulmonary carcinoma")
  - Keyword search: finds exact matches
    ("NCT04012345", "pembrolizumab")

Combining both gives better results than either alone.
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from database.models import ClinicalTrial, PubMedArticle
from embeddings.embedding_service import generate_embedding
from rag.vector_store import search_vectors
from backend.app.core.logger import logger


def keyword_search(db: Session, query: str, limit: int = 20) -> list[dict]:
    """Search PostgreSQL using keyword matching (SQL ILIKE)."""
    search_term = f"%{query}%"

    trials = db.query(ClinicalTrial).filter(
        or_(
            ClinicalTrial.title.ilike(search_term),
            ClinicalTrial.brief_summary.ilike(search_term),
            ClinicalTrial.eligibility_criteria.ilike(search_term),
        )
    ).limit(limit).all()

    articles = db.query(PubMedArticle).filter(
        or_(
            PubMedArticle.title.ilike(search_term),
            PubMedArticle.abstract.ilike(search_term),
        )
    ).limit(limit).all()

    results = []
    for t in trials:
        results.append({
            "id": f"trial_{t.nct_id}",
            "entity_type": "clinical_trial",
            "title": t.title,
            "nct_id": t.nct_id,
            "score": 0.5,
            "source": "keyword",
        })
    for a in articles:
        results.append({
            "id": f"article_{a.pmid}",
            "entity_type": "pubmed_article",
            "title": a.title,
            "pmid": a.pmid,
            "score": 0.5,
            "source": "keyword",
        })

    return results


def semantic_search(query: str, limit: int = 10) -> list[dict]:
    """Search Qdrant using vector similarity."""
    query_vector = generate_embedding(query)
    results = search_vectors(query_vector, limit=limit)

    return [
        {
            "id": r["payload"].get("source_id", str(r["id"])),
            "entity_type": r["payload"].get("entity_type", "unknown"),
            "title": r["payload"].get("title", ""),
            "score": r["score"],
            "source": "semantic",
            **{k: v for k, v in r["payload"].items() if k not in ["title", "entity_type"]},
        }
        for r in results
    ]


def hybrid_search(
    db: Session,
    query: str,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    limit: int = 20,
) -> list[dict]:
    """
    Combine semantic + keyword search with weighted scoring.

    Hybrid scoring: final_score = (semantic_weight * vector_score) + (keyword_weight * keyword_score)
    """
    logger.info(f"Hybrid search: '{query}' (semantic={semantic_weight}, keyword={keyword_weight})")

    # Get results from both sources
    semantic_results = semantic_search(query, limit=limit)
    keyword_results = keyword_search(db, query, limit=limit)

    # Merge results by ID
    merged = {}

    for r in semantic_results:
        rid = r["id"]
        merged[rid] = r.copy()
        merged[rid]["score"] = r["score"] * semantic_weight
        merged[rid]["sources"] = ["semantic"]

    for r in keyword_results:
        rid = r["id"]
        if rid in merged:
            merged[rid]["score"] += r["score"] * keyword_weight
            merged[rid]["sources"].append("keyword")
        else:
            merged[rid] = r.copy()
            merged[rid]["score"] = r["score"] * keyword_weight
            merged[rid]["sources"] = ["keyword"]

    # Sort by combined score
    results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
    logger.info(f"Hybrid search returned {len(results)} results")

    return results[:limit]
