# server/main.py
"""
UIDAI Testing Automation API - Fixed Async/Sync Issue
Uses threading instead of asyncio for background tasks
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends,WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse,FileResponse, JSONResponse
from pathlib import Path
import mimetypes
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging
import uuid
from pathlib import Path
from datetime import datetime
import threading
import json


# Enhanced imports
from src.tools.discovery_enhanced import discover_with_selectors
from src.tools.generator import generate_tests, SCENARIO_TEMPLATES
from src.tools.runner import run_playwright_tests
from src.tools.auto_healer import auto_heal_and_rerun
from src.database.connection import get_db, get_db_session, init_db
from src.database.models import Run, RunLog
from src.tools.progress_tracker import progress_tracker

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="UIDAI Testing Automation API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        init_db()
        log.info("✅ Database initialized")
    except Exception as e:
        log.error(f"❌ Database initialization failed: {e}")

class RunRequest(BaseModel):
    url: str
    mode: str = "headless"
    preset: str = "balanced"
    useOllama: bool = True
    runName: Optional[str] = None
    scenario: Optional[str] = None
    maxHealAttempts: int = 3
    autoHeal: bool = True
    useRecorder: bool = False

def get_run_dir(run_id: str) -> Path:
    return Path("/tmp/uidai_runs") / run_id

def add_log_to_db(db: Session, run_id: str, message: str):
    try:
        log_entry = RunLog(run_id=run_id, message=message)
        db.add(log_entry)
        db.commit()
        log.info(f"[{run_id}] {message}")
    except Exception as e:
        log.info(f"[{run_id}] {message}")

def get_preset_config(preset: str) -> Dict[str, Any]:
    configs = {
        "quick": {"level": 1, "max_pages": 5, "timeout": 180},
        "balanced": {"level": 1, "max_pages": 15, "timeout": 300},
        "deep": {"level": 2, "max_pages": 30, "timeout": 600}
    }
    return configs.get(preset, configs["balanced"])

def run_pipeline_sync(run_id: str, config: dict):
    """Sync pipeline function - runs in background thread"""
    with get_db() as db:
        try:
            url = config["url"]
            add_log_to_db(db, run_id, f"🚀 Starting pipeline for {url}")
            
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "running"
                run.phase = "discovery"
                db.commit()
            
            preset_config = get_preset_config(config["preset"])
            
            # Discovery
            add_log_to_db(db, run_id, " Phase 1: Discovery...")
            discovery_result = discover_with_selectors(
                run_id=run_id,
                url=url,
                level=preset_config["level"],
                max_pages=preset_config["max_pages"]
            )
            
            pages = discovery_result.get("pages", [])
            selectors_count = sum(len(p.get("selectors", [])) for p in pages)
            add_log_to_db(db, run_id, f"✓ Found {len(pages)} pages, {selectors_count} selectors")
            
            if run:
                run.discovery_result = discovery_result
                run.phase = "generation"
                db.commit()
            
            # Generation
            add_log_to_db(db, run_id, "⚙️ Phase 2: Generating tests...")
            scenario_param = config.get("scenario", "") or "auto"
            models = ["qwen2.5-coder:14b"] if config["useOllama"] else []
            
            gen_result = generate_tests(
                run_id=run_id,
                url=url,
                pages=pages,
                scenario=scenario_param,
                models=models
            )
            
            if not gen_result.get("ok"):
                raise Exception("Test generation failed")
            
            test_count = gen_result.get("count", 0)
            add_log_to_db(db, run_id, f"✓ Generated {test_count} test(s)")
            
            if run:
                run.generation_result = gen_result
                run.phase = "execution"
                db.commit()
            
            # Execution
            add_log_to_db(db, run_id, "🧪 Phase 3: Executing tests...")
            tests_dir = get_run_dir(run_id) / "generator" / "tests"
            
            run_result = run_playwright_tests(
                run_id=run_id,
                gen_dir=str(tests_dir),
                headed=config["mode"] == "headed",
                timeout_seconds=preset_config["timeout"]
            )
            
            summary = run_result.get("summary", {})
            passed = int(summary.get("passed", 0))
            failed = int(summary.get("failed", 0))
            total = int(summary.get("total", 0))
            
            if run:
                run.execution_result = run_result
                db.commit()
            
            if failed == 0 and passed > 0:
                add_log_to_db(db, run_id, f"✅ All tests passed! ({passed}/{total})")
                if run:
                    run.status = "completed"
                    run.phase = "completed"
                    run.completed_at = datetime.utcnow()
                    db.commit()
            elif failed > 0 and config.get("autoHeal", True):
                # Healing
                add_log_to_db(db, run_id, f"🔧 Phase 4: Auto-healing ({failed} failures)...")
                if run:
                    run.phase = "healing"
                    db.commit()
                
                all_tests = run_result.get("tests", [])
                failed_tests = [t for t in all_tests if t.get("outcome") == "failed"]
                
                healing_result = auto_heal_and_rerun(
                    run_id=run_id,
                    gen_dir=str(tests_dir),
                    failed_tests=failed_tests,
                    summary=summary,
                    generated_files=[t.get("path", "") for t in gen_result.get("tests", [])],
                    models=models,
                    max_attempts=config["maxHealAttempts"],
                    headed=config["mode"] == "headed",
                    timeout_seconds=preset_config["timeout"]
                )
                
                if run:
                    run.healing_result = healing_result
                    db.commit()
                
                if healing_result.get("healed"):
                    attempts = healing_result.get("healing_attempts", 0)
                    add_log_to_db(db, run_id, f"✅ Healed after {attempts} attempt(s)!")
                    if run:
                        run.status = "completed"
                        run.execution_result = healing_result.get("final_result")
                        db.commit()
                else:
                    add_log_to_db(db, run_id, "⚠️ Healing incomplete")
                    if run:
                        run.status = "failed"
                        db.commit()
            else:
                if run:
                    run.status = "failed"
                    db.commit()
            
            if run:
                run.phase = "completed"
                run.completed_at = datetime.utcnow()
                db.commit()
            
            add_log_to_db(db, run_id, "🏁 Pipeline completed")
            
        except Exception as e:
            log.exception(f"Pipeline failed for {run_id}: {e}")
            add_log_to_db(db, run_id, f"💥 Failed: {str(e)}")
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "failed"
                run.phase = "failed"
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                db.commit()

@app.get("/")
def root():
    return {"name": "UIDAI Testing API", "version": "2.0.0", "status": "running"}


@app.get("/api/runs")
def list_runs(limit: int = 50, db: Session = Depends(get_db_session)):
    """List all runs"""
    runs = db.query(Run).order_by(Run.created_at.desc()).limit(limit).all()
    return {
        "runs": [
            {
                "runId": r.id,
                "targetUrl": r.target_url,
                "status": r.status,
                "phase": r.phase,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
                "completedAt": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]
    }

@app.get("/api/run/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db_session)):
    """Get full run data"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Access the stored JSON fields directly from the model
    return {
        "runId": run.id,
        "targetUrl": run.target_url,
        "status": run.status,
        "phase": run.phase,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
        "completedAt": run.completed_at.isoformat() if run.completed_at else None,
        "discovery": run.discovery_result,
        "tests": run.generation_result,
        "results": run.execution_result,
        "healing": run.healing_result,
        "config": {
            "mode": run.mode,
            "preset": run.preset,
            "scenario": run.scenario,
            "maxHealAttempts": run.max_heal_attempts,
        },
    }

