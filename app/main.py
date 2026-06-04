import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from .database import get_db, SessionLocal
from .models import Issue, SentimentData
from .scraper import scrape_and_store_sentiment, scrape_tiktok_comments

logger = logging.getLogger("app.main")

app = FastAPI(
    title="Aceh Sentimen Analisis API",
    description="Backend API for Aceh Sentimen Analisis System",
    version="0.1.0"
)

# Enable CORS (Cross-Origin Resource Sharing) so the frontend can call these APIs
# TODO(security): Restrict allowed origins in production instead of using wildcard '*'
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IssueCreate(BaseModel):
    nama_isu: str
    keyword: str

class ScrapeOptions(BaseModel):
    max_records: int = 50
    time_filter: str = "7d"

async def run_background_scrape(issue_id: int, options: ScrapeOptions):
    """
    Background task to execute scraping with a standalone DB session.
    """
    db = SessionLocal()
    try:
        issue = db.query(Issue).filter(Issue.id == issue_id, Issue.is_active == True).first()
        if issue:
            # 1. Scrape Google News
            try:
                logger.info("Starting Google News scraping for issue %s", issue.nama_isu)
                await scrape_and_store_sentiment(issue.keyword, db, options.max_records, options.time_filter)
            except Exception as news_err:
                logger.error("Google News scraping failed for issue %s: %s", issue_id, news_err)

            # 2. Scrape TikTok comments
            try:
                logger.info("Starting TikTok comments scraping for issue %s", issue.nama_isu)
                await scrape_tiktok_comments(issue.keyword, db, options.max_records)
            except Exception as tiktok_err:
                logger.error("TikTok comments scraping failed for issue %s: %s", issue_id, tiktok_err)
        else:
            logger.error("Active issue not found in background task for id %s", issue_id)
    except Exception as e:
        logger.error("Background scrape failed for issue %s: %s", issue_id, e)
    finally:
        db.close()


@app.get("/health", tags=["System"])
def health_check():
    """
    Check the application status.
    """
    return {"status": "healthy"}

@app.get("/db-check", tags=["System"])
def db_check(db: Session = Depends(get_db)):
    """
    Verify the database connection.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as e:
        # Secure error handling: log the actual error for developers, return generic error to user
        logger.error("Database connection failure: %s", e)
        return {"database": "disconnected", "error": "Unable to establish database connection."}


@app.get("/issues", tags=["Issues"])
def get_issues(active_only: bool = False, db: Session = Depends(get_db)):
    """
    Fetch issues from the database. Optionally filter for active ones.
    """
    try:
        query = db.query(Issue)
        if active_only:
            query = query.filter(Issue.is_active == True)
        issues = query.order_by(Issue.created_at.desc()).all()
        
        # Query total records per issue
        counts = db.query(
            SentimentData.issue_id,
            func.count(SentimentData.id).label("count")
        ).group_by(SentimentData.issue_id).all()
        counts_map = {c.issue_id: c.count for c in counts}
        
        return [
            {
                "id": issue.id,
                "nama_isu": issue.nama_isu,
                "keyword": issue.keyword,
                "created_at": issue.created_at,
                "is_active": issue.is_active,
                "total_records": counts_map.get(issue.id, 0)
            }
            for issue in issues
        ]
    except Exception as e:
        logger.error("Error retrieving issues: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve issues.")


@app.post("/issues", tags=["Issues"])
def create_issue(issue_in: IssueCreate, db: Session = Depends(get_db)):
    """
    Create a new issue to track.
    """
    try:
        # Check if keyword is empty or whitespace
        if not issue_in.nama_isu.strip() or not issue_in.keyword.strip():
            raise HTTPException(status_code=400, detail="Issue name and keyword cannot be empty.")
            
        # Check if active issue with this keyword already exists
        existing = db.query(Issue).filter(
            Issue.keyword == issue_in.keyword.strip(), 
            Issue.is_active == True
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="An active issue with this keyword already exists.")

        new_issue = Issue(
            nama_isu=issue_in.nama_isu.strip(),
            keyword=issue_in.keyword.strip(),
            is_active=True
        )
        db.add(new_issue)
        db.commit()
        db.refresh(new_issue)
        return {
            "id": new_issue.id,
            "nama_isu": new_issue.nama_isu,
            "keyword": new_issue.keyword,
            "is_active": new_issue.is_active,
            "created_at": new_issue.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error creating new issue: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create new issue.")


@app.post("/trigger-scrape/{issue_id}", tags=["Scraping"])
async def trigger_scrape(
    issue_id: int,
    options: ScrapeOptions,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger scraping for a specific active issue in the background.
    """
    # Verify active issue exists
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.is_active == True).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Active issue not found.")

    try:
        # Dispatch to background task
        background_tasks.add_task(run_background_scrape, issue_id, options)
        return {
            "status": "processing",
            "message": f"Scraping started in background for issue '{issue.nama_isu}' with limit {options.max_records} and time {options.time_filter}.",
            "data": []
        }
    except Exception as e:
        logger.error("Unexpected error dispatching background task for issue %s: %s", issue_id, e)
        raise HTTPException(status_code=500, detail="Failed to dispatch background scrape.")


