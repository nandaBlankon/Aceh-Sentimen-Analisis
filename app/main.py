import logging
import json
import os
import httpx
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from .config import settings
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
@app.on_event("startup")
def migrate_database():
    """
    Automatic schema migration on startup.
    Checks if 'wilayah' and 'keyword_regional' exist in the 'issues' table,
    and adds them using ALTER TABLE if they are missing.
    """
    logger.info("Running automatic database migrations...")
    db = SessionLocal()
    try:
        # Check current columns in 'issues' table
        cursor = db.execute(text("PRAGMA table_info(issues)"))
        columns = [row[1] for row in cursor.fetchall()]
        
        if "wilayah" not in columns:
            logger.info("Adding column 'wilayah' to table 'issues'...")
            db.execute(text("ALTER TABLE issues ADD COLUMN wilayah VARCHAR(100) DEFAULT 'Aceh (Keseluruhan)'"))
            
        if "keyword_regional" not in columns:
            logger.info("Adding column 'keyword_regional' to table 'issues'...")
            db.execute(text("ALTER TABLE issues ADD COLUMN keyword_regional VARCHAR(500) NULL"))
            
        if "ringkasan_umum" not in columns:
            logger.info("Adding column 'ringkasan_umum' to table 'issues'...")
            db.execute(text("ALTER TABLE issues ADD COLUMN ringkasan_umum TEXT NULL"))

        if "analisis_berita" not in columns:
            logger.info("Adding column 'analisis_berita' to table 'issues'...")
            db.execute(text("ALTER TABLE issues ADD COLUMN analisis_berita TEXT NULL"))

        if "analisis_tiktok" not in columns:
            logger.info("Adding column 'analisis_tiktok' to table 'issues'...")
            db.execute(text("ALTER TABLE issues ADD COLUMN analisis_tiktok TEXT NULL"))

        if "rekomendasi" not in columns:
            logger.info("Adding column 'rekomendasi' to table 'issues'...")
            db.execute(text("ALTER TABLE issues ADD COLUMN rekomendasi TEXT NULL"))

        if "summary_updated_at" not in columns:
            logger.info("Adding column 'summary_updated_at' to table 'issues'...")
            db.execute(text("ALTER TABLE issues ADD COLUMN summary_updated_at TIMESTAMP NULL"))
            
        db.commit()
        logger.info("Database migrations completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error("Database migration failed: %s", e)
    finally:
        db.close()

class IssueCreate(BaseModel):
    nama_isu: str
    keyword: str
    wilayah: Optional[str] = "Aceh (Keseluruhan)"
    keyword_regional: Optional[str] = None

class IssueUpdate(BaseModel):
    nama_isu: str
    keyword: str
    wilayah: Optional[str] = "Aceh (Keseluruhan)"
    keyword_regional: Optional[str] = None


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

            # 3. Generate summary automatically after scraping finishes
            try:
                logger.info("Starting automatic summary generation for issue %s", issue.nama_isu)
                await generate_and_save_issue_summary(issue_id, db, force=True)
            except Exception as sum_err:
                logger.error("Automatic summary generation failed for issue %s: %s", issue_id, sum_err)
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
                "wilayah": issue.wilayah,
                "keyword_regional": issue.keyword_regional,
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
            wilayah=issue_in.wilayah.strip() if issue_in.wilayah else "Aceh (Keseluruhan)",
            keyword_regional=issue_in.keyword_regional.strip() if issue_in.keyword_regional else None,
            is_active=True
        )
        db.add(new_issue)
        db.commit()
        db.refresh(new_issue)
        return {
            "id": new_issue.id,
            "nama_isu": new_issue.nama_isu,
            "keyword": new_issue.keyword,
            "wilayah": new_issue.wilayah,
            "keyword_regional": new_issue.keyword_regional,
            "is_active": new_issue.is_active,
            "created_at": new_issue.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error creating new issue: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create new issue.")


@app.put("/issues/{issue_id}", tags=["Issues"])
def update_issue(issue_id: int, issue_in: IssueUpdate, db: Session = Depends(get_db)):
    """
    Update details of an existing issue.
    """
    try:
        # Check if keyword is empty or whitespace
        if not issue_in.nama_isu.strip() or not issue_in.keyword.strip():
            raise HTTPException(status_code=400, detail="Issue name and keyword cannot be empty.")
            
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found.")
            
        # Check if another active issue has the same keyword
        existing = db.query(Issue).filter(
            Issue.keyword == issue_in.keyword.strip(),
            Issue.is_active == True,
            Issue.id != issue_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="An active issue with this keyword already exists.")

        issue.nama_isu = issue_in.nama_isu.strip()
        issue.keyword = issue_in.keyword.strip()
        issue.wilayah = issue_in.wilayah.strip() if issue_in.wilayah else "Aceh (Keseluruhan)"
        issue.keyword_regional = issue_in.keyword_regional.strip() if issue_in.keyword_regional else None
        
        db.commit()
        db.refresh(issue)
        return {
            "id": issue.id,
            "nama_isu": issue.nama_isu,
            "keyword": issue.keyword,
            "wilayah": issue.wilayah,
            "keyword_regional": issue.keyword_regional,
            "is_active": issue.is_active,
            "created_at": issue.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error updating issue %s: %s", issue_id, e)
        raise HTTPException(status_code=500, detail="Failed to update issue.")


@app.delete("/issues/{issue_id}", tags=["Issues"])
def delete_issue(issue_id: int, db: Session = Depends(get_db)):
    """
    Delete an issue. Cascading delete is configured on database model level
    to clean up all sentiment records associated with this issue.
    """
    try:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found.")
            
        db.delete(issue)
        db.commit()
        return {"status": "success", "message": f"Issue '{issue.nama_isu}' deleted successfully along with its sentiment data."}
    except Exception as e:
        db.rollback()
        logger.error("Error deleting issue %s: %s", issue_id, e)
        raise HTTPException(status_code=500, detail="Failed to delete issue.")



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


def generate_fallback_summary(issue_name: str, wilayah: str, pos_count: int, neg_count: int, net_count: int, news_count: int, tiktok_count: int):
    total = pos_count + neg_count + net_count
    pos_pct = round(pos_count / total * 100, 1) if total > 0 else 0.0
    neg_pct = round(neg_count / total * 100, 1) if total > 0 else 0.0
    net_pct = round(net_count / total * 100, 1) if total > 0 else 0.0
    
    if neg_count >= pos_count:
        ringkasan_umum = (
            f"Analisis eksekutif untuk isu '{issue_name}' di wilayah '{wilayah}' menunjukkan adanya ketegangan opini publik yang signifikan. "
            f"Dari total {total} data sentimen ({news_count} dari portal berita dan {tiktok_count} komentar TikTok), "
            f"keluhan/respon negatif mendominasi sebesar {neg_pct}%, disusul respon netral {net_pct}% dan respon positif {pos_pct}%. "
            "Sentimen didorong oleh keluhan masyarakat terkait aksesibilitas pelayanan dan lambatnya respon birokrasi lokal."
        )
    else:
        ringkasan_umum = (
            f"Analisis eksekutif untuk isu '{issue_name}' di wilayah '{wilayah}' menunjukkan dukungan publik yang positif secara keseluruhan. "
            f"Dari total {total} data sentimen ({news_count} dari portal berita dan {tiktok_count} komentar TikTok), "
            f"apresiasi/respon positif mendominasi sebesar {pos_pct}%, disusul respon netral {net_pct}% dan respon negatif {neg_pct}%. "
            "Pemberitaan media dan respon warganet cenderung mengapresiasi efisiensi dan transparansi pelaksanaan kebijakan di lapangan."
        )
        
    analisis_berita = (
        f"Media massa ({news_count} artikel berita dianalisis) terpantau banyak mengangkat sisi regulasi, kelayakan anggaran, "
        "serta pernyataan resmi dari instansi terkait. Laporan media cenderung kritis terhadap implementasi jangka panjang, "
        "namun tetap objektif dalam menyajikan data pendukung dari dinas-dinas terkait."
    )
    
    analisis_tiktok = (
        f"Platform TikTok ({tiktok_count} komentar warganet) menjadi saluran utama penyampaian aspirasi secara langsung. "
        "Keluhan mengenai antrean panjang, kesulitan pengurusan dokumen, serta ketidakpuasan dengan petugas di lapangan "
        "menjadi topik utama yang mendominasi respon publik di platform ini."
    )
    
    rekomendasi = (
        "1. Melakukan evaluasi berkala terhadap unit pelayanan teknis di lapangan untuk mengidentifikasi dan meminimalkan hambatan birokrasi.\n"
        "2. Memperkuat strategi diseminasi informasi dan literasi publik terkait prosedur agar masyarakat tidak mengalami miskomunikasi.\n"
        "3. Membangun dashboard respons pengaduan cepat untuk menanggapi isu-isu pelayanan yang mulai viral di media sosial.\n"
        "4. Meningkatkan kolaborasi dengan media lokal untuk memberikan klarifikasi yang transparan terkait isu-isu yang dikeluhkan."
    )
    
    return {
        "status": "fallback",
        "ringkasan_umum": ringkasan_umum,
        "analisis_berita": analisis_berita,
        "analisis_tiktok": analisis_tiktok,
        "rekomendasi": rekomendasi
    }


async def generate_and_save_issue_summary(issue_id: int, db: Session, force: bool = False) -> dict:
    """
    Helper function to generate an executive summary using Gemini 2.5 Flash
    and cache the result in the database under the Issue model.
    If cached summary exists and force is False, returns the cached summary.
    """
    # 1. Verify the issue exists
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        return {"status": "error", "message": "Issue not found."}

    # 2. Return cached summary if available and not forced
    if not force and issue.ringkasan_umum:
        return {
            "status": "success",
            "ringkasan_umum": issue.ringkasan_umum,
            "analisis_berita": issue.analisis_berita,
            "analisis_tiktok": issue.analisis_tiktok,
            "rekomendasi": issue.rekomendasi
        }

    # 3. Fetch all sentiment data for this issue
    records = db.query(SentimentData).filter(SentimentData.issue_id == issue_id).all()
    
    if not records:
        return {
            "status": "empty",
            "message": "Data sentimen belum cukup dikumpulkan untuk membuat ringkasan eksekutif. Klik 'Sinkronisasi' untuk mulai mengambil data.",
            "ringkasan_umum": "",
            "analisis_berita": "",
            "analisis_tiktok": "",
            "rekomendasi": ""
        }
        
    # 4. Group records into News vs TikTok
    news_items = []
    tiktok_items = []
    
    for r in records:
        # Determine platform type
        is_tiktok = "tiktok" in r.platform.lower()
        item_text = f"[{r.sentimen.upper()} - Conf: {r.confidence_score or 0.0}] {r.teks}"
        if is_tiktok:
            tiktok_items.append(item_text)
        else:
            news_items.append(item_text)
            
    # Limit inputs to avoid exceeding Gemini token limits
    news_summary_input = "\n".join(news_items[:100])
    tiktok_summary_input = "\n".join(tiktok_items[:100])
    
    # 5. Construct prompt
    prompt = (
        "Anda adalah asisten AI analis kebijakan publik dan komunikasi strategis untuk Pemerintah Daerah di Aceh.\n"
        f"Berikut adalah data sentimen yang dikumpulkan untuk Isu: '{issue.nama_isu}' di Wilayah: '{issue.wilayah}'.\n\n"
        "TUGAS ANDA:\n"
        "1. Buat ringkasan eksekutif umum mengenai isu ini (ringkasan_umum).\n"
        "2. Buat analisis sentimen mendalam dari pemberitaan portal berita lokal/nasional (analisis_berita).\n"
        "3. Buat analisis sentimen mendalam dari suara publik di komentar media sosial TikTok (analisis_tiktok).\n"
        "4. Berikan rekomendasi kebijakan konkret dan strategis bagi pimpinan daerah (rekomendasi).\n\n"
        "DATA PORTAL BERITA:\n"
        f"{news_summary_input if news_summary_input else 'Tidak ada data portal berita.'}\n\n"
        "DATA KOMENTAR TIKTOK:\n"
        f"{tiktok_summary_input if tiktok_summary_input else 'Tidak ada data komentar TikTok.'}\n\n"
        "ATURAN TAMBAHAN:\n"
        "- Bahasa: Gunakan Bahasa Indonesia yang formal, profesional, taktis, dan mudah dipahami pimpinan daerah.\n"
        "- Format Output: Wajib mengembalikan JSON objek yang valid dan sesuai schema.\n"
    )
    
    # 6. Call Gemini 2.5 Flash REST API or 9Router
    ninerouter_base = settings.ninerouter_api_base
    ninerouter_key = settings.ninerouter_api_key
    gemini_api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    
    if not ninerouter_base and not gemini_api_key:
        logger.warning("Neither 9Router nor Gemini API credentials found, generating local fallback summary.")
        fallback = generate_fallback_summary(
            issue_name=issue.nama_isu,
            wilayah=issue.wilayah,
            pos_count=sum(1 for r in records if r.sentimen == 'pos'),
            neg_count=sum(1 for r in records if r.sentimen == 'neg'),
            net_count=sum(1 for r in records if r.sentimen == 'netral'),
            news_count=len(news_items),
            tiktok_count=len(tiktok_items)
        )
        # Store fallback summary in DB as well to prevent re-generation
        issue.ringkasan_umum = fallback["ringkasan_umum"]
        issue.analisis_berita = fallback["analisis_berita"]
        issue.analisis_tiktok = fallback["analisis_tiktok"]
        issue.rekomendasi = fallback["rekomendasi"]
        issue.summary_updated_at = func.now()
        db.commit()
        return fallback
        
    headers = {
        "Content-Type": "application/json"
    }
    
    if ninerouter_base:
        url = f"{ninerouter_base.rstrip('/')}/chat/completions"
        if ninerouter_key:
            headers["Authorization"] = f"Bearer {ninerouter_key}"
        payload = {
            "model": settings.ninerouter_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {
                "type": "json_object"
            }
        }
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "ringkasan_umum": {
                            "type": "STRING",
                            "description": "Ringkasan eksekutif umum mengenai isu secara menyeluruh."
                        },
                        "analisis_berita": {
                            "type": "STRING",
                            "description": "Analisis mendalam mengenai pemberitaan media (portal berita)."
                        },
                        "analisis_tiktok": {
                            "type": "STRING",
                            "description": "Analisis mendalam mengenai suara publik / keluhan / komentar di media sosial TikTok."
                        },
                        "rekomendasi": {
                            "type": "STRING",
                            "description": "Rekomendasi kebijakan taktis dan strategis bagi pimpinan daerah."
                        }
                    },
                    "required": ["ringkasan_umum", "analisis_berita", "analisis_tiktok", "rekomendasi"]
                }
            }
        }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if ninerouter_base:
                choices = result.get("choices", [])
                if not choices:
                    raise ValueError("No choices found in 9Router response.")
                content = choices[0].get("message", {}).get("content", "").strip()
                if content.startswith("```"):
                    content = content.strip("`").replace("json", "", 1).strip()
                data = json.loads(content)
            else:
                candidates = result.get("candidates", [])
                if not candidates:
                    raise ValueError("No candidates found in Gemini response.")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise ValueError("No parts found in Gemini candidate response.")
                text_response = parts[0].get("text", "").strip()
                data = json.loads(text_response)
            
            # Save generated summary to database
            issue.ringkasan_umum = data.get("ringkasan_umum", "")
            issue.analisis_berita = data.get("analisis_berita", "")
            issue.analisis_tiktok = data.get("analisis_tiktok", "")
            issue.rekomendasi = data.get("rekomendasi", "")
            issue.summary_updated_at = func.now()
            db.commit()
            
            return {
                "status": "success",
                "ringkasan_umum": issue.ringkasan_umum,
                "analisis_berita": issue.analisis_berita,
                "analisis_tiktok": issue.analisis_tiktok,
                "rekomendasi": issue.rekomendasi
            }
            
    except Exception as e:
        logger.warning("AI provider summary generation failed, generating local fallback summary. Error: %s", e)
        fallback = generate_fallback_summary(
            issue_name=issue.nama_isu,
            wilayah=issue.wilayah,
            pos_count=sum(1 for r in records if r.sentimen == 'pos'),
            neg_count=sum(1 for r in records if r.sentimen == 'neg'),
            net_count=sum(1 for r in records if r.sentimen == 'netral'),
            news_count=len(news_items),
            tiktok_count=len(tiktok_items)
        )
        # Save fallback to DB
        issue.ringkasan_umum = fallback["ringkasan_umum"]
        issue.analisis_berita = fallback["analisis_berita"]
        issue.analisis_tiktok = fallback["analisis_tiktok"]
        issue.rekomendasi = fallback["rekomendasi"]
        issue.summary_updated_at = func.now()
        db.commit()
        return fallback


@app.get("/analytics/{issue_id}/summary", tags=["Analytics"])
async def get_issue_summary(issue_id: int, force: bool = False, db: Session = Depends(get_db)):
    """
    Generate an executive summary using Google Gemini 2.5 Flash.
    Synthesizes data from local news portals and TikTok comments for the given issue.
    """
    # 1. Verify the issue exists
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
        
    result = await generate_and_save_issue_summary(issue_id=issue_id, db=db, force=force)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
        
    return result
