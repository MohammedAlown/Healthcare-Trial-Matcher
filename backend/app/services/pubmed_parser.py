"""
pubmed_parser.py - Parse PubMed XML Responses

PubMed returns deeply nested XML (converted to dict by xmltodict).
This module extracts the fields we need and flattens them into
dictionaries matching our PubMedArticle database model.

The XML structure (simplified):
  PubmedArticle
    MedlineCitation
      PMID
      Article
        ArticleTitle
        Abstract / AbstractText
        AuthorList / Author
        Journal / Title
        ArticleDate
      MeshHeadingList / MeshHeading
    PubmedData
      ArticleIdList / ArticleId (DOI, etc.)
"""

from typing import Optional
from backend.app.core.logger import logger


def _safe_get(data, *keys, default=None):
    """Safely navigate nested dicts."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current


def _extract_text(value) -> str:
    """
    Extract text from xmltodict values.

    xmltodict sometimes returns:
      - A plain string: "Hello"
      - A dict with #text: {"#text": "Hello", "@Label": "something"}
      - A list of dicts: [{"#text": "Part 1"}, {"#text": "Part 2"}]
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("#text", str(value))
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("#text", ""))
        return " ".join(parts)
    return str(value)


def parse_article(article_raw: dict) -> Optional[dict]:
    """
    Parse a single PubMed article into a flat dictionary.

    Args:
        article_raw: Raw article dict from xmltodict

    Returns:
        Dictionary ready for database insertion, or None if parsing fails
    """
    try:
        citation = article_raw.get("MedlineCitation", {})
        article = citation.get("Article", {})
        pubmed_data = article_raw.get("PubmedData", {})

        # --- PMID ---
        pmid_value = citation.get("PMID", {})
        pmid = _extract_text(pmid_value)

        if not pmid:
            logger.warning("Article missing PMID, skipping")
            return None

        # --- Title ---
        title = _extract_text(article.get("ArticleTitle", ""))

        # --- Abstract ---
        abstract_section = article.get("Abstract", {})
        abstract_text = abstract_section.get("AbstractText", "")
        abstract = _extract_text(abstract_text)

        # --- Authors ---
        author_list = _safe_get(article, "AuthorList", "Author", default=[])
        if isinstance(author_list, dict):
            author_list = [author_list]

        authors = []
        for author in author_list:
            if isinstance(author, dict):
                last = author.get("LastName", "")
                first = author.get("ForeName", "")
                if last:
                    authors.append(f"{last} {first}".strip())

        # --- Journal ---
        journal = _safe_get(
            article, "Journal", "Title", default=""
        )

        # --- Publication Date ---
        pub_date = _safe_get(
            article, "Journal", "JournalIssue", "PubDate", default={}
        )
        year = pub_date.get("Year", "")
        month = pub_date.get("Month", "")
        day = pub_date.get("Day", "")
        publication_date = f"{year} {month} {day}".strip()

        # --- DOI ---
        doi = ""
        article_ids = _safe_get(
            pubmed_data, "ArticleIdList", "ArticleId", default=[]
        )
        if isinstance(article_ids, dict):
            article_ids = [article_ids]
        for aid in article_ids:
            if isinstance(aid, dict) and aid.get("@IdType") == "doi":
                doi = aid.get("#text", "")
                break

        # --- Keywords ---
        keyword_list = _safe_get(
            citation, "KeywordList", "Keyword", default=[]
        )
        if isinstance(keyword_list, str):
            keyword_list = [keyword_list]
        elif isinstance(keyword_list, dict):
            keyword_list = [keyword_list]
        keywords = [_extract_text(k) for k in keyword_list if k]

        # --- MeSH Terms ---
        mesh_list = _safe_get(
            citation, "MeshHeadingList", "MeshHeading", default=[]
        )
        if isinstance(mesh_list, dict):
            mesh_list = [mesh_list]
        mesh_terms = []
        for mesh in mesh_list:
            if isinstance(mesh, dict):
                descriptor = mesh.get("DescriptorName", {})
                mesh_terms.append(_extract_text(descriptor))

        # --- Build result ---
        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors[:20],  # Limit to 20 authors
            "journal": journal,
            "publication_date": publication_date,
            "doi": doi,
            "keywords": keywords,
            "mesh_terms": mesh_terms,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }

    except Exception as e:
        logger.error(f"Error parsing PubMed article: {e}")
        return None


def parse_articles(articles_raw: list[dict]) -> list[dict]:
    """
    Parse multiple PubMed articles.

    Args:
        articles_raw: List of raw article dicts

    Returns:
        List of parsed article dicts ready for database insertion
    """
    parsed = []
    for article in articles_raw:
        result = parse_article(article)
        if result:
            parsed.append(result)

    logger.info(f"Successfully parsed {len(parsed)}/{len(articles_raw)} articles")
    return parsed
