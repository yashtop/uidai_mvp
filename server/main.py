# server/main.py
"""
UIDAI Testing Automation API - Fixed Async/Sync Issue
Uses threading instead of asyncio for background tasks
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends,WebSocket, WebSocketDisconnect,Query
from fastapi.responses import StreamingResponse,FileResponse, JSONResponse
from pathlib import Path
import mimetypes
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

import logging
import uuid
from pathlib import Path
from datetime import datetime
import threading
import json
from typing import List, Optional
from datetime import datetime, timedelta

import statistics

# Enhanced imports
from src.tools.discovery_enhanced import discover_with_selectors
from src.tools.generator import generate_tests, SCENARIO_TEMPLATES
from src.tools.runner import run_playwright_tests
from src.tools.auto_healer import auto_heal_and_rerun
from src.database.connection import get_db, get_db_session, init_db
from src.database.models import Run, RunLog
from src.tools.progress_tracker import progress_tracker
from src.tools.recorder import launch_codegen_recorder
from pathlib import Path
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
            use_recorder = config.get("useRecorder", False)
            add_log_to_db(db, run_id, f"🚀 Starting pipeline for {url}")
            # If recorder mode, launch interactive browser FIRST
            if use_recorder:
                asyncio.run(progress_tracker.broadcast_progress(
                    run_id,
                    progress_tracker.update_phase(
                        run_id, "starting", "running",
                        "🎥 Launching Interactive Recorder...", 5
                    )
                ))
                
                add_log_to_db(db, run_id, "🎥 Launching Interactive Recorder...")
                add_log_to_db(db, run_id, "👉 Browser will open - perform your test actions")
                
                from src.tools.recorder import launch_codegen_recorder
                from src.tools.runner import get_run_dir
                
                recorder_result = launch_codegen_recorder(
                    run_id=run_id,
                    url=url,
                    output_dir=get_run_dir(run_id) / "recorded"
                )
                
                if recorder_result.get("ok"):
                    recorded_file = recorder_result.get("output_file")
                    add_log_to_db(db, run_id, f"✅ Recording saved: {recorded_file}")
                    
                    # Update progress
                    asyncio.run(progress_tracker.broadcast_progress(
                        run_id,
                        progress_tracker.update_phase(
                            run_id, "starting", "completed",
                            "Recording complete!", 10
                        )
                    ))
                else:
                    error = recorder_result.get("message", "Unknown error")
                    add_log_to_db(db, run_id, f"⚠️ Recording issue: {error}")
            
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
            
            headed_mode = config.get("mode") == "headed" or config.get("useRecorder", False)

            if config.get("useRecorder"):
                add_log_to_db(db, run_id, "🎥 Running tests in VISIBLE mode (Recorder)")

            run_result = run_playwright_tests(
                run_id=run_id,
                gen_dir=str(tests_dir),
                headed=headed_mode,  # ← USE THIS VARIABLE
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
                "mode": r.mode,
                "preset": r.preset,
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
        "autoHeal": request.autoHeal,
        "useRecorder": request.useRecorder
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
    """Sync pipeline function with real-time progress updates"""
    with get_db() as db:
        try:
            url = config["url"]
            use_recorder = config.get("useRecorder", False)
            
            add_log_to_db(db, run_id, f"🚀 Starting pipeline for {url}")
            
            # ============================================================
            # 🎥 RECORDER MODE - Skip discovery & generation
            # ============================================================
            if use_recorder:
                add_log_to_db(db, run_id, "🎥 Visual Recorder Mode - Manual Test Creation")
                add_log_to_db(db, run_id, "⏭️ Skipping discovery & AI generation")
                
                asyncio.run(progress_tracker.broadcast_progress(
                    run_id,
                    progress_tracker.update_phase(
                        run_id, "starting", "running",
                        "🎥 Opening browser for recording...", 10
                    )
                ))
                
                # Import recorder
                
                
                run_dir = get_run_dir(run_id)
                recorded_dir = run_dir / "recorded"
                recorded_dir.mkdir(parents=True, exist_ok=True)
                
                # Launch codegen - BLOCKS until user closes browser
                add_log_to_db(db, run_id, "🎬 Launching Playwright Codegen...")
                recorder_result = launch_codegen_recorder(
                    run_id=run_id,
                    url=url,
                    output_dir=recorded_dir
                )
                
                if not recorder_result.get("ok"):
                    raise Exception(f"Recording failed: {recorder_result.get('message')}")
                
                recorded_file = Path(recorder_result.get("output_file"))
                add_log_to_db(db, run_id, f"✅ Recording saved: {recorded_file.name}")
                
                # Copy recorded test to tests directory
                tests_dir = run_dir / "generator" / "tests"
                tests_dir.mkdir(parents=True, exist_ok=True)
                
                import shutil
                target_file = tests_dir / "test_recorded.py"
                shutil.copy(recorded_file, target_file)
                
                add_log_to_db(db, run_id, f"📝 Recorded test saved to: {target_file.name}")

                # Save data to database for UI
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    run.discovery_result = {
                        "ok": True,
                        "pages": [{"url": url, "title": "Manual Recording", "selectors": []}],
                        "stats": {"mode": "recorder"}
                    }
                    run.generation_result = {
                        "ok": True,
                        "count": 1,
                        "tests": [{"name": "test_recorded", "type": "recorded"}],
                        "mode": "recorder"
                    }
                    run.phase = "execution"
                    db.commit()
                
                # Update progress - skip to 60% (skip discovery & generation)
                asyncio.run(progress_tracker.broadcast_progress(
                    run_id,
                    progress_tracker.update_phase(
                        run_id, "generation", "completed",
                        "Manual test recorded", 60
                    )
                ))
                
                # Phase 3: Execute ONLY the recorded test
                add_log_to_db(db, run_id, "🧪 Phase 3: Executing recorded test...")
                asyncio.run(progress_tracker.broadcast_progress(
                    run_id,
                    progress_tracker.update_phase(
                        run_id, "execution", "running",
                        "Running recorded test...", 70
                    )
                ))
                
                preset_config = get_preset_config(config["preset"])
                
                run_result = run_playwright_tests(
                    run_id=run_id,
                    gen_dir=str(tests_dir),
                    headed=True,  # Keep visible
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
                
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    run.execution_result = run_result
                    run.status = "completed" if passed == total else "failed"
                    run.phase = "completed"
                    run.completed_at = datetime.utcnow()
                    db.commit()
                
                if passed == total:
                    add_log_to_db(db, run_id, f"✅ Recorded test passed! ({passed}/{total})")
                    asyncio.run(progress_tracker.broadcast_progress(
                        run_id,
                        progress_tracker.update_phase(
                            run_id, "completed", "success",
                            f"Recorded test passed!", 100
                        )
                    ))
                else:
                    add_log_to_db(db, run_id, f"⚠️ Recorded test failed ({passed}/{total})")
                    asyncio.run(progress_tracker.broadcast_progress(
                        run_id,
                        progress_tracker.update_phase(
                            run_id, "completed", "failed",
                            f"Test failed", 100
                        )
                    ))
                
                add_log_to_db(db, run_id, "🏁 Pipeline completed")
                return  # ← EXIT HERE - Skip normal pipeline
            
            # ============================================================
            # If NOT recorder mode, continue with NORMAL pipeline
            # ============================================================
            
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
            add_log_to_db(db, run_id, "📡 Phase 1: Discovery...")
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "discovery", "running",
                    f"Discovering pages on {url}...", 10 if not use_recorder else 25
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
                    f"Found {len(pages)} pages, {selectors_count} elements", 30 if not use_recorder else 40
                )
            ))
            
            if run:
                run.discovery_result = discovery_result
                run.phase = "generation"
                db.commit()
            
            # Phase 2: Generation
            add_log_to_db(db, run_id, "⚙️ Phase 2: Generating tests...")
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "generation", "running",
                    "AI is generating test cases...", 40 if not use_recorder else 50
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
            
            # If recorder was used, add to count
            if use_recorder:
                test_count += 1  # Add the recorded test
                add_log_to_db(db, run_id, f"✓ Generated {test_count} test(s) (1 recorded + {test_count-1} AI-generated)")
            else:
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
            add_log_to_db(db, run_id, "🧪 Phase 3: Executing tests...")
            asyncio.run(progress_tracker.broadcast_progress(
                run_id,
                progress_tracker.update_phase(
                    run_id, "execution", "running",
                    f"Running {test_count} tests...", 70
                )
            ))
            
            tests_dir = get_run_dir(run_id) / "generator" / "tests"
            
            # Use headed mode if recorder was used OR if mode is headed
            headed_mode = config["mode"] == "headed" or use_recorder
            
            if use_recorder:
                add_log_to_db(db, run_id, "🎥 Running tests in VISIBLE mode (Recorder)")
            
            run_result = run_playwright_tests(
                run_id=run_id,
                gen_dir=str(tests_dir),
                headed=headed_mode,  # ← MODIFIED
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
                add_log_to_db(db, run_id, f"✅ All tests passed! ({passed}/{total})")
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
                add_log_to_db(db, run_id, f"🔧 Phase 4: Auto-healing ({failed} failures)...")
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
                    headed=headed_mode,  # ← MODIFIED
                    timeout_seconds=preset_config["timeout"]
                )
                
                if run:
                    run.healing_result = healing_result
                    db.commit()
                
                if healing_result.get("healed"):
                    attempts = healing_result.get("healing_attempts", 0)
                    add_log_to_db(db, run_id, f"✅ Healed after {attempts} attempt(s)!")
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
                    add_log_to_db(db, run_id, "⚠️ Healing incomplete")
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
            
            add_log_to_db(db, run_id, "🏁 Pipeline completed")
            
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

# Add these endpoints to server/src/api/routes.py






# ============================================================
# COMPARISON ENDPOINTS
# ============================================================

@app.get("/api/runs/compare")
async def compare_runs(
    run_ids: str = Query(..., description="Comma-separated run IDs")
):
    """
    Compare multiple test runs side-by-side
    
    Example: /api/runs/compare?run_ids=abc-123,def-456
    """
    run_id_list = [rid.strip() for rid in run_ids.split(",")]
    
    if len(run_id_list) < 2:
        raise HTTPException(400, "Need at least 2 run IDs to compare")
    
    if len(run_id_list) > 5:
        raise HTTPException(400, "Cannot compare more than 5 runs at once")
    
    with get_db() as db:
        runs = []
        for run_id in run_id_list:
            run = db.query(Run).filter(Run.id == run_id).first()
            if not run:
                raise HTTPException(404, f"Run {run_id} not found")
            runs.append(run)
        
        # Build comparison data
        comparison = {
            "runs": [],
            "summary": {
                "total_runs": len(runs),
                "avg_pass_rate": 0,
                "avg_duration": 0,
                "common_failures": []
            }
        }
        
        total_pass_rate = 0
        total_duration = 0
        all_failures = {}
        
        for run in runs:
            results = run.execution_result or {}
            summary = results.get("summary", {})
            
            passed = int(summary.get("passed", 0))
            failed = int(summary.get("failed", 0))
            total = int(summary.get("total", 0))
            
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            # Calculate duration
            duration = 0
            if run.completed_at and run.created_at:
                duration = (run.completed_at - run.created_at).total_seconds()
            
            total_pass_rate += pass_rate
            total_duration += duration
            
            # Track failures
            if results.get("tests"):
                for test in results["tests"]:
                    if test.get("outcome") == "failed":
                        test_name = test.get("nodeid", "unknown")
                        all_failures[test_name] = all_failures.get(test_name, 0) + 1
            
            # Build run data
            run_data = {
                "run_id": run.id,
                "target_url": run.target_url,
                "status": run.status,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "duration_seconds": duration,
                "preset": run.preset,
                "mode": run.mode,
                "tests": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "pass_rate": round(pass_rate, 1)
                },
                "discovery": {
                    "pages": len(run.discovery_result.get("pages", [])) if run.discovery_result else 0
                },
                "healing": {
                    "used": bool(run.healing_result),
                    "attempts": run.healing_result.get("healing_attempts", 0) if run.healing_result else 0,
                    "healed": run.healing_result.get("healed", False) if run.healing_result else False
                }
            }
            
            comparison["runs"].append(run_data)
        
        # Calculate summary
        comparison["summary"]["avg_pass_rate"] = round(total_pass_rate / len(runs), 1)
        comparison["summary"]["avg_duration"] = round(total_duration / len(runs), 1)
        
        # Find common failures (appear in 2+ runs)
        common_failures = [
            {"test": test, "occurrences": count}
            for test, count in all_failures.items()
            if count >= 2
        ]
        comparison["summary"]["common_failures"] = sorted(
            common_failures, 
            key=lambda x: x["occurrences"], 
            reverse=True
        )[:10]  # Top 10
        
        return comparison


# ============================================================
# TRENDS & ANALYTICS ENDPOINTS
# ============================================================

@app.get("/api/runs/trends")
async def get_trends(
    days: int = Query(7, description="Number of days to analyze"),
    url: Optional[str] = Query(None, description="Filter by target URL")
):
    """
    Get test trends over time
    
    Example: /api/runs/trends?days=7&url=https://example.com
    """
    with get_db() as db:
        # Get runs from last N days
        since = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(Run).filter(
            Run.created_at >= since,
            Run.status.in_(["completed", "failed"])
        )
        
        if url:
            query = query.filter(Run.target_url == url)
        
        runs = query.order_by(Run.created_at.asc()).all()
        
        if not runs:
            return {
                "period_days": days,
                "total_runs": 0,
                "data_points": [],
                "summary": {}
            }
        
        # Build timeline data
        data_points = []
        all_pass_rates = []
        all_durations = []
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for run in runs:
            results = run.execution_result or {}
            summary = results.get("summary", {})
            
            passed = int(summary.get("passed", 0))
            failed = int(summary.get("failed", 0))
            total = int(summary.get("total", 0))
            
            pass_rate = (passed / total * 100) if total > 0 else 0
            all_pass_rates.append(pass_rate)
            
            duration = 0
            if run.completed_at and run.created_at:
                duration = (run.completed_at - run.created_at).total_seconds()
                all_durations.append(duration)
            
            total_tests += total
            total_passed += passed
            total_failed += failed
            
            data_points.append({
                "run_id": run.id,
                "timestamp": run.created_at.isoformat(),
                "pass_rate": round(pass_rate, 1),
                "duration_seconds": round(duration, 1),
                "tests_total": total,
                "tests_passed": passed,
                "tests_failed": failed,
                "status": run.status,
                "healing_used": bool(run.healing_result)
            })
        
        # Calculate summary stats
        summary = {
            "total_runs": len(runs),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "overall_pass_rate": round((total_passed / total_tests * 100) if total_tests > 0 else 0, 1),
            "avg_pass_rate": round(statistics.mean(all_pass_rates) if all_pass_rates else 0, 1),
            "median_pass_rate": round(statistics.median(all_pass_rates) if all_pass_rates else 0, 1),
            "pass_rate_stdev": round(statistics.stdev(all_pass_rates) if len(all_pass_rates) > 1 else 0, 1),
            "avg_duration": round(statistics.mean(all_durations) if all_durations else 0, 1),
            "median_duration": round(statistics.median(all_durations) if all_durations else 0, 1),
            "successful_runs": sum(1 for r in runs if r.status == "completed"),
            "failed_runs": sum(1 for r in runs if r.status == "failed"),
            "healing_used_count": sum(1 for r in runs if r.healing_result)
        }
        
        return {
            "period_days": days,
            "start_date": runs[0].created_at.isoformat(),
            "end_date": runs[-1].created_at.isoformat(),
            "total_runs": len(runs),
            "data_points": data_points,
            "summary": summary
        }


@app.get("/api/runs/flaky-tests")
async def get_flaky_tests(
    days: int = Query(7, description="Number of days to analyze"),
    min_runs: int = Query(3, description="Minimum runs to consider")
):
    """
    Detect flaky tests (tests that sometimes pass, sometimes fail)
    
    Example: /api/runs/flaky-tests?days=7&min_runs=3
    """
    with get_db() as db:
        since = datetime.utcnow() - timedelta(days=days)
        
        runs = db.query(Run).filter(
            Run.created_at >= since,
            Run.status.in_(["completed", "failed"])
        ).all()
        
        # Track test outcomes
        test_outcomes = {}  # {test_name: [pass, fail, pass, ...]}
        
        for run in runs:
            results = run.execution_result or {}
            tests = results.get("tests", [])
            
            for test in tests:
                test_name = test.get("nodeid", "unknown")
                outcome = test.get("outcome")
                
                if test_name not in test_outcomes:
                    test_outcomes[test_name] = []
                
                test_outcomes[test_name].append(outcome)
        
        # Find flaky tests
        flaky_tests = []
        
        for test_name, outcomes in test_outcomes.items():
            if len(outcomes) < min_runs:
                continue
            
            passed_count = outcomes.count("passed")
            failed_count = outcomes.count("failed")
            total = len(outcomes)
            
            # Flaky if it has both passes and failures
            if passed_count > 0 and failed_count > 0:
                flakiness_score = min(passed_count, failed_count) / total
                
                flaky_tests.append({
                    "test_name": test_name,
                    "total_runs": total,
                    "passed": passed_count,
                    "failed": failed_count,
                    "pass_rate": round((passed_count / total) * 100, 1),
                    "flakiness_score": round(flakiness_score, 2),
                    "outcomes": outcomes
                })
        
        # Sort by flakiness score (higher = more flaky)
        flaky_tests.sort(key=lambda x: x["flakiness_score"], reverse=True)
        
        return {
            "period_days": days,
            "total_tests_analyzed": len(test_outcomes),
            "flaky_tests_found": len(flaky_tests),
            "tests": flaky_tests
        }


@app.get("/api/runs/stats")
async def get_overall_stats():
    """
    Get overall platform statistics
    
    Example: /api/runs/stats
    """
    with get_db() as db:
        total_runs = db.query(func.count(Run.id)).scalar()
        
        completed_runs = db.query(func.count(Run.id)).filter(
            Run.status == "completed"
        ).scalar()
        
        failed_runs = db.query(func.count(Run.id)).filter(
            Run.status == "failed"
        ).scalar()
        
        # Get all execution results
        runs_with_results = db.query(Run).filter(
            Run.execution_result.isnot(None)
        ).all()
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for run in runs_with_results:
            summary = run.execution_result.get("summary", {})
            total_tests += int(summary.get("total", 0))
            total_passed += int(summary.get("passed", 0))
            total_failed += int(summary.get("failed", 0))
        
        # Recent activity (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_runs = db.query(func.count(Run.id)).filter(
            Run.created_at >= last_24h
        ).scalar()
        
        return {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "success_rate": round((completed_runs / total_runs * 100) if total_runs > 0 else 0, 1),
            "total_tests_executed": total_tests,
            "total_tests_passed": total_passed,
            "total_tests_failed": total_failed,
            "overall_pass_rate": round((total_passed / total_tests * 100) if total_tests > 0 else 0, 1),
            "recent_activity": {
                "runs_last_24h": recent_runs
            }
        }
if __name__ == "__main__":
    import uvicorn
    log.info("Starting UIDAI Testing Automation API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)