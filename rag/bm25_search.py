"""
bm25_search.py — BM25 Keyword Search

BM25 (Best Matching 25) is a ranking function used by search engines.
Unlike simple keyword matching (ILIKE), BM25 considers:
  - Term frequency (TF): how often a word appears in a document
  - Inverse document frequency (IDF): how rare a word is across all docs
  - Document length normalization

This gives much better keyword search results than SQL ILIKE.
"""

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from database.models import ClinicalTrial, PubMedArticle
from backend.app.core.logger import logger


class BM25Index:
    """
    In-memory BM25 index built from database records.
    Rebuilt on each search to include latest data.
    """

    def __init__(self):
        self.documents = []     # Original records
        self.corpus = []        # Tokenized texts
        self.bm25 = None

    def build_from_db(self, db: Session):
        """Build BM25 index from all trials and articles in the database."""
        self.documents = []
        self.corpus = []

        # Load trials
        trials = db.query(ClinicalTrial).all()
        for t in trials:
            text = f"{t.title} {t.brief_summary or ''} {t.eligibility_criteria or ''}"
            conditions = t.conditions if isinstance(t.conditions, list) else []
            text += " " + " ".join(conditions)
            self.documents.append({
                "id": f"trial_{t.nct_id}",
                "entity_type": "clinical_trial",
                "nct_id": t.nct_id,
                "title": t.title,
                "brief_summary": t.brief_summary or "",
                "status": t.status,
            })
            self.corpus.append(text.lower().split())

        # Load articles
        articles = db.query(PubMedArticle).all()
        for a in articles:
            text = f"{a.title} {a.abstract or ''}"
            keywords = a.keywords if isinstance(a.keywords, list) else []
            text += " " + " ".join(keywords)
            self.documents.append({
                "id": f"article_{a.pmid}",
                "entity_type": "pubmed_article",
                "pmid": a.pmid,
                "title": a.title,
                "abstract": a.abstract or "",
            })
            self.corpus.append(text.lower().split())

        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)
            logger.info(f"BM25 index built: {len(self.corpus)} documents")
        else:
            logger.warning("BM25 index empty — no documents in database")

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        """
        Search the BM25 index.

        Returns ranked results with BM25 scores.
        """
        if not self.bm25 or not self.corpus:
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        # Pair scores with documents and sort
        scored_docs = list(zip(scores, self.documents))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored_docs[:top_k]:
            if score > 0:
                result = doc.copy()
                result["bm25_score"] = float(score)
                result["source"] = "bm25"
                results.append(result)

        logger.info(f"BM25 search '{query}': {len(results)} results")
        return results


# Global index instance
bm25_index = BM25Index()