@app.get("/api/run/{run_id}/discovery")
def get_discovery(run_id: str, db: Session = Depends(get_db_session)):
    """Get discovery results for a run"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if not run.discovery_result:
        return {"ok": False, "message": "Discovery not yet completed"}
    
    return {**run.discovery_result, "ok": True}

@app.get("/api/run/{run_id}/tests")
def get_tests(run_id: str, db: Session = Depends(get_db_session)):
    """Get generated tests for a run"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if not run.generation_result:
        return {"ok": False, "message": "Tests not yet generated"}
    
    return {**run.generation_result, "ok": True}

@app.get("/api/run/{run_id}/results")
def get_results(run_id: str, db: Session = Depends(get_db_session)):
    """Get test results for a run"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if not run.execution_result:
        return {"ok": False, "message": "Results not yet available"}
    
    return {**run.execution_result, "ok": True}

@app.get("/api/run/{run_id}/healing")
def get_healing(run_id: str, db: Session = Depends(get_db_session)):
    """Get healing data for a run"""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if not run.healing_result:
        return {"ok": False, "message": "No healing data available"}
    
    return {**run.healing_result, "ok": True}

@app.get("/api/run/{run_id}/logs")
def get_logs(run_id: str, db: Session = Depends(get_db_session)):
    """Get logs for a run"""
    logs = db.query(RunLog).filter(RunLog.run_id == run_id).order_by(RunLog.timestamp).all()
    return {"logs": [{"message": l.message, "timestamp": l.timestamp.isoformat()} for l in logs]}

@app.get("/api/run/{run_id}/logs/stream")
async def stream_logs(run_id: str):
    """
    Server-Sent Events endpoint for streaming logs in real-time
    """
    async def event_generator():
        """Generate SSE events from database logs"""
        last_id = 0
        
        try:
            while True:
                # Get new logs since last check
                with get_db() as db:
                    new_logs = db.query(RunLog)\
                        .filter(RunLog.run_id == run_id)\
                        .filter(RunLog.id > last_id)\
                        .order_by(RunLog.timestamp)\
                        .all()
                    
                    for log in new_logs:
                        last_id = log.id
                        # Format as SSE
                        data = {
                            "line": log.message,
                            "timestamp": log.timestamp.isoformat()
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    
                    # Check if run is completed
                    run = db.query(Run).filter(Run.id == run_id).first()
                    if run and run.status in ["completed", "failed"]:
                        # Send final message and close
                        yield f"data: {json.dumps({'line': f'[Stream ended - Run {run.status}]'})}\n\n"
                        break
                
                # Wait before checking for new logs
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            # Client disconnected
            log.info(f"Client disconnected from log stream for {run_id}")
        except Exception as e:
            log.error(f"Error streaming logs for {run_id}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
# Add this to your main.py imports

@app.get("/api/run/{run_id}/logs/stream")
async def stream_logs(run_id: str):
    """
    Server-Sent Events endpoint for streaming logs in real-time
    """
    async def event_generator():
        """Generate SSE events from database logs"""
        last_id = 0
        
        try:
            while True:
                # Get new logs since last check
                with get_db() as db:
                    new_logs = db.query(RunLog)\
                        .filter(RunLog.run_id == run_id)\
                        .filter(RunLog.id > last_id)\
                        .order_by(RunLog.timestamp)\
                        .all()
                    
                    for log in new_logs:
                        last_id = log.id
                        # Format as SSE
                        data = {
                            "line": log.message,
                            "timestamp": log.timestamp.isoformat()
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    
                    # Check if run is completed
                    run = db.query(Run).filter(Run.id == run_id).first()
                    if run and run.status in ["completed", "failed"]:
                        # Send final message and close
                        yield f"data: {json.dumps({'line': f'[Stream ended - Run {run.status}]'})}\n\n"
                        break
                
                # Wait before checking for new logs
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            # Client disconnected
            log.info(f"Client disconnected from log stream for {run_id}")
        except Exception as e:
            log.error(f"Error streaming logs for {run_id}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/run")
def create_run(request: RunRequest, db: Session = Depends(get_db_session)):
    run_id = str(uuid.uuid4())
    run_name = request.runName or f"Run {run_id[:8]}"
    
    run = Run(
        id=run_id,
        run_name=run_name,
        target_url=request.url,
        mode=request.mode,
        preset=request.preset,
        scenario=request.scenario or "",
        max_heal_attempts=request.maxHealAttempts
    )
    
    try:
        db.add(run)
        db.commit()
        log.info(f"Created run: {run_id}")
    except Exception as e:
        log.error(f"DB error: {e}")
    
    config = {
        "url": request.url,
        "mode": request.mode,
        "preset": request.preset,
        "useOllama": request.useOllama,
        "scenario": request.scenario or "",
        "maxHealAttempts": request.maxHealAttempts,
        "autoHeal": request.autoHeal
    }
    
    # Run in thread to avoid async/sync conflicts
    thread = threading.Thread(target=run_pipeline_sync, args=(run_id, config), daemon=True)
    thread.start()
    
    return {"ok": True, "runId": run_id, "runName": run_name}


@app.get("/api/run/{run_id}/artifacts")
def list_artifacts(run_id: str):
    """
    List all artifacts (screenshots, videos, traces) for a run
    """
    artifacts_dir = Path("/tmp/uidai_runs") / run_id / "artifacts"
    
    if not artifacts_dir.exists():
        return {"ok": False, "message": "No artifacts found", "artifacts": []}
    
    artifacts = []
    
    # Scan for all artifact files
    for file_path in artifacts_dir.rglob("*"):
        if file_path.is_file():
            rel_path = file_path.relative_to(artifacts_dir)
            file_type = "unknown"
            
            # Determine file type
            suffix = file_path.suffix.lower()
            if suffix in ['.png', '.jpg', '.jpeg']:
                file_type = "screenshot"
            elif suffix in ['.webm', '.mp4']:
                file_type = "video"
            elif suffix == '.zip':
                file_type = "trace"
            elif suffix == '.log':
                file_type = "log"
            
            artifacts.append({
                "name": file_path.name,
                "path": str(rel_path),
                "type": file_type,
                "size": file_path.stat().st_size,
                "url": f"/api/run/{run_id}/artifacts/{rel_path}"
            })
    
    return {
        "ok": True,
        "runId": run_id,
        "count": len(artifacts),
        "artifacts": artifacts
    }

@app.get("/api/run/{run_id}/artifacts/{artifact_path:path}")
def get_artifact(run_id: str, artifact_path: str):
    """
    Serve a specific artifact file (screenshot, video, etc.)
    """
    file_path = Path("/tmp/uidai_runs") / run_id / "artifacts" / artifact_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Security check - ensure file is within artifacts directory
    try:
        file_path.resolve().relative_to(Path("/tmp/uidai_runs") / run_id / "artifacts")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Determine media type
    media_type, _ = mimetypes.guess_type(str(file_path))
    
    return FileResponse(
        path=file_path,
        media_type=media_type or "application/octet-stream",
        filename=file_path.name
    )

@app.get("/api/run/{run_id}/screenshots")
def list_screenshots(run_id: str):
    """
    List only screenshot artifacts for a run
    """
    artifacts_response = list_artifacts(run_id)
    
    if not artifacts_response.get("ok"):
        return artifacts_response
    
    screenshots = [
        art for art in artifacts_response["artifacts"]
        if art["type"] == "screenshot"
    ]
    
    return {
        "ok": True,
        "runId": run_id,
        "count": len(screenshots),
        "screenshots": screenshots
    }

@app.get("/api/run/{run_id}/failures")
def get_failures_with_screenshots(run_id: str, db: Session = Depends(get_db_session)):
    """
    Get failed tests with their associated screenshots
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if not run.execution_result:
        return {"ok": False, "message": "No test results available"}
    
    # Get all test results
    tests = run.execution_result.get("tests", [])
    failed_tests = [t for t in tests if t.get("outcome") == "failed"]
    
    # Get screenshots
    screenshots_response = list_screenshots(run_id)
    screenshots = screenshots_response.get("screenshots", [])
    
    # Match screenshots to failed tests (by test name or timestamp)
    failures_with_screenshots = []
    
    for test in failed_tests:
        test_name = test.get("nodeid", "").split("::")[-1] if "::" in test.get("nodeid", "") else test.get("nodeid", "")
        
        # Find matching screenshots
        matching_screenshots = [
            s for s in screenshots
            if test_name.lower() in s["name"].lower()
        ]
        
        failures_with_screenshots.append({
            "test": test,
            "screenshots": matching_screenshots,
            "hasScreenshot": len(matching_screenshots) > 0
        })
    
    return {
        "ok": True,
        "runId": run_id,
        "failureCount": len(failed_tests),
        "failures": failures_with_screenshots
    }


