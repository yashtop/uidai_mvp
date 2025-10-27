# server/src/database/models.py - COMPLETE VERSION

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


# ============================================
# MAIN TEST RUN MODEL
# ============================================

class TestRun(Base):
    """Main test run record"""
    __tablename__ = "test_runs"
    
    # Primary identifiers
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), unique=True, nullable=False, index=True, default=generate_uuid)
    run_name = Column(String(255))
    
    # Configuration
    target_url = Column(String(500), nullable=False)
    test_creation_mode = Column(String(50), default="ai")  # ai/record/hybrid
    mode = Column(String(50), default="headless")  # headless/headed
    preset = Column(String(50), default="balanced")  # quick/balanced/deep
    
    # Status tracking
    status = Column(String(50), default="queued", index=True)  # queued/running/completed/failed/cancelled
    details = Column(String, default="Initializing...")
    progress = Column(Integer, default=0)
    phase = Column(String(100), default="starting")  # starting/discovery/generation/execution/healing/completed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Discovery results
    discovery_data = Column(JSON)  # Full discovery results
    pages_discovered = Column(Integer, default=0)
    elements_found = Column(Integer, default=0)
    
    # Story and scenarios
    user_story = Column(Text)  # User-provided story
    final_story = Column(Text)  # Generated/enhanced story
    story_model = Column(String(100))  # Model used for story generation
    scenarios = Column(JSON)  # Generated test scenarios
    scenarios_count = Column(Integer, default=0)
    
    # Generated tests
    generated_tests = Column(JSON)  # List of generated test files
    tests_count = Column(Integer, default=0)
    
    # Execution results
    tests_total = Column(Integer, default=0)
    tests_passed = Column(Integer, default=0)
    tests_failed = Column(Integer, default=0)
    tests_skipped = Column(Integer, default=0)
    duration_seconds = Column(Float)
    
    # Healing
    auto_heal = Column(Boolean, default=True)
    max_heal_attempts = Column(Integer, default=3)
    healing_attempts = Column(Integer, default=0)
    is_healed = Column(Boolean, default=False)
    healing_result = Column(JSON)  # Detailed healing attempts and results
    
    # Artifacts
    artifacts = Column(JSON)  # List of artifact files (screenshots, videos, etc.)
    report_path = Column(String(500))
    
    # Error tracking
    error_message = Column(Text)
    error_traceback = Column(Text)
    
    # Relationships
    test_results = relationship("TestResult", back_populates="run", cascade="all, delete-orphan")
    logs = relationship("RunLog", back_populates="run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TestRun(run_id={self.run_id}, status={self.status}, phase={self.phase})>"


# ============================================
# TEST RESULT MODEL
# ============================================

class TestResult(Base):
    """Individual test result"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), ForeignKey("test_runs.run_id"), nullable=False, index=True)
    
    # Test identification
    nodeid = Column(String(500), nullable=False)  # Full pytest node ID
    test_name = Column(String(255))  # Extracted test name
    test_file = Column(String(255))  # Test file path
    
    # Result
    outcome = Column(String(50))  # passed/failed/skipped/error
    duration = Column(Float)
    
    # Error details
    error_message = Column(Text)
    error_traceback = Column(Text)
    
    # Metadata
    line_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Healing tracking
    was_healed = Column(Boolean, default=False)
    healing_attempt = Column(Integer)  # Which healing attempt fixed this
    
    # Relationship
    run = relationship("TestRun", back_populates="test_results")
    
    def __repr__(self):
        return f"<TestResult(nodeid={self.nodeid}, outcome={self.outcome})>"


# ============================================
# RUN LOG MODEL
# ============================================

class RunLog(Base):
    """Log entries for a run"""
    __tablename__ = "run_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), ForeignKey("test_runs.run_id"), nullable=False, index=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(20))  # INFO/WARNING/ERROR/DEBUG
    message = Column(Text)
    
    # Relationship
    run = relationship("TestRun", back_populates="logs")
    
    def __repr__(self):
        return f"<RunLog(run_id={self.run_id}, level={self.level})>"


# ============================================
# LEGACY MODELS (Keep for backward compatibility)
# ============================================

class Run(Base):
    """Legacy run model - kept for backward compatibility"""
    __tablename__ = "runs_legacy"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), unique=True, nullable=False)
    target_url = Column(String(500))
    status = Column(String(50), default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Run(run_id={self.run_id}, status={self.status})>"


class Artifact(Base):
    """Artifact files"""
    __tablename__ = "artifacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), nullable=False, index=True)
    filename = Column(String(255))
    file_path = Column(String(500))
    file_type = Column(String(50))  # screenshot/video/report/log
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Artifact(filename={self.filename}, type={self.file_type})>"