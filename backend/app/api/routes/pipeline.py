"""
pipeline.py — Pipeline API Endpoints
"""

from fastapi import APIRouter
from backend.app.core.logger import logger
from backend.app.services.clinicaltrials_client import fetch_trials
from backend.app.services.clinicaltrials_parser import parse_api_response
from backend.app.services.pubmed_client import search_pubmed, fetch_articles
from backend.app.services.pubmed_parser import parse_articles
from backend.app.models.contracts import validate_bronze_trial, validate_bronze_article
from pipeline.kafka.producer import KafkaProducer, InMemoryBus
from pipeline.lakehouse.delta_tables import delta_write, delta_merge, get_delta_stats
from validation.expectations import validate_bronze, validate_silver, validate_gold
from validation.lineage import track_ingestion, track_transformation, track_enrichment, lineage
from datetime import datetime
import time

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.post("/run", summary="Run Full Pipeline",
    description="Execute: Fetch → Contract → Kafka → Bronze → Silver → Gold → Embed → GE → Lineage")
async def run_pipeline():
    start = time.time()
    logger.info("STARTING FULL PIPELINE")

    # Step 1: Fetch
    conditions = ["lung cancer", "diabetes"]
    all_trials = []
    for cond in conditions:
        resp = await fetch_trials(cond, max_results=10)
        parsed = parse_api_response(resp)
        all_trials.extend(parsed)

    all_articles = []
    pmids = await search_pubmed("lung cancer treatment", max_results=5)
    raw = await fetch_articles(pmids)
    all_articles = parse_articles(raw)

    logger.info(f"Step 1: Fetched {len(all_trials)} trials, {len(all_articles)} articles")

    # Step 2: Pydantic contracts
    valid_trials = [t for t in all_trials if validate_bronze_trial(t)[0]]
    valid_articles = [a for a in all_articles if validate_bronze_article(a)[0]]
    logger.info(f"Step 2: Contracts passed {len(valid_trials)}/{len(all_trials)} trials, {len(valid_articles)}/{len(all_articles)} articles")

    # Step 3: Kafka
    producer = KafkaProducer()
    producer.connect()
    for t in valid_trials:
        producer.produce("clinical-trials", t.get("nct_id", ""), t)
    for a in valid_articles:
        producer.produce("pubmed-articles", a.get("pmid", ""), a)
    logger.info(f"Step 3: Kafka published. Topics: {InMemoryBus.get_stats()}")

    # Step 4: Delta Bronze
    delta_write("clinical_trials", "bronze", valid_trials)
    delta_write("pubmed_articles", "bronze", valid_articles)
    track_ingestion("clinicaltrials.gov", "clinical_trials", len(valid_trials))
    track_ingestion("pubmed", "pubmed_articles", len(valid_articles))
    logger.info("Step 4: Bronze written")

    # Step 5: Delta Silver MERGE
    t_merge = delta_merge("clinical_trials", "silver", valid_trials, merge_key="nct_id")
    a_merge = delta_merge("pubmed_articles", "silver", valid_articles, merge_key="pmid")
    track_transformation("clinical_trials", len(valid_trials), t_merge["total"])
    track_transformation("pubmed_articles", len(valid_articles), a_merge["total"])
    logger.info(f"Step 5: Silver MERGE done. Trials: {t_merge['inserted']}i/{t_merge['updated']}u")

    # Step 6: Delta Gold
    gold_records = []
    for t in valid_trials:
        parts = [t.get("title",""), t.get("brief_summary",""), t.get("eligibility_criteria","")]
        conds = t.get("conditions", [])
        if isinstance(conds, list): parts.extend(conds)
        gold_records.append({**t, "source_id": t.get("nct_id",""), "entity_type": "clinical_trial",
            "search_text": " ".join(p for p in parts if p), "enriched_at": datetime.utcnow().isoformat()})
    for a in valid_articles:
        gold_records.append({**a, "source_id": a.get("pmid",""), "entity_type": "pubmed_article",
            "search_text": f"{a.get('title','')} {a.get('abstract','')}", "enriched_at": datetime.utcnow().isoformat()})
    delta_write("clinical_trials", "gold", [r for r in gold_records if r["entity_type"]=="clinical_trial"])
    delta_write("pubmed_articles", "gold", [r for r in gold_records if r["entity_type"]=="pubmed_article"])
    track_enrichment("clinical_trials", len(valid_trials))
    track_enrichment("pubmed_articles", len(valid_articles))
    logger.info("Step 6: Gold enriched")

    # Step 7: Embeddings
    try:
        from embeddings.embedding_service import generate_embeddings_batch
        from rag.vector_store import upsert_vectors, init_collection
        init_collection()
        texts = [r["search_text"][:500] for r in gold_records[:30]]
        if texts:
            embeddings = generate_embeddings_batch(texts)
            points = [{"id": abs(hash(r["source_id"])) % (2**63), "vector": e,
                "payload": {"source_id": r["source_id"], "entity_type": r["entity_type"],
                    "title": r.get("title",""), "brief_summary": r.get("brief_summary", r.get("abstract",""))[:500],
                    "status": r.get("status","")}}
                for r, e in zip(gold_records[:30], embeddings)]
            upsert_vectors(points)
            logger.info(f"Step 7: Embedded {len(points)} vectors")
    except Exception as e:
        logger.warning(f"Step 7: Embedding skipped: {e}")

    # Step 8: Great Expectations
    ge_reports = []
    ge_reports.append(validate_bronze(valid_trials, "clinical_trials"))
    ge_reports.append(validate_silver(valid_trials, "clinical_trials"))
    ge_reports.append(validate_gold([r for r in gold_records if "search_text" in r], "clinical_trials"))
    for r in ge_reports:
        logger.info(f"Step 8 GE '{r['suite']}': {r['passed']}/{r['total_expectations']} passed")

    # Step 9: OpenLineage
    lineage.emit_event("full_pipeline", "COMPLETE",
        inputs=[{"name": "clinicaltrials.gov"}, {"name": "pubmed"}],
        outputs=[{"name": "delta.gold.clinical_trials"}, {"name": "qdrant.clinical_data"}])
    logger.info("Step 9: OpenLineage emitted")

    elapsed = time.time() - start
    return {
        "status": "success",
        "trials_processed": len(valid_trials),
        "articles_processed": len(valid_articles),
        "gold_records": len(gold_records),
        "delta_stats": get_delta_stats(),
        "kafka_topics": InMemoryBus.get_stats(),
        "ge_reports": [{"suite": r["suite"], "passed": r["passed"], "total": r["total_expectations"]} for r in ge_reports],
        "elapsed_seconds": round(elapsed, 1),
    }


@router.get("/stats", summary="Pipeline Statistics")
async def pipeline_stats():
    from rag.vector_store import get_collection_stats
    return {
        "delta_lakehouse": get_delta_stats(),
        "vector_store": get_collection_stats(),
        "kafka_topics": InMemoryBus.get_stats(),
    }
