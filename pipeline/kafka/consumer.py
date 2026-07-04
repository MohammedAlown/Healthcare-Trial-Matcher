"""
Kafka Consumer — Reads messages from Kafka topics and processes them.

Consumes data from:
  - clinical-trials topic → stores in PostgreSQL clinical_trials table
  - pubmed-articles topic → stores in PostgreSQL pubmed_articles table
  - documents topic → triggers document processing pipeline

Each message goes through:
  1. Schema validation
  2. Bronze layer (raw storage)
  3. Silver layer (cleaned/transformed)
  4. Gold layer (enriched/ready for RAG)
"""

import json
from typing import Callable
from backend.app.core.logger import logger
from pipeline.kafka.producer import InMemoryBus


class KafkaConsumer:
    """Consumer that reads from in-memory bus or real Kafka."""

    def __init__(self, topics: list[str], group_id: str = "trial-matcher"):
        self.topics = topics
        self.group_id = group_id
        self.handlers: dict[str, Callable] = {}
        self.offsets: dict[str, int] = {t: 0 for t in topics}

    def register_handler(self, topic: str, handler: Callable):
        """Register a processing function for a topic."""
        self.handlers[topic] = handler
        logger.info(f"Registered handler for topic: {topic}")

    def consume_batch(self) -> dict:
        """Process all pending messages across topics."""
        stats = {"processed": 0, "errors": 0}

        for topic in self.topics:
            messages = InMemoryBus.consume(topic, from_offset=self.offsets[topic])
            handler = self.handlers.get(topic)

            for msg in messages:
                try:
                    if handler:
                        handler(msg["value"])
                    stats["processed"] += 1
                except Exception as e:
                    logger.error(f"Error processing {topic} message: {e}")
                    stats["errors"] += 1

            self.offsets[topic] += len(messages)

        return stats