# WebSocket endpoint for real-time progress
@app.websocket("/ws/run/{run_id}/progress")
async def websocket_progress(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()
    progress_tracker.register_connection(run_id, websocket)
    
    try:
        # Send current progress immediately
        current_progress = progress_tracker.get_progress(run_id)
        if current_progress:
            await websocket.send_text(json.dumps(current_progress))
        
        # Keep connection alive and wait for client messages
        while True:
            try:
                # Receive ping/pong to keep connection alive
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    except Exception as e:
        log.error(f"WebSocket error for run {run_id}: {e}")
    finally:
        progress_tracker.unregister_connection(run_id, websocket)

# HTTP endpoint to get current progress
@app.get("/api/run/{run_id}/progress")
def get_progress(run_id: str):
    """Get current progress for a run"""
    progress = progress_tracker.get_progress(run_id)
    if not progress:
        return {
            "ok": False,
            "message": "No progress data available",
            "phase": "unknown",
            "progress": 0
        }
    return {"ok": True, **progress}


# MODIFIED: Update run_pipeline_sync to broadcast progress
def run_pipeline_sync(run_id: str, config: dict):
    use_recorder = config.get("useRecorder", False)
    """Sync pipeline function with real-time progress updates"""
    with get_db() as db:
        try:
            url = config["url"]
            add_log_to_db(db, run_id, f" Starting pipeline for {url}")
            
            # Update: Starting
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "starting", "running", 
                    "Initializing test run...", 5
                )
            ))
            
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "running"
                run.phase = "discovery"
                db.commit()
            
            preset_config = get_preset_config(config["preset"])
            
            # Phase 1: Discovery
            add_log_to_db(db, run_id, " Phase 1: Discovery...")
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "discovery", "running",
                    f"Discovering pages on {url}...", 10
                )
            ))
            
            discovery_result = discover_with_selectors(
                run_id=run_id,
                url=url,
                level=preset_config["level"],
                max_pages=preset_config["max_pages"]
            )
            
            pages = discovery_result.get("pages", [])
            selectors_count = sum(len(p.get("selectors", [])) for p in pages)
            add_log_to_db(db, run_id, f"✓ Found {len(pages)} pages, {selectors_count} selectors")
            
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "discovery", "completed",
                    f"Found {len(pages)} pages, {selectors_count} elements", 30
                )
            ))
            
            if run:
                run.discovery_result = discovery_result
                run.phase = "generation"
                db.commit()
            
            # Phase 2: Generation
            add_log_to_db(db, run_id, " Phase 2: Generating tests...")
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "generation", "running",
                    "AI is generating test cases...", 40
                )
            ))
            
            scenario_param = config.get("scenario", "") or "auto"
            models = ["qwen2.5-coder:14b"] if config["useOllama"] else []
            
            gen_result = generate_tests(
                run_id=run_id,
                url=url,
                pages=pages,
                scenario=scenario_param,
                models=models
            )
            
            if not gen_result.get("ok"):
                raise Exception("Test generation failed")
            
            test_count = gen_result.get("count", 0)
            add_log_to_db(db, run_id, f"✓ Generated {test_count} test(s)")
            
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "generation", "completed",
                    f"Generated {test_count} tests", 60
                )
            ))
            
            if run:
                run.generation_result = gen_result
                run.phase = "execution"
                db.commit()
            
            # Phase 3: Execution
            add_log_to_db(db, run_id, " Phase 3: Executing tests...")
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "execution", "running",
                    f"Running {test_count} tests...", 70
                )
            ))
            
            tests_dir = get_run_dir(run_id) / "generator" / "tests"
            headed_mode = config.get("mode") == "headed" or use_recorder

            run_result = run_playwright_tests(
                run_id=run_id,
                gen_dir=str(tests_dir),
                #headed=config["mode"] == "headed",
                headed=True,  # ← Use this
                timeout_seconds=preset_config["timeout"]
            )
            
            summary = run_result.get("summary", {})
            passed = int(summary.get("passed", 0))
            failed = int(summary.get("failed", 0))
            total = int(summary.get("total", 0))
            
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "execution", "completed",
                    f"{passed}/{total} tests passed", 85
                )
            ))
            
            if run:
                run.execution_result = run_result
                db.commit()
            
            if failed == 0 and passed > 0:
                add_log_to_db(db, run_id, f" All tests passed! ({passed}/{total})")
                asyncio.run(progress_tracker.broadcast_progress(
                    run_id,
                    progress_tracker.update_phase(
                        run_id, "completed", "success",
                        f"All {passed} tests passed!", 100
                    )
                ))
                if run:
                    run.status = "completed"
                    run.phase = "completed"
                    run.completed_at = datetime.utcnow()
                    db.commit()
                    
            elif failed > 0 and config.get("autoHeal", True):
                # Phase 4: Healing
                add_log_to_db(db, run_id, f" Phase 4: Auto-healing ({failed} failures)...")
                asyncio.run(progress_tracker.broadcast_progress(
                    run_id,
                    progress_tracker.update_phase(
                        run_id, "healing", "running",
                        f"AI is fixing {failed} failed tests...", 90
                    )
                ))
                
                if run:
                    run.phase = "healing"
                    db.commit()
                
                all_tests = run_result.get("tests", [])
                failed_tests = [t for t in all_tests if t.get("outcome") == "failed"]
                
                healing_result = auto_heal_and_rerun(
                    run_id=run_id,
                    gen_dir=str(tests_dir),
                    failed_tests=failed_tests,
                    summary=summary,
                    generated_files=[t.get("path", "") for t in gen_result.get("tests", [])],
                    models=models,
                    max_attempts=config["maxHealAttempts"],
                    headed=config["mode"] == "headed",
                    timeout_seconds=preset_config["timeout"]
                )
                
                if run:
                    run.healing_result = healing_result
                    db.commit()
                
                if healing_result.get("healed"):
                    attempts = healing_result.get("healing_attempts", 0)
                    add_log_to_db(db, run_id, f" Healed after {attempts} attempt(s)!")
                    asyncio.run(progress_tracker.broadcast_progress(
                        run_id,
                        progress_tracker.update_phase(
                            run_id, "completed", "success",
                            f"Tests healed after {attempts} attempts!", 100
                        )
                    ))
                    if run:
                        run.status = "completed"
                        run.execution_result = healing_result.get("final_result")
                        db.commit()
                else:
                    add_log_to_db(db, run_id, " Healing incomplete")
                    asyncio.run(progress_tracker.broadcast_progress(
                        run_id,
                        progress_tracker.update_phase(
                            run_id, "completed", "partial",
                            "Some tests still failing", 100
                        )
                    ))
                    if run:
                        run.status = "failed"
                        db.commit()
            else:
                asyncio.run(progress_tracker.broadcast_progress(
                    run_id,
                    progress_tracker.update_phase(
                        run_id, "completed", "failed",
                        f"{failed} tests failed", 100
                    )
                ))
                if run:
                    run.status = "failed"
                    db.commit()
            
            if run:
                run.phase = "completed"
                run.completed_at = datetime.utcnow()
                db.commit()
            
            add_log_to_db(db, run_id, " Pipeline completed")
            
        except Exception as e:
            log.exception(f"Pipeline failed for {run_id}: {e}")
            add_log_to_db(db, run_id, f"💥 Failed: {str(e)}")
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "failed", "error",
                    f"Error: {str(e)}", 0
                )
            ))
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "failed"
                run.phase = "failed"
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                db.commit()

if __name__ == "__main__":
    import uvicorn
    log.info("Starting UIDAI Testing Automation API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)