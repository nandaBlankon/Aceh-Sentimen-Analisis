import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from .database import get_db
from .models import Issue, SentimentData
from .scraper import scrape_and_store_sentiment

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
def get_active_issues(db: Session = Depends(get_db)):
    """
    Fetch all active issues from the database.
    """
    try:
        issues = db.query(Issue).filter(Issue.is_active == True).all()
        return [
            {
                "id": issue.id,
                "nama_isu": issue.nama_isu,
                "keyword": issue.keyword,
                "created_at": issue.created_at,
                "is_active": issue.is_active
            }
            for issue in issues
        ]
    except Exception as e:
        logger.error("Error retrieving active issues: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve active issues.")


@app.post("/trigger-scrape/{issue_id}", tags=["Scraping"])
async def trigger_scrape(issue_id: int, db: Session = Depends(get_db)):
    """
    Trigger scraping for a specific active issue, run sentiment analysis,
    and store the results in the SentimentData database table.
    """
    # Verify active issue exists
    issue = db.query(Issue).filter(Issue.id == issue_id, Issue.is_active == True).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Active issue not found.")

    try:
        # Run scraper and store results
        records = await scrape_and_store_sentiment(issue.keyword, db)
        return {
            "status": "success",
            "message": f"Successfully scraped and analyzed {len(records)} articles.",
            "data": [
                {
                    "id": record.id,
                    "teks": record.teks[:100] + "..." if len(record.teks) > 100 else record.teks,
                    "platform": record.platform,
                    "sentimen": record.sentimen,
                    "confidence_score": record.confidence_score
                }
                for record in records
            ]
        }
    except ValueError as e:
        logger.error("Scraper validation error for issue %s: %s", issue_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error during scraping for issue %s: %s", issue_id, e)
        raise HTTPException(status_code=500, detail="Failed to scrape and analyze data.")


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

        # 3. Daily time-series counts
        daily_counts = db.query(
            cast(SentimentData.scraped_at, Date).label("date_only"),
            SentimentData.sentimen,
            func.count(SentimentData.id).label("count")
        ).filter(SentimentData.issue_id == issue_id)\
         .group_by("date_only", SentimentData.sentimen)\
         .order_by("date_only").all()

        # Transform database queries into clean response structures
        total_by_platform = {r.platform: r.count for r in platform_counts}

        counts_dict = {r.sentimen: r.count for r in sentiment_counts}
        total_sentiment_count = sum(counts_dict.values())

        sentiment_distribution = {}
        for key in ["pos", "neg", "netral"]:
            count = counts_dict.get(key, 0)
            pct = (count / total_sentiment_count * 100) if total_sentiment_count > 0 else 0.0
            sentiment_distribution[key] = round(pct, 2)

        # Build Daily Time-Series data
        time_series_map = {}
        for r in daily_counts:
            date_str = r.date_only.strftime("%Y-%m-%d") if r.date_only else "unknown"
            if date_str not in time_series_map:
                time_series_map[date_str] = {"date": date_str, "pos": 0, "neg": 0, "netral": 0}
            time_series_map[date_str][r.sentimen] = r.count

        time_series = list(time_series_map.values())

        return {
            "issue_id": issue_id,
            "nama_isu": issue.nama_isu,
            "total_by_platform": total_by_platform,
            "sentiment_distribution": sentiment_distribution,
            "time_series": time_series
        }
    except Exception as e:
        logger.error("Error generating analytics for issue %s: %s", issue_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics data.")
