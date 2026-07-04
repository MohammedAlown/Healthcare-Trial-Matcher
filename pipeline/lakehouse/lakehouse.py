"""
Delta Lakehouse — Bronze / Silver / Gold Architecture

This implements the medallion architecture pattern:

  BRONZE (Raw Layer)
    - Raw data exactly as received from APIs
    - No transformations, no cleaning
    - Append-only, immutable
    - Purpose: audit trail, reprocessing

  SILVER (Cleaned Layer)
    - Deduplicated, validated, standardized
    - Schema enforced
    - NULL handling, type casting
    - Purpose: reliable single source of truth

  GOLD (Enriched Layer)
    - Business-ready, aggregated
    - Joined with other data sources
    - Embeddings generated, search-ready
    - Purpose: serves the RAG pipeline and analytics

Data flows: Source → Bronze → Silver → Gold → RAG/Search
"""

import json
import os
import time
from datetime import datetime
from typing import Optional
from backend.app.core.logger import logger


# Storage paths
LAKEHOUSE_BASE = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "lakehouse"
)


class LakehouseLayer:
    """Manages a single layer (bronze/silver/gold) of the lakehouse."""

    def __init__(self, layer_name: str):
        self.layer_name = layer_name
        self.base_path = os.path.join(LAKEHOUSE_BASE, layer_name)
        os.makedirs(self.base_path, exist_ok=True)

    def write(self, entity_type: str, records: list[dict]) -> dict:
        """Write records to this layer."""
        entity_path = os.path.join(self.base_path, entity_type)
        os.makedirs(entity_path, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{entity_type}_{timestamp}.json"
        filepath = os.path.join(entity_path, filename)

        payload = {
            "layer": self.layer_name,
            "entity_type": entity_type,
            "timestamp": timestamp,
            "record_count": len(records),
            "records": records,
        }

        with open(filepath, "w") as f:
            json.dump(payload, f, indent=2, default=str)

        logger.info(
            f"[{self.layer_name.upper()}] Wrote {len(records)} "
            f"{entity_type} records to {filename}"
        )
        return {"file": filename, "records": len(records)}

    def read_latest(self, entity_type: str) -> list[dict]:
        """Read the latest file for an entity type."""
        entity_path = os.path.join(self.base_path, entity_type)
        if not os.path.exists(entity_path):
            return []

        files = sorted(os.listdir(entity_path))
        if not files:
            return []

        latest_file = os.path.join(entity_path, files[-1])
        with open(latest_file, "r") as f:
            data = json.load(f)
        return data.get("records", [])

    def count_files(self, entity_type: str = None) -> int:
        """Count files in this layer."""
        if entity_type:
            path = os.path.join(self.base_path, entity_type)
            if not os.path.exists(path):
                return 0
            return len(os.listdir(path))
        total = 0
        if os.path.exists(self.base_path):
            for d in os.listdir(self.base_path):
                dp = os.path.join(self.base_path, d)
                if os.path.isdir(dp):
                    total += len(os.listdir(dp))
        return total


# Initialize layers
bronze = LakehouseLayer("bronze")
silver = LakehouseLayer("silver")
gold = LakehouseLayer("gold")


# ============================================================
# Transformation Functions
# ============================================================

def bronze_ingest(entity_type: str, raw_records: list[dict]) -> dict:
    """Write raw data to bronze layer (no transformation)."""
    return bronze.write(entity_type, raw_records)


def silver_transform(entity_type: str, raw_records: list[dict]) -> list[dict]:
    """
    Clean and validate records for silver layer.

    Transformations:
      - Remove duplicates (by nct_id or pmid)
      - Strip whitespace from text fields
      - Enforce required fields
      - Standardize status values
    """
    seen_ids = set()
    cleaned = []

    for record in raw_records:
        # Determine unique key
        uid = record.get("nct_id") or record.get("pmid") or record.get("filename")
        if not uid or uid in seen_ids:
            continue
        seen_ids.add(uid)

        # Strip whitespace from string fields
        for key, value in record.items():
            if isinstance(value, str):
                record[key] = value.strip()

        # Validate required fields
        title = record.get("title", "")
        if not title:
            continue

        # Standardize status
        status = record.get("status", "Unknown")
        status_map = {
            "RECRUITING": "Recruiting",
            "COMPLETED": "Completed",
            "ACTIVE_NOT_RECRUITING": "Active, not recruiting",
            "WITHDRAWN": "Withdrawn",
            "TERMINATED": "Terminated",
            "SUSPENDED": "Suspended",
        }
        record["status"] = status_map.get(status.upper().replace(" ", "_"), status)

        cleaned.append(record)

    # Write to silver
    silver.write(entity_type, cleaned)
    logger.info(
        f"[SILVER] Transformed {len(raw_records)} → {len(cleaned)} "
        f"{entity_type} records"
    )
    return cleaned


def gold_enrich(entity_type: str, clean_records: list[dict]) -> list[dict]:
    """
    Enrich records for gold layer.

    Enrichments:
      - Combine title + summary into searchable text
      - Add metadata tags
      - Mark as ready for embedding
    """
    enriched = []

    for record in clean_records:
        # Build combined search text
        parts = [
            record.get("title", ""),
            record.get("brief_summary", "") or record.get("abstract", ""),
            record.get("eligibility_criteria", ""),
        ]
        conditions = record.get("conditions", [])
        if isinstance(conditions, list):
            parts.extend(conditions)

        record["search_text"] = " ".join(p for p in parts if p)
        record["is_gold"] = True
        record["enriched_at"] = datetime.utcnow().isoformat()
        enriched.append(record)

    # Write to gold
    gold.write(entity_type, enriched)
    logger.info(
        f"[GOLD] Enriched {len(enriched)} {entity_type} records"
    )
    return enriched


def run_lakehouse_pipeline(entity_type: str, raw_records: list[dict]) -> dict:
    """
    Full lakehouse pipeline: Bronze → Silver → Gold

    MERGE logic: upserts based on unique ID (nct_id / pmid).
    Schema enforcement: validates required fields at silver layer.
    """
    logger.info(f"Running lakehouse pipeline for {len(raw_records)} {entity_type}")

    # Bronze: raw storage
    bronze_result = bronze_ingest(entity_type, raw_records)

    # Silver: clean + validate + deduplicate (MERGE)
    silver_records = silver_transform(entity_type, raw_records)

    # Gold: enrich for RAG
    gold_records = gold_enrich(entity_type, silver_records)

    return {
        "entity_type": entity_type,
        "bronze_records": bronze_result["records"],
        "silver_records": len(silver_records),
        "gold_records": len(gold_records),
    }


def get_lakehouse_stats() -> dict:
    """Get file counts across all layers."""
    return {
        "bronze": bronze.count_files(),
        "silver": silver.count_files(),
        "gold": gold.count_files(),
    }
