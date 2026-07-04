"""
run_pipeline.py — End-to-End Pipeline Runner

Runs the complete pipeline either standalone or as Airflow tasks.
Each step is wired to actually call the real modules.

Pipeline flow:
  1. Fetch data (ClinicalTrials.gov + PubMed)
  2. Validate with Pydantic contracts
  3. Publish to Kafka (with schema validation)
  4. Write to Delta Bronze layer
  5. Transform: Delta Silver (clean + MERGE)
  6. Enrich: Delta Gold (search_text + metadata)
  7. Generate embeddings + upsert to Qdrant
  8. Run Great Expectations validation suite
  9. Emit OpenLineage lineage events
"""

import sys
import os
import json
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.core.logger import logger
from backend.app.models.contracts import (
    validate_bronze_trial, validate_bronze_article,
    validate_silver_trial, validate_gold_record,
)
from pipeline.kafka.producer import KafkaProducer, InMemoryBus
from pipeline.kafka.consumer import KafkaConsumer
from pipeline.lakehouse.delta_tables import delta_write, delta_merge, get_delta_stats
from validation.expectations import validate_bronze, validate_silver, validate_gold
from validation.lineage import track_ingestion, track_transformation, track_enrichment
from datetime import datetime


def step_1_fetch_data():
    """Fetch raw data from APIs."""
    from backend.app.services.clinicaltrials_client import fetch_trials
    from backend.app.services.clinicaltrials_parser import parse_api_response
    from backend.app.services.pubmed_client import search_pubmed, fetch_articles
    from backend.app.services.pubmed_parser import parse_articles

    logger.info("=" * 50)
    logger.info("STEP 1: Fetching data from APIs")

    conditions = ["lung cancer", "diabetes"]
    all_trials = []
    for cond in conditions:
        resp = asyncio.run(fetch_trials(cond, max_results=10))
        parsed = parse_api_response(resp)
        all_trials.extend(parsed)
    logger.info(f"Fetched {len(all_trials)} trials")

    all_articles = []
    for query in ["lung cancer treatment"]:
        pmids = asyncio.run(search_pubmed(query, max_results=5))
        raw = asyncio.run(fetch_articles(pmids))
        parsed = parse_articles(raw)
        all_articles.extend(parsed)
    logger.info(f"Fetched {len(all_articles)} articles")

    return all_trials, all_articles


def step_2_validate_contracts(trials, articles):
    """Validate data against Pydantic contracts."""
    logger.info("=" * 50)
    logger.info("STEP 2: Pydantic contract validation")

    valid_trials = []
    for t in trials:
        ok, err = validate_bronze_trial(t)
        if ok:
            valid_trials.append(t)
        else:
            logger.warning(f"Contract rejected trial: {err}")

    valid_articles = []
    for a in articles:
        ok, err = validate_bronze_article(a)
        if ok:
            valid_articles.append(a)
        else:
            logger.warning(f"Contract rejected article: {err}")

    logger.info(f"Contracts: {len(valid_trials)}/{len(trials)} trials, "
                f"{len(valid_articles)}/{len(articles)} articles passed")
    return valid_trials, valid_articles


def step_3_kafka_publish(trials, articles):
    """Publish to Kafka with schema validation."""
    logger.info("=" * 50)
    logger.info("STEP 3: Kafka publish (with schema validation)")

    producer = KafkaProducer()
    producer.connect()

    for t in trials:
        producer.produce("clinical-trials", t.get("nct_id", ""), t)
    for a in articles:
        producer.produce("pubmed-articles", a.get("pmid", ""), a)

    stats = InMemoryBus.get_stats()
    logger.info(f"Kafka stats: {stats}")
    return stats


def step_4_delta_bronze(trials, articles):
    """Write to Delta Bronze layer."""
    logger.info("=" * 50)
    logger.info("STEP 4: Delta Bronze (raw storage)")

    t_result = delta_write("clinical_trials", "bronze", trials, mode="append")
    a_result = delta_write("pubmed_articles", "bronze", articles, mode="append")

    track_ingestion("clinicaltrials.gov", "clinical_trials", len(trials))
    track_ingestion("pubmed", "pubmed_articles", len(articles))

    return t_result, a_result


def step_5_delta_silver(trials, articles):
    """MERGE into Delta Silver layer (clean + deduplicate)."""
    logger.info("=" * 50)
    logger.info("STEP 5: Delta Silver (MERGE + clean)")

    t_result = delta_merge("clinical_trials", "silver", trials, merge_key="nct_id")
    a_result = delta_merge("pubmed_articles", "silver", articles, merge_key="pmid")

    track_transformation("clinical_trials", len(trials), t_result["total"])
    track_transformation("pubmed_articles", len(articles), a_result["total"])

    return t_result, a_result


