"""
Kafka Producer — Uses in-memory message bus with schema validation.
In production, swap InMemoryBus for real Kafka (confluent-kafka).
"""

import json
import time
from backend.app.core.logger import logger


class InMemoryBus:
    """In-memory message bus with schema validation (Kafka replacement for dev)."""
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
        cls._topics[topic].append({"key": key, "value": value, "timestamp": time.time()})
        logger.info(f"[Kafka/InMemoryBus] Published to '{topic}': {key}")

    @classmethod
    def consume(cls, topic: str, from_offset: int = 0) -> list[dict]:
        return cls._topics.get(topic, [])[from_offset:]

    @classmethod
    def get_stats(cls) -> dict:
        return {topic: len(msgs) for topic, msgs in cls._topics.items()}


# Register schemas
InMemoryBus.register_schema("clinical-trials", ["nct_id", "title", "status"])
InMemoryBus.register_schema("pubmed-articles", ["pmid", "title"])
InMemoryBus.register_schema("documents", ["filename", "num_pages"])


class KafkaProducer:
    """Producer that uses InMemoryBus (swap for confluent-kafka in production)."""
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.connected = False
    def connect(self):
        self.connected = True
        logger.info("Kafka producer ready (in-memory mode)")
    def produce(self, topic: str, key: str, value: dict):
        InMemoryBus.publish(topic, key, value)
    def close(self):
        pass
