"""
pubmed_ingestion_service.py - PubMed Ingestion Pipeline

Orchestrates fetching, parsing, and storing PubMed articles:
  1. Search PubMed for PMIDs matching a query
  2. Fetch full article details for those PMIDs
  3. Parse the XML into flat dicts
  4. Store in PostgreSQL via CRUD layer
  5. Log everything for audit
"""

import time
from sqlalchemy.orm import Session

from backend.app.services.pubmed_client import search_pubmed, fetch_articles
from backend.app.services.pubmed_parser import parse_articles
from backend.app.core.logger import logger
from database import crud


async def ingest_pubmed_articles(
    db: Session,
    query: str,
    max_results: int = 20,
) -> dict:
    """
    Fetch, parse, and store PubMed articles for a search query.

    Args:
        db: Database session
        query: Search term (e.g. "lung cancer treatment")
        max_results: Maximum articles to fetch

    Returns:
        Summary dict with ingestion stats
    """
    start_time = time.time()
    logger.info(f"Starting PubMed ingestion for: '{query}'")

    stats = {
        "query": query,
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "failed": 0,
    }

    try:
        # Step 1: Search for PMIDs
        pmids = await search_pubmed(query, max_results=max_results)

        if not pmids:
            logger.warning(f"No PubMed results for: '{query}'")
            stats["elapsed_seconds"] = round(time.time() - start_time, 2)
            return stats

        # Step 2: Fetch full article details
        articles_raw = await fetch_articles(pmids)

        # Step 3: Parse articles
        parsed_articles = parse_articles(articles_raw)
        stats["fetched"] = len(parsed_articles)

        # Step 4: Store in database
        for article_data in parsed_articles:
            try:
                existing = crud.get_article_by_pmid(db, article_data["pmid"])

                if existing:
                    # Update existing article
                    for key, value in article_data.items():
                        setattr(existing, key, value)
                    db.commit()
                    stats["updated"] += 1
                else:
                    # Create new article
                    crud.create_article(db, article_data)
                    stats["created"] += 1

            except Exception as e:
                logger.error(
                    f"Failed to store article {article_data.get('pmid')}: {e}"
                )
                db.rollback()
                stats["failed"] += 1

        # Step 5: Audit log
        crud.create_audit_log(
            db=db,
            action="ingest_pubmed",
            entity_type="pubmed_article",
            details=stats,
            user_id="system",
        )

    except Exception as e:
        logger.error(f"PubMed ingestion failed for '{query}': {e}")
        stats["error"] = str(e)

    elapsed = time.time() - start_time
    stats["elapsed_seconds"] = round(elapsed, 2)

    logger.info(
        f"PubMed ingestion complete: {stats['created']} created, "
        f"{stats['updated']} updated, {stats['failed']} failed "
        f"in {elapsed:.2f}s"
    )

    return stats


async def ingest_pubmed_batch(
    db: Session,
    queries: list[str],
    max_per_query: int = 20,
) -> list[dict]:
    """
    Ingest PubMed articles for multiple search queries.

    Args:
        db: Database session
        queries: List of search terms
        max_per_query: Max articles per query

    Returns:
        List of stats dicts, one per query
    """
    logger.info(f"Starting batch PubMed ingestion for {len(queries)} queries")
    all_stats = []

    for query in queries:
        stats = await ingest_pubmed_articles(db, query, max_per_query)
        all_stats.append(stats)

    total_created = sum(s["created"] for s in all_stats)
    logger.info(f"Batch PubMed ingestion complete: {total_created} articles created")

    return all_stats