@app.get("/analytics/{issue_id}", tags=["Analytics"])
def get_analytics(issue_id: int, db: Session = Depends(get_db)):
    """
    Returns aggregated analytics for a specific issue:
    1. Total data count per platform.
    2. Sentiment percentage distribution (pos, neg, netral).
    3. Daily time-series counts grouped by date and sentiment for Chart.js rendering.
    """
    # Verify the issue exists
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    try:
        # 1. Total data by platform
        platform_counts = db.query(
            SentimentData.platform,
            func.count(SentimentData.id).label("count")
        ).filter(SentimentData.issue_id == issue_id).group_by(SentimentData.platform).all()

        # 2. Sentiment distribution count
        sentiment_counts = db.query(
            SentimentData.sentimen,
            func.count(SentimentData.id).label("count")
        ).filter(SentimentData.issue_id == issue_id).group_by(SentimentData.sentimen).all()

        # 2b. Platform-specific sentiment counts
        plat_sent_counts = db.query(
            SentimentData.platform,
            SentimentData.sentimen,
            func.count(SentimentData.id).label("count")
        ).filter(SentimentData.issue_id == issue_id).group_by(SentimentData.platform, SentimentData.sentimen).all()

        # 3. Daily time-series counts (Aggregated in Python to avoid SQLite date cast issues)
        raw_records = db.query(SentimentData.scraped_at, SentimentData.sentimen)\
                        .filter(SentimentData.issue_id == issue_id).all()

        # Transform database queries into clean response structures
        total_by_platform = {r.platform: r.count for r in platform_counts}

        counts_dict = {r.sentimen: r.count for r in sentiment_counts}
        total_sentiment_count = sum(counts_dict.values())

        sentiment_distribution = {}
        for key in ["pos", "neg", "netral"]:
            count = counts_dict.get(key, 0)
            pct = (count / total_sentiment_count * 100) if total_sentiment_count > 0 else 0.0
            sentiment_distribution[key] = round(pct, 2)

        # Build platform sentiment counts dict
        platform_sentiment_counts = {}
        for r in plat_sent_counts:
            plat = r.platform
            sent = r.sentimen
            cnt = r.count
            if plat not in platform_sentiment_counts:
                platform_sentiment_counts[plat] = {"pos": 0, "neg": 0, "netral": 0}
            platform_sentiment_counts[plat][sent] = cnt

        # Build Daily Time-Series data
        time_series_map = {}
        for r in raw_records:
            if not r.scraped_at:
                continue
            date_str = r.scraped_at.strftime("%Y-%m-%d")
            if date_str not in time_series_map:
                time_series_map[date_str] = {"date": date_str, "pos": 0, "neg": 0, "netral": 0}
            if r.sentimen in time_series_map[date_str]:
                time_series_map[date_str][r.sentimen] += 1

        time_series = list(time_series_map.values())
        time_series.sort(key=lambda x: x["date"])

        return {
            "issue_id": issue_id,
            "nama_isu": issue.nama_isu,
            "total_by_platform": total_by_platform,
            "sentiment_distribution": sentiment_distribution,
            "platform_sentiment_counts": platform_sentiment_counts,
            "time_series": time_series
        }

    except Exception as e:
        logger.error("Error generating analytics for issue %s: %s", issue_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics data.")


@app.get("/feed/{issue_id}", tags=["Analytics"])
def get_feed(issue_id: int, limit: int = 15, db: Session = Depends(get_db)):
    """
    Fetch the latest raw sentiment records for a specific issue to show in the live feed.
    """
    try:
        records = db.query(SentimentData).filter(SentimentData.issue_id == issue_id)\
            .order_by(SentimentData.scraped_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "teks": r.teks,
                "platform": r.platform,
                "sentimen": r.sentimen,
                "confidence_score": round(r.confidence_score, 2) if r.confidence_score else 0.0,
                "scraped_at": r.scraped_at
            }
            for r in records
        ]
    except Exception as e:
        logger.error("Error retrieving feed for issue %s: %s", issue_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve feed data.")
