"""
Kafka Producer — Publishes clinical trial and PubMed data to Kafka topics.

In production, data flows:
  API Source → Kafka Producer → Topic → Kafka Consumer → Database

This decouples ingestion from storage, enabling:
  - Buffering during high load
  - Multiple consumers processing the same data
  - Replay of messages if processing fails
"""

import json
import time
from typing import Optional
from backend.app.core.logger import logger

# Try confluent-kafka first, fall back to kafka-python
try:
    from confluent_kafka import Producer as ConfluentProducer

    class KafkaProducer:
        def __init__(self, bootstrap_servers: str = "localhost:9092"):
            self.config = {"bootstrap.servers": bootstrap_servers}
            self._producer = None
            self.connected = False

        def connect(self):
            try:
                self._producer = ConfluentProducer(self.config)
                self.connected = True
                logger.info("Kafka producer connected (confluent-kafka)")
            except Exception as e:
                logger.warning(f"Kafka not available: {e}. Using in-memory fallback.")
                self.connected = False

        def produce(self, topic: str, key: str, value: dict):
            message = json.dumps(value)
            if self.connected and self._producer:
                self._producer.produce(topic, key=key, value=message)
                self._producer.flush()
                logger.info(f"Produced to {topic}: {key}")
            else:
                InMemoryBus.publish(topic, key, value)

        def close(self):
            if self._producer:
                self._producer.flush()

except ImportError:
    class KafkaProducer:
        def __init__(self, bootstrap_servers: str = "localhost:9092"):
            self.connected = False
        def connect(self):
            logger.info("Kafka not installed. Using in-memory message bus.")
        def produce(self, topic: str, key: str, value: dict):
            InMemoryBus.publish(topic, key, value)
        def close(self):
            pass


class InMemoryBus:
    """
    In-memory message bus fallback when Kafka is not running.
    Implements the same produce/consume pattern for development.
    Schema validation is applied before publishing.
    """
    _topics: dict[str, list] = {}
    _schemas: dict[str, dict] = {}

    @classmethod
    def register_schema(cls, topic: str, required_fields: list[str]):
        cls._schemas[topic] = {"required_fields": required_fields}

    @classmethod
    def validate(cls, topic: str, value: dict) -> bool:
        schema = cls._schemas.get(topic)
        if not schema:
            return True
        for field in schema["required_fields"]:
            if field not in value:
                logger.error(f"Schema validation failed: missing '{field}' in topic '{topic}'")
                return False
        return True

    @classmethod
    def publish(cls, topic: str, key: str, value: dict):
        if not cls.validate(topic, value):
            raise ValueError(f"Schema validation failed for topic '{topic}'")
        if topic not in cls._topics:
            cls._topics[topic] = []
        message = {
            "key": key,
            "value": value,
            "timestamp": time.time(),
        }
        cls._topics[topic].append(message)
        logger.info(f"[InMemoryBus] Published to '{topic}': {key}")

    @classmethod
    def consume(cls, topic: str, from_offset: int = 0) -> list[dict]:
        messages = cls._topics.get(topic, [])
        return messages[from_offset:]

    @classmethod
    def get_stats(cls) -> dict:
        return {topic: len(msgs) for topic, msgs in cls._topics.items()}


# Register schemas for validation
InMemoryBus.register_schema("clinical-trials", [
    "nct_id", "title", "status"
])
InMemoryBus.register_schema("pubmed-articles", [
    "pmid", "title"
])
InMemoryBus.register_schema("documents", [
    "filename", "num_pages"
])
