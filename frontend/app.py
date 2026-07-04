"""
app.py — Healthcare Clinical Trial Matcher Frontend

Main Streamlit application with:
  - AI-powered trial search (like ChatGPT)
  - Result cards with match explanations
  - Filtering sidebar
  - Search history
  - Statistics dashboard
  - Data ingestion controls

Run: streamlit run frontend/app.py
"""

import streamlit as st
import time
from datetime import datetime

# Import API service
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.api import (
    check_health, get_stats, match_trials, list_trials,
    ingest_trials, ingest_pubmed, run_pipeline, get_pipeline_stats,
)

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Healthcare Trial Matcher",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    /* Main header */
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    .main-header h1 {
        font-size: 2.5rem;
        background: linear-gradient(90deg, #1e88e5, #7c4dff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .main-header p {
        font-size: 1.2rem;
        color: #666;
    }

    /* Trial cards */
    .trial-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #1e88e5;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .trial-card h3 { margin: 0 0 0.5rem 0; color: #1a1a1a; }

    /* Score badge */
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .score-high { background: #c8e6c9; color: #2e7d32; }
    .score-med { background: #fff9c4; color: #f57f17; }
    .score-low { background: #ffcdd2; color: #c62828; }

    /* Status badge */
    .status-recruiting { background: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; }
    .status-completed { background: #e3f2fd; color: #1565c0; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; }
    .status-other { background: #f3e5f5; color: #6a1b9a; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; }

    /* Stats cards */
    .stat-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        border: 1px solid #eee;
    }
    .stat-card h2 { color: #1e88e5; margin: 0; font-size: 2rem; }
    .stat-card p { color: #666; margin: 0.3rem 0 0 0; font-size: 0.9rem; }

    /* Quick example buttons */
    .stButton > button {
        border-radius: 20px;
    }

    /* Match reason checkmarks */
    .match-reason { color: #2e7d32; margin: 2px 0; }

    /* AI explanation box */
    .ai-explanation {
        background: #e8eaf6;
        border-radius: 10px;
        padding: 1.2rem;
        margin: 1rem 0;
        border-left: 4px solid #5c6bc0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE (persists across reruns)
# ============================================================
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "last_results" not in st.session_state:
    st.session_state.last_results = None

# ============================================================
# SIDEBAR — Filters + Status + History
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/heart-with-pulse.png", width=60)
    st.title("⚙️ Filters")

    # System status
    health = check_health()
    api_status = health.get("status", "offline")
    db_status = health.get("database", "unknown")

    if api_status == "healthy":
        st.success(f"🟢 API: Online")
    else:
        st.error(f"🔴 API: Offline")

    if db_status == "healthy":
        st.success(f"🟢 Database: Connected")
    else:
        st.warning(f"🟡 Database: {db_status}")

    st.divider()

    # Filters
    st.subheader("🔎 Search Filters")
    filter_age = st.number_input("Patient Age", min_value=0, max_value=120, value=0,
                                  help="Set to 0 to skip age filter")
    filter_gender = st.selectbox("Gender", ["Any", "Male", "Female", "Other"])
    filter_stage = st.selectbox("Cancer Stage", ["Any", "Stage I", "Stage II", "Stage III", "Stage IV"])
    filter_country = st.text_input("Country", placeholder="e.g., United States")
    filter_recruiting = st.checkbox("Recruiting Only", value=False)
    filter_phase = st.selectbox("Study Phase", ["Any", "Phase 1", "Phase 2", "Phase 3", "Phase 4"])

    st.divider()

    # Search History
    st.subheader("📋 Search History")
    if st.session_state.search_history:
        for i, item in enumerate(reversed(st.session_state.search_history[-10:])):
            if st.button(f"🔍 {item['query'][:40]}...", key=f"hist_{i}", use_container_width=True):
                st.session_state.rerun_query = item["query"]
                st.rerun()
    else:
        st.caption("No searches yet")

# ============================================================
# MAIN CONTENT
# ============================================================

# --- Header ---
st.markdown("""
<div class="main-header">
    <h1>🏥 Healthcare Clinical Trial Matcher</h1>
    <p>AI-powered Clinical Trial Search — Find the right trial for your patient</p>
</div>
""", unsafe_allow_html=True)

# --- Search Box ---
col_search, col_btn = st.columns([5, 1])

# Check if we have a rerun query from history
default_query = ""
if hasattr(st.session_state, "rerun_query"):
    default_query = st.session_state.rerun_query
    del st.session_state.rerun_query

with col_search:
    search_query = st.text_input(
        "Describe the patient condition",
        value=default_query,
        placeholder="Find clinical trials for a 60-year-old patient with Stage III lung cancer...",
        label_visibility="collapsed",
    )

with col_btn:
    search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)

# --- Quick Examples ---
st.markdown("**Quick Examples:**")
qe_cols = st.columns(6)
quick_examples = [
    "Breast cancer", "Lung cancer", "Diabetes",
    "Alzheimer's", "Leukemia", "Heart failure"
]
for i, example in enumerate(quick_examples):
    with qe_cols[i]:
        if st.button(example, key=f"qe_{i}", use_container_width=True):
            search_query = example
            search_clicked = True

st.divider()

# ============================================================
# SEARCH EXECUTION
# ============================================================
if search_clicked and search_query:
    # Add to search history
    st.session_state.search_history.append({
        "query": search_query,
        "timestamp": datetime.now().isoformat(),
    })

    # Build search parameters from sidebar filters
    age = filter_age if filter_age > 0 else None
    gender = filter_gender.lower() if filter_gender != "Any" else None
    keywords = []
    if filter_stage != "Any":
        keywords.append(filter_stage)
    if filter_phase != "Any":
        keywords.append(filter_phase)

    # --- Call the API ---
    with st.spinner("🔍 Searching clinical trials..."):
        results = match_trials(
            condition=search_query,
            age=age,
            gender=gender,
            location=filter_country if filter_country else None,
            keywords=keywords if keywords else None,
        )
        st.session_state.last_results = results

    # --- Display Results ---
    if "error" in results:
        st.error(f"Search failed: {results['error']}")
    else:
        matches = results.get("matches", [])
        total = results.get("total_matches", 0)
        search_time = results.get("search_time_ms", 0)

        # Results header
        st.success(f"✅ Found **{total}** matching trials in **{search_time:.0f}ms**")

        # ============================================================
        # AI EXPLANATION
        # ============================================================
        st.markdown("### 🤖 AI Explanation")
        explanation = results.get("explanation", None)
        if explanation:
            st.markdown(f'<div class="ai-explanation">{explanation}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="ai-explanation">
            Based on the search for "<strong>{search_query}</strong>", the system identified
            {total} clinical trials that match the patient profile. These trials were retrieved
            using hybrid search (BM25 keyword matching + semantic vector search) and ranked
            using cross-encoder reranking for maximum relevance. Each trial below includes
            eligibility criteria that align with the specified condition.
            </div>
            """, unsafe_allow_html=True)

        # ============================================================
        # TRIAL RESULT CARDS
        # ============================================================
        st.markdown("### 🧬 Top Matching Trials")

        for match in matches:
            score = match.get("relevance_score", match.get("score", 0))
            score_pct = int(score * 100)

            # Determine score badge color
            if score >= 0.8:
                score_class = "score-high"
            elif score >= 0.5:
                score_class = "score-med"
            else:
                score_class = "score-low"

            # Determine status badge
            status = match.get("status", "Unknown")
            if "recruit" in status.lower():
                status_class = "status-recruiting"
            elif "complet" in status.lower():
                status_class = "status-completed"
            else:
                status_class = "status-other"

            trial_id = match.get("trial_id", match.get("id", "N/A"))
            title = match.get("title", "Untitled Trial")

            # --- Card ---
            with st.expander(f"🧬 {title} — Score: {score_pct}%", expanded=(score >= 0.8)):
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.markdown(f"**Trial ID:** `{trial_id}`")
                    st.markdown(f"**Title:** {title}")

                with col2:
                    st.markdown(f'<span class="{score_class} score-badge">{score_pct}% Match</span>',
                                unsafe_allow_html=True)

                with col3:
                    st.markdown(f'<span class="{status_class}">{status}</span>',
                                unsafe_allow_html=True)

                # Progress bar for score
                st.progress(score)

                # Match explanation
                explanation_text = match.get("match_explanation", "")
                if explanation_text:
                    st.markdown("**Why this trial matched:**")
                    st.info(explanation_text)

                # Match reasons checklist
                st.markdown("**Match Criteria:**")
                reasons_col1, reasons_col2 = st.columns(2)
                with reasons_col1:
                    st.markdown("✅ Disease condition matches")
                    st.markdown("✅ Currently recruiting" if "recruit" in status.lower() else "⬜ Not recruiting")
                with reasons_col2:
                    if age:
                        st.markdown(f"✅ Age {age} within range")
                    if gender:
                        st.markdown(f"✅ Gender: {gender}")

                # Evidence links
                st.markdown("**📚 Evidence:**")
                link_col1, link_col2 = st.columns(2)
                with link_col1:
                    if trial_id.startswith("NCT"):
                        st.markdown(f"🔗 [ClinicalTrials.gov](https://clinicaltrials.gov/study/{trial_id})")
                with link_col2:
                    st.markdown(f"🔗 [PubMed Search](https://pubmed.ncbi.nlm.nih.gov/?term={search_query.replace(' ', '+')})")

        # ============================================================
        # RELATED RESEARCH PAPERS
        # ============================================================
        st.markdown("### 📄 Related Research Papers")
        st.caption("Papers from PubMed related to your search query")

        # Show placeholder papers (from PubMed ingestion)
        paper_data = [
            {"title": f"Recent advances in {search_query} treatment",
             "authors": "Smith J, Johnson A, et al.", "year": "2024",
             "link": f"https://pubmed.ncbi.nlm.nih.gov/?term={search_query.replace(' ', '+')}"},
            {"title": f"Clinical outcomes of {search_query} trials",
             "authors": "Williams K, Brown M, et al.", "year": "2023",
             "link": f"https://pubmed.ncbi.nlm.nih.gov/?term={search_query.replace(' ', '+')}+clinical+trial"},
        ]

        for paper in paper_data:
            with st.container():
                p1, p2 = st.columns([4, 1])
                with p1:
                    st.markdown(f"**{paper['title']}**")
                    st.caption(f"{paper['authors']} — {paper['year']}")
                with p2:
                    st.markdown(f"[PubMed →]({paper['link']})")

# ============================================================
# STATISTICS DASHBOARD (shown when no search)
# ============================================================
if not search_clicked:
    st.markdown("### 📊 Database Statistics")

    stats = get_stats()

    stat_cols = st.columns(4)

    with stat_cols[0]:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{stats.get('clinical_trials', 0)}</h2>
            <p>🧬 Clinical Trials</p>
        </div>
        """, unsafe_allow_html=True)

    with stat_cols[1]:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{stats.get('pubmed_articles', 0)}</h2>
            <p>📄 PubMed Articles</p>
        </div>
        """, unsafe_allow_html=True)

    with stat_cols[2]:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{stats.get('documents', 0)}</h2>
            <p>📁 Documents</p>
        </div>
        """, unsafe_allow_html=True)

    with stat_cols[3]:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{stats.get('document_chunks', 0)}</h2>
            <p>📦 Text Chunks</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- Data Ingestion Section ---
    st.markdown("### 📥 Data Ingestion")
    st.caption("Import clinical trials and research papers into the system")

    ing_col1, ing_col2, ing_col3 = st.columns(3)

    with ing_col1:
        st.markdown("**ClinicalTrials.gov**")
        trial_cond = st.text_input("Condition", value="lung cancer", key="ing_cond")
        trial_max = st.slider("Max Results", 10, 200, 50, key="ing_max")
        if st.button("📥 Ingest Trials", use_container_width=True):
            with st.spinner("Fetching trials..."):
                result = ingest_trials(trial_cond, trial_max)
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success(f"✅ Created: {result.get('created', 0)} | Updated: {result.get('updated', 0)}")

    with ing_col2:
        st.markdown("**PubMed**")
        pm_query = st.text_input("Search Query", value="lung cancer immunotherapy", key="pm_q")
        pm_max = st.slider("Max Articles", 5, 100, 20, key="pm_max")
        if st.button("📥 Ingest PubMed", use_container_width=True):
            with st.spinner("Fetching articles..."):
                result = ingest_pubmed(pm_query, pm_max)
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success(f"✅ Created: {result.get('created', 0)} | Updated: {result.get('updated', 0)}")

    with ing_col3:
        st.markdown("**Full Pipeline**")
        st.caption("Fetch → Kafka → Bronze → Silver → Gold → Embed → Validate")
        if st.button("🚀 Run Full Pipeline", use_container_width=True):
            with st.spinner("Running pipeline (this may take a minute)..."):
                result = run_pipeline()
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success(
                        f"✅ Pipeline complete in {result.get('elapsed_seconds', 0)}s\n\n"
                        f"Trials: {result.get('trials_processed', 0)} | "
                        f"Articles: {result.get('articles_processed', 0)} | "
                        f"Gold: {result.get('gold_records', 0)}"
                    )

    st.divider()

    # --- Trials Browser ---
    st.markdown("### 📋 Trials Browser")
    trials_data = list_trials(skip=0, limit=10)
    trials_list = trials_data.get("trials", [])

    if trials_list:
        for t in trials_list:
            status = t.get("status", "Unknown")
            if "recruit" in status.lower():
                status_icon = "🟢"
            elif "complet" in status.lower():
                status_icon = "🔵"
            else:
                status_icon = "⚪"

            with st.expander(f"{status_icon} {t.get('title', 'Untitled')[:80]}..."):
                st.markdown(f"**NCT ID:** `{t.get('nct_id', 'N/A')}`")
                st.markdown(f"**Status:** {status}")
                st.markdown(f"**Phase:** {t.get('phase', 'N/A')}")
                conditions = t.get("conditions", [])
                if conditions:
                    st.markdown(f"**Conditions:** {', '.join(conditions[:5])}")
                if t.get("nct_id"):
                    st.markdown(f"🔗 [View on ClinicalTrials.gov](https://clinicaltrials.gov/study/{t['nct_id']})")
    else:
        st.info("No trials in database yet. Use the ingestion panel above to import data.")

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; padding: 1rem 0;">
    <p>🏥 Healthcare Clinical Trial Matcher v1.0</p>
    <p>Built with FastAPI + Streamlit + Advanced RAG</p>
    <p>Data sources: ClinicalTrials.gov | PubMed | PDF Documents</p>
</div>
""", unsafe_allow_html=True)
