"""
Embedding Service — Generates vector embeddings for text.

Uses SentenceTransformers to convert text into dense vectors.
These vectors capture semantic meaning, so similar medical
concepts end up close together in vector space.

Model: all-MiniLM-L6-v2 (fast, good quality, 384 dimensions)
For medical: can swap to ClinicalBERT / BioBERT for better results.
"""

from sentence_transformers import SentenceTransformer
from backend.app.core.logger import logger

# Load model once at import time
logger.info("Loading embedding model...")
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded: all-MiniLM-L6-v2 (384 dims)")
    return _model


def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding vector from text."""
    model = get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_embeddings_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    model = get_model()
    embeddings = model.encode(texts, batch_size=batch_size, normalize_embeddings=True)
    logger.info(f"Generated {len(embeddings)} embeddings")
    return [e.tolist() for e in embeddings]
