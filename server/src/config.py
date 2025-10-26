# server/src/config.py
"""
Configuration management with environment variables
Optimized for Apple M1 Pro (32GB RAM)
"""
import os
from typing import List, Dict
from pathlib import Path
import logging
log = logging.getLogger(__name__)

class Config:
    """Application configuration"""
    DEFAULT_EXECUTION_MODE = "headless"  # Always default to headless
    ALLOW_HEADED_MODE = True  # Set to False to force headless
    
    def validate_execution_mode(self, mode: str) -> str:
        """Validate and return execution mode"""
        if mode == "headed" and not self.ALLOW_HEADED_MODE:
            log.warning("Headed mode disabled, forcing headless")
            return "headless"
        return mode if mode in ["headed", "headless"] else "headless"
    # ============================================================
    # DATABASE
    # ============================================================
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://suyash.mishra:pass%40123@localhost:5432/uidai_mvp_extended"
    )
    
    # ============================================================
    # OLLAMA
    # ============================================================
    OLLAMA_HTTP: str = os.getenv("OLLAMA_HTTP", "http://localhost:11434")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    
    # Model registry for M1 Pro
    MODEL_REGISTRY: Dict[str, List[str]] = {
        "story_generation": [
            os.getenv("MODEL_STORY_GENERATION", "qwen2.5:14b"),
            "qwen2.5:7b",
            "deepseek-r1:14b"
        ],
        "recording_analysis": [
            "qwen2.5:14b",
            "qwen2.5:7b"
        ],
        "scenario_conversion": [
            "qwen2.5:14b",
            "qwen2.5:7b"
        ],
        "scenario_validation": [
            "qwen2.5:7b",
            "llama3.2:3b"
        ],
        "code_generation": [
            os.getenv("MODEL_CODE_GENERATION", "qwen2.5-coder:14b"),
            "qwen2.5:7b"
        ],
        "code_validation": [
            os.getenv("MODEL_VALIDATION", "llama3.2:3b"),
            "qwen2.5:7b"
        ],
        "healing": [
            os.getenv("MODEL_HEALING", "qwen2.5-coder:14b"),
            "qwen2.5:14b"
        ]
    }
    
    # ============================================================
    # APPLICATION
    # ============================================================
    UIDAI_RUNS_DIR: Path = Path(os.getenv("UIDAI_RUNS_DIR", "/tmp/uidai_runs"))
    MAX_CONCURRENT_RUNS: int = int(os.getenv("MAX_CONCURRENT_RUNS", "2"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    JSON_LOGS: bool = os.getenv("JSON_LOGS", "false").lower() == "true"
    
    # ============================================================
    # MINIO
    # ============================================================
    MINIO_ENABLED: bool = os.getenv("MINIO_ENABLED", "false").lower() == "true"
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9001")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "uidai-artifacts-extended")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    # ============================================================
    # FRONTEND (CORS)
    # ============================================================
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000"
    ).split(",")
    
    # ============================================================
    # FEATURES
    # ============================================================
    ENABLE_RECORDER: bool = os.getenv("ENABLE_RECORDER", "true").lower() == "true"
    ENABLE_HEALING: bool = os.getenv("ENABLE_HEALING", "true").lower() == "true"
    MAX_HEAL_ATTEMPTS: int = int(os.getenv("MAX_HEAL_ATTEMPTS", "3"))
    
    # Cleanup
    RUN_RETENTION_DAYS: int = int(os.getenv("RUN_RETENTION_DAYS", "7"))
    ENABLE_AUTO_CLEANUP: bool = os.getenv("ENABLE_AUTO_CLEANUP", "true").lower() == "true"
    
    # ============================================================
    # RATE LIMITING
    # ============================================================
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_RUNS: str = os.getenv("RATE_LIMIT_RUNS", "10/hour")
    RATE_LIMIT_API: str = os.getenv("RATE_LIMIT_API", "100/minute")
    
    # ============================================================
    # MONITORING
    # ============================================================
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    
    # ============================================================
    # METHODS
    # ============================================================
    @classmethod
    def get_model_for_task(cls, task: str, attempt: int = 0) -> str:
        """Get model for task with fallback support"""
        models = cls.MODEL_REGISTRY.get(task, [])
        if attempt < len(models):
            return models[attempt]
        raise ValueError(f"No fallback model available for task '{task}' at attempt {attempt}")
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        # Check database
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        # Check Ollama
        if not cls.OLLAMA_HTTP:
            errors.append("OLLAMA_HTTP is required")
        
        # Check concurrent runs
        if cls.MAX_CONCURRENT_RUNS < 1:
            errors.append("MAX_CONCURRENT_RUNS must be >= 1")
        if cls.MAX_CONCURRENT_RUNS > 3:
            errors.append("MAX_CONCURRENT_RUNS > 3 not recommended for M1 Pro (32GB)")
        
        # Check runs directory
        if not cls.UIDAI_RUNS_DIR.parent.exists():
            errors.append(f"Parent directory of UIDAI_RUNS_DIR does not exist: {cls.UIDAI_RUNS_DIR.parent}")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("=" * 60)
        print("UIDAI Test Automation - Configuration")
        print("=" * 60)
        print(f"Database: {cls.DATABASE_URL}")
        print(f"Ollama: {cls.OLLAMA_HTTP}")
        print(f"Max Concurrent Runs: {cls.MAX_CONCURRENT_RUNS}")
        print(f"Runs Directory: {cls.UIDAI_RUNS_DIR}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"MinIO Enabled: {cls.MINIO_ENABLED}")
        print(f"Recorder Enabled: {cls.ENABLE_RECORDER}")
        print(f"Healing Enabled: {cls.ENABLE_HEALING}")
        print(f"Rate Limiting: {cls.RATE_LIMIT_ENABLED}")
        print(f"Metrics: {cls.ENABLE_METRICS}")
        print("=" * 60)

# Singleton instance
config = Config()

# Validate on import
try:
    config.validate()
except ValueError as e:
    print(f"⚠️  Configuration Warning: {e}")