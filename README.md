# Healthcare Clinical Trial Matcher

A production-style Healthcare Clinical Trial Matcher using Advanced RAG (Retrieval-Augmented Generation).

## Architecture

- **Backend:** FastAPI
- **Frontend:** Streamlit
- **Database:** PostgreSQL
- **Vector DB:** Qdrant
- **LLM:** OpenAI API
- **Embeddings:** SentenceTransformers + ClinicalBERT
- **RAG:** LangChain with Hybrid Search + Cross-Encoder Reranking
- **Pipeline:** Apache Airflow
- **Validation:** Great Expectations
- **Containerization:** Docker

## Features

- ClinicalTrials.gov data ingestion
- PubMed paper ingestion
- PDF document processing
- Hybrid vector + keyword search
- Cross-Encoder reranking
- Citation generation with match explanations
- Data quality validation
- Audit logging and governance
- Real-time data pipeline
- Dockerized deployment

## Setup

```bash
git clone https://github.com/MohammedAlown/Healthcare-Trial-Matcher.git
cd Healthcare-Trial-Matcher
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

## Project Status

- [x] Milestone 1: Project Setup
- [ ] Milestone 2: FastAPI Backend
- [ ] Milestone 3: PostgreSQL Integration
- [ ] Milestone 4: ClinicalTrials.gov Ingestion
- [ ] Milestone 5: PubMed Ingestion
- [ ] Milestone 6: Document Processing
- [ ] Milestone 7: Embedding Generation
- [ ] Milestone 8: Qdrant Vector Database
- [ ] Milestone 9: Advanced RAG
- [ ] Milestone 10: Cross-Encoder Reranking
- [ ] Milestone 11: Real-Time Pipeline
- [ ] Milestone 12: Data Validation
- [ ] Milestone 13: Governance & Audit
- [ ] Milestone 14: Frontend
- [ ] Milestone 15: Docker Deployment
- [ ] Milestone 16: Testing
- [ ] Milestone 17: Documentation
- [ ] Milestone 18: Final Push
