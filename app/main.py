import logging
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from .database import get_db

app = FastAPI(
    title="Aceh Sentimen Analisis API",
    description="Backend API for Aceh Sentimen Analisis System",
    version="0.1.0"
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
        logging.error("Database connection failure: %s", e)
        return {"database": "disconnected", "error": "Unable to establish database connection."}
