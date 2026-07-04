"""
Streamlit Frontend — Healthcare Clinical Trial Matcher UI

Run with: streamlit run frontend/app.py
"""

import streamlit as st
import requests
import json

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Healthcare Trial Matcher",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Healthcare Clinical Trial Matcher")
st.markdown("*Advanced RAG-powered clinical trial matching system*")

# Sidebar
st.sidebar.header("System Status")
try:
    health = requests.get(f"{API_URL}/health", timeout=5).json()
    st.sidebar.success(f"API: {health.get('status', 'unknown')}")
    st.sidebar.info(f"DB: {health.get('database', 'unknown')}")

    stats = requests.get(f"{API_URL}/trials/stats", timeout=5).json()
    st.sidebar.metric("Clinical Trials", stats.get("clinical_trials", 0))
    st.sidebar.metric("PubMed Articles", stats.get("pubmed_articles", 0))
    st.sidebar.metric("Documents", stats.get("documents", 0))
except Exception:
    st.sidebar.error("API not running")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Trial Matcher", "📥 Data Ingestion", "📄 Documents", "📊 Pipeline"
])

with tab1:
    st.header("Find Matching Clinical Trials")
    condition = st.text_input("Patient Condition", placeholder="e.g., Stage 3 non-small cell lung cancer")
    col1, col2 = st.columns(2)
    age = col1.number_input("Age", min_value=0, max_value=120, value=55)
    gender = col2.selectbox("Gender", ["", "male", "female", "other"])

    if st.button("🔍 Find Matches", type="primary"):
        if condition:
            with st.spinner("Searching..."):
                try:
                    resp = requests.post(
                        f"{API_URL}/trials/match",
                        json={"condition": condition, "age": age, "gender": gender or None},
                        timeout=30,
                    ).json()
                    st.success(f"Found {resp.get('total_matches', 0)} matches in {resp.get('search_time_ms', 0):.0f}ms")
                    for match in resp.get("matches", []):
                        with st.expander(f"🧬 {match['title']} (Score: {match['relevance_score']:.2f})"):
                            st.write(f"**Trial ID:** {match['trial_id']}")
                            st.write(f"**Status:** {match.get('status', 'N/A')}")
                            st.write(f"**Why it matched:** {match['match_explanation']}")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab2:
    st.header("Data Ingestion")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("ClinicalTrials.gov")
        trial_condition = st.text_input("Condition", value="lung cancer", key="trial_cond")
        trial_max = st.slider("Max Results", 10, 200, 50, key="trial_max")
        if st.button("Ingest Trials"):
            with st.spinner("Fetching..."):
                resp = requests.post(
                    f"{API_URL}/ingest/trials",
                    params={"condition": trial_condition, "max_results": trial_max},
                    timeout=60,
                ).json()
                st.json(resp)

    with col2:
        st.subheader("PubMed")
        pubmed_query = st.text_input("Search Query", value="lung cancer immunotherapy", key="pm_q")
        pubmed_max = st.slider("Max Articles", 5, 100, 20, key="pm_max")
        if st.button("Ingest PubMed"):
            with st.spinner("Fetching..."):
                resp = requests.post(
                    f"{API_URL}/ingest/pubmed",
                    params={"query": pubmed_query, "max_results": pubmed_max},
                    timeout=60,
                ).json()
                st.json(resp)

with tab3:
    st.header("Document Management")
    uploaded = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded and st.button("Process PDF"):
        with st.spinner("Processing..."):
            resp = requests.post(
                f"{API_URL}/documents/upload",
                files={"file": (uploaded.name, uploaded.read(), "application/pdf")},
                timeout=60,
            ).json()
            st.json(resp)

    if st.button("Refresh Document List"):
        resp = requests.get(f"{API_URL}/documents/list", timeout=10).json()
        for doc in resp.get("documents", []):
            st.write(f"📄 {doc['filename']} — {doc['num_pages']} pages, {doc['total_chunks']} chunks")

with tab4:
    st.header("Pipeline Status")
    st.markdown("""
    **Architecture:** Kafka → Bronze → Silver → Gold → Embeddings → Qdrant
    
    **Components:**
    - ✅ Kafka Producer/Consumer (with schema validation)
    - ✅ Delta Lakehouse (Bronze/Silver/Gold zones)
    - ✅ RAG Pipeline (Hybrid Search + Cross-Encoder Reranking)
    - ✅ Airflow DAG (end-to-end orchestration)
    - ✅ Great Expectations (data quality validation)
    - ✅ OpenLineage (data lineage tracking)
    """)
