import logging
import urllib.parse
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from .config import settings
from .ai_engine import analyze_sentiment
from .models import Issue, SentimentData

logger = logging.getLogger("app.scraper")

# Target news portal search URL (HTTPS is enforced for security)
BASE_SEARCH_URL = "https://www.antaranews.com/search"

async def scrape_and_store_sentiment(keyword: str, db: Session) -> List[SentimentData]:
    """
    Scrapes news articles from Antara News by keyword, analyzes their sentiment,
    saves the results to the SentimentData database table, and returns the saved records.
    
    Args:
        keyword (str): The search keyword based on an active issue.
        db (Session): The SQLAlchemy database session.

    Returns:
        List[SentimentData]: A list of newly created and stored SentimentData records (max 100).

    Raises:
        ValueError: If no active issue matches the keyword or input validation fails.
        RuntimeError: If scraping or database operations fail.
    """
    # 1. Input validation & sanitization
    if not keyword or not isinstance(keyword, str):
        raise ValueError("Keyword must be a non-empty string.")
    
    sanitized_keyword = keyword.strip()
    if not sanitized_keyword:
        raise ValueError("Keyword cannot consist only of whitespace.")

    # 2. Look up the active issue associated with this keyword
    # Fallback checks both exact keyword match and partial match, prioritizing exact match
    issue = db.query(Issue).filter(Issue.keyword == sanitized_keyword, Issue.is_active == True).first()
    if not issue:
        issue = db.query(Issue).filter(
            (Issue.keyword.ilike(f"%{sanitized_keyword}%") | Issue.nama_isu.ilike(f"%{sanitized_keyword}%")),
            Issue.is_active == True
        ).first()

    if not issue:
        logger.error("Failed to find any active issue in database matching keyword: '%s'", sanitized_keyword)
        raise ValueError(f"No active issue found in the database for keyword: '{sanitized_keyword}'")

    saved_records: List[SentimentData] = []
    page_num = 1
    max_records = 100

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    logger.info("Starting scrape process for keyword '%s' (Issue ID: %s)...", sanitized_keyword, issue.id)

    # Scrape loop, running until we reach 100 records, there are no more pages, or we exceed page limit
    max_pages = 10
    while len(saved_records) < max_records and page_num <= max_pages:
        # Build search URL with query parameters
        params = {
            "q": sanitized_keyword,
            "page": page_num
        }
        
        try:
            # Synchronous requests call to fetch the page
            response = requests.get(BASE_SEARCH_URL, params=params, headers=headers, timeout=15.0)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch search page %s for keyword '%s': %s", page_num, sanitized_keyword, e)
            # If the first page fails completely, raise an error. Otherwise, break and save what we have.
            if page_num == 1:
                raise RuntimeError(f"Failed to initiate scraping for keyword '{sanitized_keyword}': {e}") from e
            break

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Locate article cards in Antara News search results
        cards = soup.find_all(class_="card__post__content")
        if not cards:
            logger.info("No more articles found for keyword '%s' at page %s.", sanitized_keyword, page_num)
            break

        page_processed_count = 0
        for card in cards:
            if len(saved_records) >= max_records:
                break

            # Parse title
            title = ""
            title_div = card.find(class_="card__post__title")
            if title_div:
                a_tag = title_div.find("a")
                if a_tag:
                    title = a_tag.text.strip()
            if not title:
                # Fallback to direct anchor tag search
                a_tag = card.find("a")
                if a_tag:
                    title = a_tag.text.strip()

            # Parse summary
            summary = ""
            p_tag = card.find("p")
            if p_tag:
                summary = p_tag.text.strip()

            # Skip if both title and summary are empty
            if not title and not summary:
                continue

            # Combine title and summary for rich sentiment context
            combined_text = f"{title}. {summary}" if title and summary else (title or summary)

            try:
                # Call the async sentiment analysis function
                sentiment_label, confidence = await analyze_sentiment(combined_text)
                
                # Map the full label back to the database constraint format ('pos', 'neg', 'netral')
                # DB CheckConstraint: sentimen IN ('pos', 'neg', 'netral')
                sentiment_mapping = {
                    "positif": "pos",
                    "negatif": "neg",
                    "netral": "netral"
                }
                db_sentiment = sentiment_mapping.get(sentiment_label, "netral")

                # Create SentimentData instance
                sentiment_record = SentimentData(
                    issue_id=issue.id,
                    teks=combined_text,
                    platform="Antara News",
                    sentimen=db_sentiment,
                    confidence_score=confidence
                )
                
                # Add to DB session
                db.add(sentiment_record)
                saved_records.append(sentiment_record)
                page_processed_count += 1
                
            except Exception as e:
                # Gracefully handle single article sentiment errors to avoid failing the entire batch
                logger.warning("Failed to analyze sentiment for article '%s': %s", title[:30], e)
                continue

        logger.info("Processed %s articles on page %s.", page_processed_count, page_num)
        page_num += 1

    # 3. Commit the transaction to the database
    if saved_records:
        try:
            db.commit()
            # Refresh instances to populate auto-generated IDs
            for record in saved_records:
                db.refresh(record)
            logger.info("Successfully saved %s sentiment records to the database.", len(saved_records))
        except Exception as e:
            db.rollback()
            logger.error("Database transaction failed, rolling back changes: %s", e)
            raise RuntimeError("Failed to persist scraped sentiment records in the database.") from e
            
    return saved_records
