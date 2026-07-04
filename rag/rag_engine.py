"""
RAG Engine — Retrieval-Augmented Generation Pipeline

The complete pipeline:
  1. User sends patient query
  2. Hybrid search retrieves candidate trials/articles
  3. Cross-encoder reranks for precision
  4. LLM (Groq/LLaMA) generates explanations with citations
  5. Response includes matched trials + why they matched

This is the core intelligence of the system.
"""

import time
from sqlalchemy.orm import Session
from groq import Groq
from backend.app.core.config import settings
from backend.app.core.logger import logger
from rag.hybrid_search import hybrid_search
from rag.reranker import rerank


def build_context(results: list[dict]) -> str:
    """Build context string from search results for the LLM."""
    context_parts = []
    for i, r in enumerate(results[:5], 1):
        title = r.get("title", "Unknown")
        entity = r.get("entity_type", "unknown")
        nct_id = r.get("nct_id", r.get("pmid", "N/A"))
        summary = r.get("brief_summary", r.get("abstract", "No summary"))
        if summary and len(summary) > 300:
            summary = summary[:300] + "..."

        context_parts.append(
            f"[{i}] {entity.upper()}: {title}\n"
            f"    ID: {nct_id}\n"
            f"    Summary: {summary}\n"
        )
    return "\n".join(context_parts)


def generate_explanation(query: str, context: str, results: list[dict]) -> str:
    """Use Groq LLM to generate match explanations."""
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)

        prompt = f"""You are a clinical trial matching assistant. A patient has the following condition:

PATIENT QUERY: {query}

RETRIEVED CLINICAL DATA:
{context}

Based on the retrieved data, explain:
1. Which trials/articles are most relevant and why
2. How each match relates to the patient's condition
3. Key eligibility considerations

Provide citations using [1], [2], etc. referring to the retrieved data above.
Be concise and medically accurate."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3,
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.warning(f"LLM generation failed: {e}")
        # Fallback: generate basic explanation without LLM
        explanations = []
        for i, r in enumerate(results[:5], 1):
            explanations.append(
                f"[{i}] {r.get('title', 'Unknown')} — "
                f"Relevance score: {r.get('rerank_score', r.get('score', 0)):.2f}"
            )
        return "Matched trials (LLM unavailable, showing scores):\n" + "\n".join(explanations)


def rag_query(
    db: Session,
    patient_condition: str,
    age: int = None,
    gender: str = None,
    top_k: int = 5,
) -> dict:
    """
    Full RAG pipeline: search → rerank → generate.
    """
    start_time = time.time()
    logger.info(f"RAG query: '{patient_condition}'")

    # Build enhanced query
    query_parts = [patient_condition]
    if age:
        query_parts.append(f"age {age}")
    if gender:
        query_parts.append(gender)
    full_query = " ".join(query_parts)

    # Step 1: Hybrid search
    search_results = hybrid_search(db, full_query, limit=20)

    # Step 2: Rerank
    if search_results:
        reranked = rerank(patient_condition, search_results, top_k=top_k)
    else:
        reranked = []

    # Step 3: Build context and generate explanation
    context = build_context(reranked)
    explanation = generate_explanation(patient_condition, context, reranked)

    elapsed = time.time() - start_time

    return {
        "query": patient_condition,
        "matches": [
            {
                "title": r.get("title", ""),
                "id": r.get("nct_id", r.get("pmid", r.get("id", ""))),
                "entity_type": r.get("entity_type", ""),
                "score": round(r.get("rerank_score", r.get("score", 0)), 4),
                "sources": r.get("sources", []),
            }
            for r in reranked
        ],
        "explanation": explanation,
        "total_matches": len(reranked),
        "search_time_seconds": round(elapsed, 2),
    }
