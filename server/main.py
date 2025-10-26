# server/main.py - COMPLETE UPDATES

import os
import sys
import logging
import uuid
import asyncio
import json
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Database
from src.database.connection import init_db, get_db, get_db_session
from src.database.models import Run, RunLog, Artifact

# LangGraph Pipeline
from src.pipeline_langgraph import langgraph_pipeline
from src.queue_manager import queue_manager
from src.config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
log = logging.getLogger(__name__)

# ============================================================
# Pydantic Models
# ============================================================

class RunRequest(BaseModel):
    url: str
    mode: str = "headless"
    preset: str = "balanced"
    useOllama: bool = True
    runName: Optional[str] = None
    
    # Test creation mode
    testCreationMode: str = "ai"  # "ai" | "record" | "hybrid"
    
    # Story field
    story: Optional[str] = None
    
    # Deprecated (backward compatibility)
    scenario: Optional[str] = None
    useRecorder: bool = False
    
    maxHealAttempts: int = 3
    autoHeal: bool = True

# ============================================================
# Lifespan Event
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    try:
        init_db()
        log.info("✅ Database initialized")
        
        config.validate()
        log.info("✅ Configuration validated")
        
    except Exception as e:
        log.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    log.info("🛑 Shutting down...")

# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="UIDAI Test Automation API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Pipeline Function
# ============================================================

def run_pipeline_sync(run_id: str, config_dict: dict):
    """
    Synchronous wrapper for LangGraph async pipeline
    Runs in background thread via queue manager
    """
    try:
        log.info(f"[{run_id}] Starting LangGraph pipeline...")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run async pipeline in this loop
            final_state = loop.run_until_complete(
                langgraph_pipeline.run(run_id, config_dict)
            )
        finally:
            loop.close()
        
        log.info(f"[{run_id}] Pipeline completed: {final_state.get('status')}")
        
    except Exception as e:
        log.error(f"[{run_id}] Pipeline failed: {e}", exc_info=True)
        
        # Mark as failed in database
        with get_db() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = 'failed'
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                db.commit()
        
        raise

# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "healthy",
            "queue": {
                "active_runs": len(queue_manager.active_runs),
                "queued_runs": queue_manager.queued_runs.qsize()
            }
        }
    }

@app.post("/api/run")
async def create_run(request: RunRequest, db: Session = Depends(get_db_session)):
    """Create and queue a new test run"""
    run_id = str(uuid.uuid4())
    run_name = request.runName or f"Run {run_id[:8]}"
    
    # Create run in database
    run = Run(
        id=run_id,
        run_name=run_name,
        target_url=request.url,
        mode=request.mode,
        preset=request.preset,
        test_creation_mode=request.testCreationMode,
        user_story=request.story,
        max_heal_attempts=request.maxHealAttempts,
        status="queued"
    )
    
    try:
        db.add(run)
        db.commit()
        log.info(f"Created run: {run_id}")
    except Exception as e:
        log.error(f"DB error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create run")
    
    # Prepare config
    run_config = {
        "url": request.url,
        "mode": request.mode,
        "preset": request.preset,
        "testCreationMode": request.testCreationMode,
        "story": request.story,
        "maxHealAttempts": request.maxHealAttempts,
        "autoHeal": request.autoHeal
    }
    
    # Add to queue
    queue_info = await queue_manager.enqueue_run(run_id, run_config)
    
    return {
        "ok": True,
        "runId": run_id,
        "runName": run_name,
        "status": "queued",
        **queue_info
    }

@app.get("/api/run/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db_session)):
    """Get run details"""
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "id": run.id,
        "runName": run.run_name,
        "targetUrl": run.target_url,
        "status": run.status,
        "phase": run.phase,
        
        "testCreationMode": run.test_creation_mode,
        "executionMode": run.mode,
        "preset": run.preset,
        
        "userStory": run.user_story,
        "finalStory": run.final_story,
        "storySource": run.story_source,
        "storyModel": run.story_model,
        
        "recordedTestPath": run.recorded_test_path,
        "recordingAnalysis": run.recording_analysis,
        
        "scenariosCount": run.scenarios_count,
        "scenarioModel": run.scenario_model,
        "testsCount": run.tests_count,
        "codeModel": run.code_model,
        
        "pagesDiscovered": run.pages_discovered,
        "elementsDiscovered": run.elements_discovered,
        
        "testsPassed": run.tests_passed,
        "testsFailed": run.tests_failed,
        "testsTotal": run.tests_total,
        
        "healingAttempts": run.healing_attempts,
        "isHealed": run.is_healed,
        
        "performance": {
            "discoverySeconds": run.discovery_duration_seconds,
            "storySeconds": run.story_duration_seconds,
            "scenariosSeconds": run.scenario_duration_seconds,
            "codeSeconds": run.code_duration_seconds,
            "executionSeconds": run.execution_duration_seconds,
            "healingSeconds": run.healing_duration_seconds,
            "totalSeconds": run.total_duration_seconds
        },
        
        "agentMetadata": run.agent_metadata,
        
        "discoveryResult": run.discovery_result,
        "generationResult": run.generation_result,
        "executionResult": run.execution_result,
        "healingResult": run.healing_result,
        "errorMessage": run.error_message,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
        "completedAt": run.completed_at.isoformat() if run.completed_at else None
    }

@app.get("/api/queue/status")
def get_queue_status():
    """Get current queue status"""
    return queue_manager.get_status()

@app.post("/api/run/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel a queued or running run"""
    cancelled = await queue_manager.cancel_run(run_id)
    
    if cancelled:
        return {"ok": True, "message": "Run cancelled"}
    else:
        raise HTTPException(status_code=404, detail="Run not found or already completed")

# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)