import asyncio
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
    # Split the main keywords by comma and wrap each in quotes if they contain spaces
    keywords = [k.strip() for k in issue.keyword.split(",") if k.strip()]
    core_terms = []
    for kw in keywords:
        if " " in kw:
            core_terms.append(f'"{kw}"')
        else:
            core_terms.append(kw)
            
    if core_terms:
        core_query_part = " OR ".join(core_terms)
    else:
        core_query_part = f'"{issue.keyword}"'

    regional_terms = []
    
    if issue.wilayah and issue.wilayah != "Aceh (Keseluruhan)":
        clean_wilayah = issue.wilayah.replace("Kabupaten ", "").replace("Kota ", "")
        regional_terms.append(f'"{clean_wilayah}"')
        
    if issue.keyword_regional:
        for kw in issue.keyword_regional.split(','):
            cleaned_kw = kw.strip()
            if cleaned_kw:
                regional_terms.append(f'"{cleaned_kw}"')
                
    if regional_terms:
        regional_query_part = " OR ".join(regional_terms)
        search_query = f'({core_query_part}) AND ({regional_query_part})'
    else:
        search_query = f'({core_query_part}) AND "Aceh"'
        
    if time_filter and time_filter != "all":
        search_query = f"{search_query} when:{time_filter}"

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
            
            # Proactively sleep 4.1s to respect Gemini API rate limits (15 RPM)
            await asyncio.sleep(4.1)
            
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


async def scrape_tiktok_comments(
    keyword: str,
    db: Session,
    max_records: int = 50
) -> List[SentimentData]:
    """
    Scrapes TikTok comments related to the given keyword using RapidAPI tiktok-api23,
    classifies their sentiments using IndoBERT, and stores them in database.
    """
    if not settings.rapidapi_tiktok_key:
        raise ValueError("Konfigurasi RAPIDAPI_TIKTOK_KEY belum diatur di file .env. Fitur TikTok memerlukan API Key.")

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

    headers = {
        "x-rapidapi-key": settings.rapidapi_tiktok_key,
        "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
    }

    # For TikTok, we split the keywords by comma and run searches in a loop to collect unique videos
    keywords = [k.strip() for k in issue.keyword.split(",") if k.strip()]
    if not keywords:
        keywords = [issue.keyword.strip()]

    videos = []
    saved_records: List[SentimentData] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Loop through the first 3 keywords to search for videos
            for kw in keywords[:3]:
                tiktok_search_terms = [kw]
                if issue.wilayah and issue.wilayah != "Aceh (Keseluruhan)":
                    clean_wilayah = issue.wilayah.replace("Kabupaten ", "").replace("Kota ", "")
                    tiktok_search_terms.append(clean_wilayah)
                    
                if issue.keyword_regional:
                    kws = [k.strip() for k in issue.keyword_regional.split(',') if k.strip()]
                    if kws:
                        tiktok_search_terms.append(kws[0])
                        
                tiktok_query = " ".join(tiktok_search_terms)
                logger.info("Starting TikTok search for query '%s'...", tiktok_query)

                try:
                    search_url = "https://tiktok-api23.p.rapidapi.com/api/search/video"
                    search_params = {"keyword": tiktok_query, "count": "5", "cursor": "0"}
                    response = await client.get(search_url, headers=headers, params=search_params)
                    response.raise_for_status()
                    search_data = response.json()
                    
                    kw_videos = []
                    if isinstance(search_data, dict):
                        if search_data.get("status") == "failed":
                            logger.error("TikTok API returned failed status for query %s: %s", tiktok_query, search_data.get("msg"))
                            continue
                        data_section = search_data.get("data") or search_data
                        if isinstance(data_section, dict):
                            kw_videos = data_section.get("videos") or data_section.get("items") or data_section.get("posts") or data_section.get("item_list") or data_section.get("itemList") or data_section.get("itemList") or []
                        elif isinstance(data_section, list):
                            kw_videos = data_section
                            
                    for v in kw_videos:
                        if isinstance(v, dict):
                            video_id = v.get("video_id") or v.get("aweme_id") or v.get("id")
                            if video_id and not any((vid.get("video_id") == video_id or vid.get("id") == video_id) for vid in videos):
                                videos.append(v)
                except Exception as search_err:
                    logger.error("TikTok search failed for query %s: %s", tiktok_query, search_err)
                    continue
            
            if not videos:
                logger.info("No TikTok videos found for keywords list: %s.", keywords)
                return []

            logger.info("Found %d unique TikTok videos across keywords, retrieving comments...", len(videos))

            # 2. Iterate videos and get comments
            for video in videos:

                if len(saved_records) >= max_records:
                    break

                video_id = None
                if isinstance(video, dict):
                    video_id = video.get("video_id") or video.get("aweme_id") or video.get("id")
                
                if not video_id:
                    continue

                comments_url = "https://tiktok-api23.p.rapidapi.com/api/post/comments"
                comments_params = {"videoId": str(video_id), "count": "20", "cursor": "0"}
                
                try:
                    comments_resp = await client.get(comments_url, headers=headers, params=comments_params)
                    comments_resp.raise_for_status()
                    comments_data = comments_resp.json()
                    
                    comments = []
                    if isinstance(comments_data, dict):
                        data_section = comments_data.get("data") or comments_data
                        if isinstance(data_section, dict):
                            comments = data_section.get("comments") or data_section.get("items") or []
                        elif isinstance(data_section, list):
                            comments = data_section
                    
                    if not comments:
                        continue

                    for comment in comments:
                        if len(saved_records) >= max_records:
                            break

                        comment_text = None
                        if isinstance(comment, dict):
                            comment_text = comment.get("text") or comment.get("comment_text") or comment.get("desc")
                        
                        if not comment_text or not comment_text.strip():
                            continue

                        # Analyze sentiment
                        sentiment_label, confidence = await analyze_sentiment(comment_text)
                        
                        sentiment_mapping = {
                            "positif": "pos",
                            "negatif": "neg",
                            "netral": "netral"
                        }
                        db_sentiment = sentiment_mapping.get(sentiment_label, "netral")

                        sentiment_record = SentimentData(
                            issue_id=issue.id,
                            teks=comment_text[:2000],
                            platform=f"TikTok (Video: {video_id})",
                            sentimen=db_sentiment,
                            confidence_score=confidence
                        )
                        db.add(sentiment_record)
                        saved_records.append(sentiment_record)

                        # Proactively sleep 4.1s to respect Gemini API rate limits (15 RPM)
                        await asyncio.sleep(4.1)

                except Exception as e:
                    logger.warning("Failed to retrieve or process comments for video %s: %s", video_id, e)
                    continue



        if saved_records:
            try:
                db.commit()
                for record in saved_records:
                    db.refresh(record)
                logger.info("Successfully saved %s TikTok comments to database.", len(saved_records))
            except Exception as e:
                db.rollback()
                logger.error("Failed to commit TikTok comments: %s", e)
                raise RuntimeError("Failed to persist scraped TikTok comments.") from e

    except Exception as e:
        logger.error("Failed to complete TikTok comments scraping: %s", e)
        raise e

    return saved_records

