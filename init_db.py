import logging
from app.database import engine, Base
# Import models to register them on Base.metadata
from app.models import Issue, SentimentData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("init_db")

def init_db():
    logger.info("Initializing database tables for 'Aceh Sentimen Analisis'...")
    try:
        # Create all tables defined in models.py
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error("Failed to create database tables: %s", e)
        raise e

if __name__ == "__main__":
    init_db()
