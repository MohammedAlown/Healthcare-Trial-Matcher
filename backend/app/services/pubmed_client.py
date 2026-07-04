"""
pubmed_client.py - PubMed E-utilities API Client

PubMed (run by NCBI/NIH) provides free access to biomedical literature
through their E-utilities API. No API key required for basic usage.

The process:
  1. ESearch: Send a search term → get back a list of PubMed IDs (PMIDs)
  2. EFetch: Send PMIDs → get back full article details in XML

API Docs: https://www.ncbi.nlm.nih.gov/books/NBK25500/

Rate Limit: 3 requests/second without API key (enough for us).
"""

import httpx
import xmltodict
from typing import Optional
from backend.app.core.logger import logger


# NCBI E-utilities base URLs
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


async def search_pubmed(
    query: str,
    max_results: int = 20,
) -> list[str]:
    """
    Search PubMed and return a list of PMIDs (article IDs).

    Args:
        query: Search term (e.g. "lung cancer immunotherapy")
        max_results: Maximum number of PMIDs to return

    Returns:
        List of PMID strings (e.g. ["12345678", "23456789"])
    """
    params = {
        "db": "pubmed",            # Search the PubMed database
        "term": query,             # Search query
        "retmax": max_results,     # Max results to return
        "retmode": "json",         # Return JSON format
        "sort": "relevance",       # Sort by relevance
    }

    logger.info(f"Searching PubMed for: '{query}' (max: {max_results})")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ESEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

    pmids = data.get("esearchresult", {}).get("idlist", [])
    logger.info(f"Found {len(pmids)} PMIDs")

    return pmids


async def fetch_articles(pmids: list[str]) -> list[dict]:
    """
    Fetch full article details for a list of PMIDs.

    Args:
        pmids: List of PubMed IDs to fetch

    Returns:
        List of raw article dictionaries parsed from XML
    """
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),     # Comma-separated PMIDs
        "retmode": "xml",          # XML has the most detail
        "rettype": "abstract",     # Include abstracts
    }

    logger.info(f"Fetching {len(pmids)} articles from PubMed")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(EFETCH_URL, params=params)
        response.raise_for_status()

    # Parse XML response into a Python dictionary
    data = xmltodict.parse(response.text)

    # Handle single vs multiple articles
    articles_raw = data.get("PubmedArticleSet", {}).get("PubmedArticle", [])

    # If only one article, xmltodict returns a dict instead of a list
    if isinstance(articles_raw, dict):
        articles_raw = [articles_raw]

    logger.info(f"Fetched {len(articles_raw)} articles")

    return articles_raw
