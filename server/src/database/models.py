# server/src/database/models.py
"""
SQLAlchemy Database Models
"""
from sqlalchemy import Column, String, Integer, JSON, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Run(Base):
    """Test Run Model"""
    __tablename__ = "runs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    run_name = Column(String, nullable=False)
    target_url = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed
    phase = Column(String, default="pending")   # discovery, scenario, generation, execution, healing
    
    # Configuration
    mode = Column(String, default="headless")
    preset = Column(String, default="balanced")
    scenario = Column(String, nullable=True)
    max_heal_attempts = Column(Integer, default=1)
    
    # Results (JSON)
    discovery_result = Column(JSON, nullable=True)
    generation_result = Column(JSON, nullable=True)
    execution_result = Column(JSON, nullable=True)
    healing_result = Column(JSON, nullable=True)
    
    # Metadata
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    logs = relationship("RunLog", back_populates="run", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="run", cascade="all, delete-orphan")

class RunLog(Base):
    """Log entries for each run"""
    __tablename__ = "run_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    run = relationship("Run", back_populates="logs")

class Artifact(Base):
    """Test artifacts (screenshots, videos, HTML snapshots)"""
    __tablename__ = "artifacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    
    artifact_type = Column(String, nullable=False)  # screenshot, html, video, trace
    file_path = Column(String, nullable=False)      # Path in MinIO
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)      # Size in bytes
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    run = relationship("Run", back_populates="artifacts")

class TestResult(Base):
    """Individual test results"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    
    test_name = Column(String, nullable=False)
    test_file = Column(String, nullable=False)
    outcome = Column(String, nullable=False)  # passed, failed, skipped
    
    duration = Column(Integer, nullable=True)  # Duration in milliseconds
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Test metadata
    test_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)