# Healthcare Clinical Trial Matcher

A production-style Healthcare Clinical Trial Matcher using Advanced RAG (Retrieval-Augmented Generation).

## Architecture

```
Source APIs → Kafka Producer → Topics → Consumer → Bronze → Silver → Gold → Embeddings → Qdrant → RAG → LLM → Response
```

### Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI |
| Frontend | Streamlit |
| Database | PostgreSQL |
| Vector DB | Qdrant |
| LLM | Groq (LLaMA 3.1) |
| Embeddings | SentenceTransformers (all-MiniLM-L6-v2) |
| RAG | LangChain + Hybrid Search + Cross-Encoder |
| Messaging | Kafka (with in-memory fallback) |
| Lakehouse | Bronze/Silver/Gold (Delta pattern) |
| Pipeline | Apache Airflow |
| Validation | Great Expectations |
| Lineage | OpenLineage |
| Containerization | Docker |

## Deliverables

### 1. Ingestion Layer (Kafka + Schema Validation)
- `pipeline/kafka/producer.py` — Kafka producer with schema validation
- `pipeline/kafka/consumer.py` — Consumer processes messages from topics
- Topics: `clinical-trials`, `pubmed-articles`, `documents`

### 2. Delta Lakehouse (Bronze/Silver/Gold)
- `pipeline/lakehouse/lakehouse.py` — Medallion architecture
- Bronze: raw data storage (append-only)
- Silver: cleaned, deduplicated, schema-enforced (MERGE)
- Gold: enriched, search-ready data

### 3. RAG Pipeline
- `documents/text_chunker.py` — Overlapping text chunking
- `embeddings/embedding_service.py` — SentenceTransformer embeddings
- `rag/vector_store.py` — Qdrant vector index
- `rag/hybrid_search.py` — Combined semantic + keyword search
- `rag/reranker.py` — Cross-encoder reranking
- `rag/rag_engine.py` — Full RAG pipeline with LLM generation

### 4. Orchestration (Airflow DAG)
- `pipeline/dags/ingestion_dag.py` — End-to-end DAG
- Tasks: Fetch → Kafka → Lakehouse → Embed → Validate → Lineage

### 5. Quality Gate
- `validation/expectations.py` — Great Expectations suite
- `validation/lineage.py` — OpenLineage event emitter
- Validates data at bronze, silver, and gold layers

## Setup

```bash
git clone https://github.com/MohammedAlown/Healthcare-Trial-Matcher.git
cd Healthcare-Trial-Matcher
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

## Running

```bash
# API server
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
streamlit run frontend/app.py

# Run pipeline standalone
python pipeline/dags/ingestion_dag.py
```

## API Docs

http://localhost:8000/docs
