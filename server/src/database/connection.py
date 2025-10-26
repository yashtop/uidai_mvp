# server/src/database/connection.py - COMPLETE FILE

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from ..config import config

log = logging.getLogger(__name__)

# Database URL from config
DATABASE_URL = config.DATABASE_URL

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database (create tables if needed)"""
    from .models import Base
    
    try:
        Base.metadata.create_all(bind=engine)
        log.info("Database tables created/verified")
    except Exception as e:
        log.error(f"Failed to initialize database: {e}")
        raise

@contextmanager
def get_db():
    """
    Context manager for database sessions
    Use with: with get_db() as db:
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """
    Dependency for FastAPI
    Use with: db: Session = Depends(get_db_session)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()