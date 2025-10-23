# server/src/database/connection_py313.py
"""
Database Connection - Python 3.13 Compatible (psycopg3)
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from .models import Base

log = logging.getLogger(__name__)

# Database URL - Use psycopg3 driver for Python 3.13
# Note: Changed from postgresql:// to postgresql+psycopg://
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://suyash.mishra:pass%40123@localhost:5432/uidai_mvp"
)

# Create engine with psycopg3 driver
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable connection pooling for simplicity
    echo=False,  # Set to True for SQL logging
    future=True
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def init_db():
    """Initialize database (create tables)"""
    try:
        Base.metadata.create_all(bind=engine)
        log.info("✅ Database tables created successfully (psycopg3)")
    except Exception as e:
        log.error(f"❌ Failed to create database tables: {e}")
        raise

@contextmanager
def get_db() -> Session:
    """
    Get database session context manager
    
    Usage:
        with get_db() as db:
            run = db.query(Run).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        log.error(f"Database error: {e}")
        raise
    finally:
        db.close()

def get_db_session() -> Session:
    """
    Get database session (for FastAPI dependency injection)
    
    Usage in FastAPI:
        @app.get("/api/runs")
        def get_runs(db: Session = Depends(get_db_session)):
            return db.query(Run).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Test connection function
def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            log.info("✅ Database connection successful (psycopg3)")
            return True
    except Exception as e:
        log.error(f"❌ Database connection failed: {e}")
        return False
