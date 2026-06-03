from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

# Set up engine. pool_pre_ping=True checks connection health to recover from DB restarts.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# Set up session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for models
class Base(DeclarativeBase):
    pass

# Dependency to get db session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
