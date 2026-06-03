import logging
import urllib.parse
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from .config import settings
from .ai_engine import analyze_sentiment
from .models import Issue, SentimentData

logger = logging.getLogger("app.scraper")

# Target Google News RSS for Indonesian news
BASE_SEARCH_URL = "https://news.google.com/rss/search"

async def scrape_and_store_sentiment(
    keyword: str, 
    db: Session,
    max_records: int = 50,
    time_filter: str = "7d"
) -> List[SentimentData]:
    """
    Scrapes news articles from Google News RSS by keyword, analyzes their sentiment,
    saves the results to the SentimentData database table, and returns the saved records.
    Runs asynchronously using httpx.
    """
    if not keyword or not isinstance(keyword, str):
        raise ValueError("Keyword must be a non-empty string.")
    
    sanitized_keyword = keyword.strip()
    if not sanitized_keyword:
        raise ValueError("Keyword cannot consist only of whitespace.")

    # Find the issue
    issue = db.query(Issue).filter(Issue.keyword == sanitized_keyword, Issue.is_active == True).first()
    if not issue:
        issue = db.query(Issue).filter(
            (Issue.keyword.ilike(f"%{sanitized_keyword}%") | Issue.nama_isu.ilike(f"%{sanitized_keyword}%")),
            Issue.is_active == True
        ).first()

    if not issue:
        logger.error("Failed to find any active issue in database matching keyword: '%s'", sanitized_keyword)
        raise ValueError(f"No active issue found in the database for keyword: '{sanitized_keyword}'")

    # Construct the search query
    # Google News allows search operators like "when:7d" (7 days) or "when:1d" (24 hours)
    search_query = sanitized_keyword
    if time_filter and time_filter != "all":
        search_query = f"{sanitized_keyword} when:{time_filter}"

    params = {
        "q": search_query,
        "hl": "id",
        "gl": "ID",
        "ceid": "ID:id"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    logger.info("Starting scrape process for query '%s' (Issue ID: %s), max_records: %s...", search_query, issue.id, max_records)

    saved_records: List[SentimentData] = []
    
    try:
        # Use httpx AsyncClient to avoid blocking the thread
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(BASE_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
            rss_text = response.text
    except httpx.RequestError as e:
        logger.error("Failed to fetch RSS for query '%s': %s", search_query, e)
        raise RuntimeError(f"Failed to initiate scraping: {e}") from e

    # Parse RSS XML using BeautifulSoup
    # We can use html.parser since it correctly finds <item>, <title>, <description>, <source>
    soup = BeautifulSoup(rss_text, "html.parser")
    items = soup.find_all("item")
    
    if not items:
        logger.info("No articles found for query '%s'.", search_query)
        return []

    for item in items:
        if len(saved_records) >= max_records:
            break

        title = item.find("title").text if item.find("title") else ""
        description = item.find("description").text if item.find("description") else ""
        
        # Google News RSS source tag contains the original publisher name
        source_tag = item.find("source")
        publisher = source_tag.text if source_tag else "Portal Berita"
        
        if not title and not description:
            continue

        # Simple HTML tag strip from description (Google News description has some basic HTML)
        clean_desc_soup = BeautifulSoup(description, "html.parser")
        clean_description = clean_desc_soup.get_text(separator=" ", strip=True)

        combined_text = f"{title}. {clean_description}"

        try:
            # AI Engine analysis
            sentiment_label, confidence = await analyze_sentiment(combined_text)
            
            sentiment_mapping = {
                "positif": "pos",
                "negatif": "neg",
                "netral": "netral"
            }
            db_sentiment = sentiment_mapping.get(sentiment_label, "netral")

            sentiment_record = SentimentData(
                issue_id=issue.id,
                teks=combined_text[:2000],  # Truncate to avoid extreme long texts
                platform=publisher,
                sentimen=db_sentiment,
                confidence_score=confidence
            )
            
            db.add(sentiment_record)
            saved_records.append(sentiment_record)
            
        except Exception as e:
            logger.warning("Failed to analyze sentiment for article '%s': %s", title[:30], e)
            continue

    if saved_records:
        try:
            db.commit()
            for record in saved_records:
                db.refresh(record)
            logger.info("Successfully saved %s sentiment records to the database.", len(saved_records))
        except Exception as e:
            db.rollback()
            logger.error("Database transaction failed, rolling back changes: %s", e)
            raise RuntimeError("Failed to persist scraped sentiment records in the database.") from e
            
    return saved_records