def step_6_delta_gold(trials, articles):
    """Enrich and write to Delta Gold layer."""
    logger.info("=" * 50)
    logger.info("STEP 6: Delta Gold (enrich)")

    gold_records = []
    for t in trials:
        parts = [t.get("title", ""), t.get("brief_summary", ""), t.get("eligibility_criteria", "")]
        conditions = t.get("conditions", [])
        if isinstance(conditions, list):
            parts.extend(conditions)
        gold_records.append({
            **t,
            "source_id": t.get("nct_id", ""),
            "entity_type": "clinical_trial",
            "search_text": " ".join(p for p in parts if p),
            "enriched_at": datetime.utcnow().isoformat(),
        })

    for a in articles:
        gold_records.append({
            **a,
            "source_id": a.get("pmid", ""),
            "entity_type": "pubmed_article",
            "search_text": f"{a.get('title', '')} {a.get('abstract', '')}",
            "enriched_at": datetime.utcnow().isoformat(),
        })

    t_result = delta_write("clinical_trials", "gold", [r for r in gold_records if r["entity_type"] == "clinical_trial"])
    a_result = delta_write("pubmed_articles", "gold", [r for r in gold_records if r["entity_type"] == "pubmed_article"])

    track_enrichment("clinical_trials", len(trials))
    track_enrichment("pubmed_articles", len(articles))

    return gold_records


def step_7_embed_and_index(gold_records):
    """Generate embeddings and upsert to Qdrant."""
    logger.info("=" * 50)
    logger.info("STEP 7: Embeddings + Qdrant indexing")

    from embeddings.embedding_service import generate_embeddings_batch
    from rag.vector_store import upsert_vectors, init_collection

    init_collection()

    texts = [r["search_text"][:500] for r in gold_records[:30]]
    if not texts:
        return

    embeddings = generate_embeddings_batch(texts)
    points = []
    for i, (rec, emb) in enumerate(zip(gold_records[:30], embeddings)):
        points.append({
            "id": abs(hash(rec["source_id"])) % (2**63),
            "vector": emb,
            "payload": {
                "source_id": rec["source_id"],
                "entity_type": rec["entity_type"],
                "title": rec.get("title", ""),
                "brief_summary": rec.get("brief_summary", rec.get("abstract", ""))[:500],
                "status": rec.get("status", ""),
            },
        })
    upsert_vectors(points)
    logger.info(f"Indexed {len(points)} vectors in Qdrant")


def step_8_great_expectations(trials, articles, gold_records):
    """Run Great Expectations validation suite."""
    logger.info("=" * 50)
    logger.info("STEP 8: Great Expectations validation")

    bronze_trial_report = validate_bronze(trials, "clinical_trials")
    bronze_article_report = validate_bronze(articles, "pubmed_articles")
    silver_trial_report = validate_silver(trials, "clinical_trials")
    gold_report = validate_gold(
        [r for r in gold_records if "search_text" in r],
        "clinical_trials",
    )

    reports = [bronze_trial_report, bronze_article_report, silver_trial_report, gold_report]
    for r in reports:
        status = "PASSED" if r["failed"] == 0 else "FAILED"
        logger.info(f"  GE Suite '{r['suite']}': {status} ({r['passed']}/{r['total_expectations']})")

    return reports


def step_9_openlineage():
    """Emit final OpenLineage events."""
    logger.info("=" * 50)
    logger.info("STEP 9: OpenLineage lineage events")
    from validation.lineage import lineage

    lineage.emit_event(
        job_name="full_pipeline",
        event_type="COMPLETE",
        inputs=[
            {"name": "clinicaltrials.gov"},
            {"name": "pubmed"},
        ],
        outputs=[
            {"name": "delta.gold.clinical_trials"},
            {"name": "delta.gold.pubmed_articles"},
            {"name": "qdrant.clinical_data"},
        ],
        run_facets={"pipeline_version": "1.0.0"},
    )
    logger.info("OpenLineage events emitted")


def run_full_pipeline():
    """Execute all pipeline steps in order."""
    start = time.time()
    logger.info("=" * 60)
    logger.info("STARTING FULL PIPELINE")
    logger.info("=" * 60)

    # Step 1: Fetch
    trials, articles = step_1_fetch_data()

    # Step 2: Pydantic contracts
    trials, articles = step_2_validate_contracts(trials, articles)

    # Step 3: Kafka
    step_3_kafka_publish(trials, articles)

    # Step 4: Delta Bronze
    step_4_delta_bronze(trials, articles)

    # Step 5: Delta Silver (MERGE)
    step_5_delta_silver(trials, articles)

    # Step 6: Delta Gold
    gold_records = step_6_delta_gold(trials, articles)

    # Step 7: Embeddings + Qdrant
    step_7_embed_and_index(gold_records)

    # Step 8: Great Expectations
    ge_reports = step_8_great_expectations(trials, articles, gold_records)

    # Step 9: OpenLineage
    step_9_openlineage()

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE in {elapsed:.1f}s")
    logger.info(f"Delta stats: {get_delta_stats()}")
    logger.info("=" * 60)

    return {
        "trials_processed": len(trials),
        "articles_processed": len(articles),
        "gold_records": len(gold_records),
        "ge_reports": len(ge_reports),
        "elapsed_seconds": round(elapsed, 1),
    }


if __name__ == "__main__":
    run_full_pipeline()
