# server/src/database/models.py - COMPLETE FILE

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Run(Base):
    __tablename__ = "runs"
    
    # ============================================================
    # EXISTING COLUMNS
    # ============================================================
    id = Column(String, primary_key=True)
    run_name = Column(String, nullable=False)
    target_url = Column(String, nullable=False)
    mode = Column(String, default="headless")
    preset = Column(String, default="balanced")
    scenario = Column(Text, nullable=True)
    max_heal_attempts = Column(Integer, default=3)
    
    status = Column(String, default="pending")
    phase = Column(String, default="pending")
    
    discovery_result = Column(JSON, nullable=True)
    generation_result = Column(JSON, nullable=True)
    execution_result = Column(JSON, nullable=True)
    healing_result = Column(JSON, nullable=True)
    
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # ============================================================
    # NEW COLUMNS for Multi-Agent System
    # ============================================================
    test_creation_mode = Column(String, default="ai")
    
    user_story = Column(Text, nullable=True)
    final_story = Column(Text, nullable=True)
    story_source = Column(String, nullable=True)
    story_model = Column(String, nullable=True)
    
    recorded_test_path = Column(String, nullable=True)
    recording_analysis = Column(JSON, nullable=True)
    
    scenarios_count = Column(Integer, default=0)
    scenario_model = Column(String, nullable=True)
    
    tests_count = Column(Integer, default=0)
    code_model = Column(String, nullable=True)
    
    pages_discovered = Column(Integer, default=0)
    elements_discovered = Column(Integer, default=0)
    
    tests_passed = Column(Integer, default=0)
    tests_failed = Column(Integer, default=0)
    tests_total = Column(Integer, default=0)
    
    healing_attempts = Column(Integer, default=0)
    is_healed = Column(Boolean, default=False)
    
    discovery_duration_seconds = Column(Integer, nullable=True)
    story_duration_seconds = Column(Integer, nullable=True)
    scenario_duration_seconds = Column(Integer, nullable=True)
    code_duration_seconds = Column(Integer, nullable=True)
    execution_duration_seconds = Column(Integer, nullable=True)
    healing_duration_seconds = Column(Integer, nullable=True)
    total_duration_seconds = Column(Integer, nullable=True)
    
    agent_metadata = Column(JSON, nullable=True)
    
    # ============================================================
    # RELATIONSHIPS (optional - comment out if causing issues)
    # ============================================================
    # Uncomment these ONLY if you have the corresponding tables
    # logs = relationship("RunLog", back_populates="run", cascade="all, delete-orphan")
    # artifacts = relationship("Artifact", back_populates="run", cascade="all, delete-orphan")
    # test_results = relationship("TestResult", back_populates="run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Run(id={self.id}, mode={self.test_creation_mode}, status={self.status})>"


class RunLog(Base):
    """Log entries for runs"""
    __tablename__ = "run_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship (optional)
    # run = relationship("Run", back_populates="logs")
    
    def __repr__(self):
        return f"<RunLog(run_id={self.run_id}, message={self.message[:50]})>"


class Artifact(Base):
    """Artifacts (screenshots, videos) for runs"""
    __tablename__ = "artifacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    filename = Column(String, nullable=False)
    artifact_type = Column(String, nullable=False)  # screenshot, video, trace
    file_path = Column(String, nullable=False)
    minio_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship (optional)
    # run = relationship("Run", back_populates="artifacts")
    
    def __repr__(self):
        return f"<Artifact(run_id={self.run_id}, type={self.artifact_type})>"


class TestResult(Base):
    """Individual test results"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    test_name = Column(String, nullable=False)
    outcome = Column(String, nullable=False)  # passed, failed, skipped
    duration_seconds = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship (optional)
    # run = relationship("Run", back_populates="test_results")
    
    def __repr__(self):
        return f"<TestResult(test={self.test_name}, outcome={self.outcome})>"