"""
OpenLineage — Data Lineage Tracking

Tracks the flow of data through the system:
  - What data was read (inputs)
  - What was produced (outputs)
  - What transformations were applied
  - When it happened

This creates an audit trail showing exactly how data
moved from source APIs → bronze → silver → gold → embeddings.

Implements OpenLineage spec: https://openlineage.io/
"""

import json
import os
from datetime import datetime
from uuid import uuid4
from backend.app.core.logger import logger


LINEAGE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "lineage"
)


class LineageEmitter:
    """Emit OpenLineage-compatible events."""

    def __init__(self, namespace: str = "healthcare-trial-matcher"):
        self.namespace = namespace
        os.makedirs(LINEAGE_DIR, exist_ok=True)

    def emit_event(
        self,
        job_name: str,
        event_type: str,  # START, COMPLETE, FAIL
        inputs: list[dict] = None,
        outputs: list[dict] = None,
        run_facets: dict = None,
    ) -> dict:
        """
        Emit an OpenLineage event.

        Args:
            job_name: Name of the pipeline step
            event_type: START, COMPLETE, or FAIL
            inputs: List of input datasets
            outputs: List of output datasets
            run_facets: Additional metadata about the run
        """
        event = {
            "eventType": event_type,
            "eventTime": datetime.utcnow().isoformat() + "Z",
            "run": {
                "runId": str(uuid4()),
                "facets": run_facets or {},
            },
            "job": {
                "namespace": self.namespace,
                "name": job_name,
            },
            "inputs": [
                {
                    "namespace": self.namespace,
                    "name": i.get("name", "unknown"),
                    "facets": i.get("facets", {}),
                }
                for i in (inputs or [])
            ],
            "outputs": [
                {
                    "namespace": self.namespace,
                    "name": o.get("name", "unknown"),
                    "facets": o.get("facets", {}),
                }
                for o in (outputs or [])
            ],
        }

        # Save event to file
        filename = f"{job_name}_{event_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(LINEAGE_DIR, filename)
        with open(filepath, "w") as f:
            json.dump(event, f, indent=2)

        logger.info(f"[OpenLineage] {event_type} event for job '{job_name}'")
        return event


# Global emitter instance
lineage = LineageEmitter()


def track_ingestion(source: str, entity_type: str, record_count: int):
    """Track a data ingestion event."""
    lineage.emit_event(
        job_name=f"ingest_{entity_type}",
        event_type="COMPLETE",
        inputs=[{"name": source, "facets": {"source_type": "api"}}],
        outputs=[{
            "name": f"bronze.{entity_type}",
            "facets": {"record_count": record_count},
        }],
    )


def track_transformation(entity_type: str, input_count: int, output_count: int):
    """Track a data transformation event."""
    lineage.emit_event(
        job_name=f"transform_{entity_type}",
        event_type="COMPLETE",
        inputs=[{"name": f"bronze.{entity_type}", "facets": {"record_count": input_count}}],
        outputs=[{"name": f"silver.{entity_type}", "facets": {"record_count": output_count}}],
    )


def track_enrichment(entity_type: str, record_count: int):
    """Track a data enrichment event."""
    lineage.emit_event(
        job_name=f"enrich_{entity_type}",
        event_type="COMPLETE",
        inputs=[{"name": f"silver.{entity_type}"}],
        outputs=[{
            "name": f"gold.{entity_type}",
            "facets": {"record_count": record_count},
        }],
    )
