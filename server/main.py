# server/main.py - COMPLETE UPDATES

import os
import sys
import logging
import uuid
import asyncio
import json
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException,  WebSocket, WebSocketDisconnect,BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session


# Database
from src.database.connection import init_db, get_db, get_db_session
from src.database.models import  RunLog, Artifact,TestRun, TestResult
from src.database.state_updater import state_updater



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
            run = db.query(TestRun).filter(TestRun.id == run_id).first()
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
async def create_run(request: dict, background_tasks: BackgroundTasks):
    """
    Create a new test run
    """
    try:
        # Extract parameters
        url = request.get("url")
        test_creation_mode = request.get("testCreationMode", "ai")
        story = request.get("story", "")
        mode = request.get("mode", "headless")
        preset = request.get("preset", "balanced")
        run_name = request.get("runName", f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        auto_heal = request.get("autoHeal", True)
        max_heal_attempts = request.get("maxHealAttempts", 3)
        
        # Validate
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Generate run ID
        run_id = str(uuid.uuid4())
        
        # Create run in database
        with get_db() as session:
            run = TestRun(
                run_id=run_id,
                run_name=run_name,
                target_url=url,
                test_creation_mode=test_creation_mode,
                mode=mode,
                preset=preset,
                user_story=story,
                auto_heal=auto_heal,
                max_heal_attempts=max_heal_attempts,
                status="queued",
                phase="starting"
            )
            
            session.add(run)
            session.commit()
            
            log.info(f"✅ Created run {run_id} in database")
        
        config = {
            "url": url,
            "testCreationMode": test_creation_mode,
            "story": story,
            "mode": mode,
            "preset": preset,
            "autoHeal": auto_heal,
            "maxHealAttempts": max_heal_attempts,
        }
        
        # ✅ Execute run in background AFTER returning response
        background_tasks.add_task(queue_manager._execute_run, run_id, config)
        
        log.info(f"✅ Queued run {run_id}")
        
        # ✅ Return immediately - don't wait for execution
        return {
            "ok": True,
            "runId": run_id,
            "message": "Run created and queued successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# server/main.py - FIX get_run ENDPOINT

@app.get("/api/run/{run_id}")
async def get_run(run_id: str):
    """
    Get run details by ID
    """
    try:
        with get_db() as session:
            from src.database.models import TestRun
            
            # Query by run_id (the UUID string), not by id (the integer)
            run = session.query(TestRun).filter_by(run_id=run_id).first()
            
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            
            # Build response
            return {
                "runId": run.run_id,
                "runName": run.run_name,
                "targetUrl": run.target_url,
                "testCreationMode": run.test_creation_mode,
                "mode": run.mode,
                "preset": run.preset,
                "status": run.status,
                "phase": run.phase,
                "createdAt": run.created_at.isoformat() if run.created_at else None,
                "startedAt": run.started_at.isoformat() if run.started_at else None,
                "completedAt": run.completed_at.isoformat() if run.completed_at else None,
                "pagesDiscovered": run.pages_discovered,
                "testsTotal": run.tests_total,
                "testsPassed": run.tests_passed,
                "testsFailed": run.tests_failed,
                "testsSkipped": run.tests_skipped,
                "durationSeconds": run.duration_seconds,
                "healingAttempts": run.healing_attempts,
                "isHealed": run.is_healed,
                "errorMessage": run.error_message,
                # Additional data
                "discovery": run.discovery_data,
                "tests": {
                    "count": run.tests_count,
                    "files": run.generated_tests
                },
                "config": {
                    "autoHeal": run.auto_heal,
                    "maxHealAttempts": run.max_heal_attempts,
                    "userStory": run.user_story
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/api/runs")
def get_all_runs(db: Session = Depends(get_db_session)):
    """Get all runs"""
    runs = db.query(TestRun).order_by(TestRun.created_at.desc()).all()
    
    runs_data = [
        {
            "runId": run.id,
            "runName": run.run_name,
            "targetUrl": run.target_url,
            "status": run.status,
            "phase": run.phase,
            "preset": run.preset,
            "mode": run.mode,
            "createdAt": run.created_at.isoformat() if run.created_at else None,
            "completedAt": run.completed_at.isoformat() if run.completed_at else None,
        }
        for run in runs
    ]
    
    return {"runs": runs_data}

@app.get("/api/runs/compare")
def compare_runs(run_ids: str, db: Session = Depends(get_db_session)):
    """Compare multiple runs"""
    run_id_list = run_ids.split(",")
    
    if len(run_id_list) < 2:
        raise HTTPException(status_code=400, detail="Please provide at least 2 run IDs to compare")
    
    runs = db.query(TestRun).filter(Run.id.in_(run_id_list)).all()
    
    if len(runs) != len(run_id_list):
        raise HTTPException(status_code=404, detail="One or more runs not found")
        
    runs_data = []
    total_pass_rate = 0
    total_duration = 0
    all_failed_tests = {}
    
    for run in runs:
        tests_passed = run.tests_passed or 0
        tests_total = run.tests_total or 0
        pass_rate = (tests_passed / tests_total * 100) if tests_total > 0 else 0
        total_pass_rate += pass_rate
        
        duration = run.total_duration_seconds or 0
        total_duration += duration
        
        # Extract failed tests (assuming execution_result is JSON with failed_tests)
        if run.execution_result and isinstance(run.execution_result, dict):
            for test in run.execution_result.get("failed_tests", []):
                all_failed_tests[test] = all_failed_tests.get(test, 0) + 1
        
        runs_data.append({
            "run_id": run.id,
            "target_url": run.target_url,
            "status": run.status,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "duration_seconds": duration,
            "tests": {
                "passed": tests_passed,
                "failed": run.tests_failed or 0,
                "total": tests_total,
                "pass_rate": round(pass_rate, 2),
            },
        })
        
    # Find common failures
    common_failures = [
        {"test": test, "occurrences": count}
        for test, count in all_failed_tests.items() if count > 1
    ]
    
    # Summary
    summary = {
        "total_runs": len(runs),
        "avg_pass_rate": round(total_pass_rate / len(runs), 2) if runs else 0,
        "avg_duration": round(total_duration / len(runs), 2) if runs else 0,
        "common_failures": sorted(common_failures, key=lambda x: x['occurrences'], reverse=True)
    }

    return {"runs": runs_data, "summary": summary}


# ============================================
# LOGS STREAMING ENDPOINT - FIXED
# ============================================

@app.get("/api/run/{run_id}/logs/stream")
async def stream_logs(run_id: str):
    """Server-Sent Events endpoint for streaming logs"""
    
    async def log_generator():
        log_file = Path(f"/tmp/uidai_runs/{run_id}/run.log")
        
        # Send initial connection message
        yield "data: " + json.dumps({'line': f'Connected to logs for {run_id[:12]}...'}) + "\n\n"
        
        if not log_file.exists():
            yield "data: " + json.dumps({'line': 'Log file not found yet. Waiting...'}) + "\n\n"
            
            # Wait for log file
            for _ in range(30):
                await asyncio.sleep(1)
                if log_file.exists():
                    break
            else:
                yield "data: " + json.dumps({'line': 'Log file not created. Run may have failed.'}) + "\n\n"
                return
        
        # Stream logs
        try:
            with open(log_file, 'r') as f:
                # Send existing lines
                for line in f:
                    yield "data: " + json.dumps({'line': line.rstrip()}) + "\n\n"
                
                file_position = f.tell()
                
                # Follow new lines
                while True:
                    line = f.readline()
                    if line:
                        yield "data: " + json.dumps({'line': line.rstrip()}) + "\n\n"
                        file_position = f.tell()
                    else:
                        # Check if run is complete
                        run = state_updater.get_run_state(run_id)
                        if run and run.get('status') in ['completed', 'failed']:
                            status = run.get('status', 'completed')
                            yield "data: " + json.dumps({'line': f'Run {status}. Closing stream.'}) + "\n\n"
                            break
                        
                        await asyncio.sleep(1)
                        f.seek(file_position)
                        
        except Exception as e:
            log.error(f"Error streaming logs: {e}")
            yield "data: " + json.dumps({'line': f'Error: {str(e)}'}) + "\n\n"
    
    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================
# DISCOVERY ENDPOINT
# ============================================

@app.get("/api/run/{run_id}/discovery")
async def get_discovery(run_id: str):
    """Get discovery results"""
    try:
        with get_db() as session:
            run = session.query(TestRun).filter_by(run_id=run_id).first()
            
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            
            if not run.discovery_data:
                return {"ok": False, "message": "Discovery not completed yet"}
            
            discovery = run.discovery_data
            
            return {
                "ok": True,
                "pages": discovery.get("pages", []),
                "metadata": {
                    "runId": run_id,
                    "start": discovery.get("start"),
                    "end": discovery.get("end"),
                    "pagesCount": len(discovery.get("pages", []))
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting discovery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# TESTS ENDPOINT
# ============================================

@app.get("/api/run/{run_id}/tests")
async def get_tests(run_id: str):
    """Get generated test files"""
    try:
        with get_db() as session:
            run = session.query(TestRun).filter_by(run_id=run_id).first()
            
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            
            if not run.generated_tests:
                return {"ok": False, "message": "Tests not generated yet"}
            
            tests = []
            for test_info in run.generated_tests:
                test_path = Path(test_info.get("path", ""))
                
                content = ""
                if test_path.exists():
                    try:
                        content = test_path.read_text()
                    except:
                        pass
                
                tests.append({
                    "filename": test_info.get("filename", ""),
                    "path": str(test_path),
                    "lines": test_info.get("lines", 0),
                    "content": content,
                    "error": test_info.get("error")
                })
            
            return {
                "ok": True,
                "tests": tests,
                "count": len(tests),
                "metadata": {
                    "model": run.story_model or "unknown",
                    "seed": run.final_story or ""
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HEALING ENDPOINT
# ============================================

@app.get("/api/run/{run_id}/healing")
async def get_healing(run_id: str):
    """Get healing attempts and results"""
    try:
        with get_db() as session:
            run = session.query(TestRun).filter_by(run_id=run_id).first()
            
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            
            if not run.healing_attempts or run.healing_attempts == 0:
                return {
                    "ok": True,
                    "attempts": [],
                    "healed": False,
                    "healing_attempts": 0,
                    "final_result": {}
                }
            
            healing_data = run.healing_result or {}
            
            return {
                "ok": True,
                "attempts": healing_data.get("attempts", []),
                "healed": run.is_healed or False,
                "healing_attempts": run.healing_attempts,
                "final_result": {
                    "summary": {
                        "passed": run.tests_passed,
                        "failed": run.tests_failed,
                        "total": run.tests_total
                    }
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting healing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FAILURES ENDPOINT
# ============================================

@app.get("/api/run/{run_id}/failures")
async def get_failures(run_id: str):
    """Get failed tests with screenshots"""
    try:
        with get_db() as session:
            run = session.query(TestRun).filter_by(run_id=run_id).first()
            
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            
            failed_tests = session.query(TestResult).filter_by(
                run_id=run_id,
                outcome="failed"
            ).all()
            
            if not failed_tests:
                return {"ok": True, "failures": [], "failureCount": 0}
            
            failures = []
            artifacts_dir = Path(f"/tmp/uidai_runs/{run_id}/generator/artifacts")
            
            for test in failed_tests:
                screenshots = []
                if artifacts_dir.exists():
                    for img in artifacts_dir.glob("*.png"):
                        screenshots.append({
                            "name": img.name,
                            "url": f"/api/run/{run_id}/artifacts/{img.name}",
                            "size": img.stat().st_size
                        })
                
                failures.append({
                    "test": {
                        "nodeid": test.nodeid,
                        "outcome": test.outcome,
                        "duration": test.duration,
                        "error": test.error_message,
                        "call": {"longrepr": test.error_message}
                    },
                    "hasScreenshot": len(screenshots) > 0,
                    "screenshots": screenshots
                })
            
            return {
                "ok": True,
                "failures": failures,
                "failureCount": len(failures)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting failures: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# RESULTS ENDPOINT
# ============================================

@app.get("/api/run/{run_id}/results")
async def get_results(run_id: str):
    """Get test execution results"""
    try:
        with get_db() as session:
            run = session.query(TestRun).filter_by(run_id=run_id).first()
            
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            
            if run.status not in ['completed', 'failed']:
                return {"ok": False, "message": "Tests not executed yet"}
            
            test_results = session.query(TestResult).filter_by(run_id=run_id).all()
            
            tests = []
            for test in test_results:
                tests.append({
                    "nodeid": test.nodeid,
                    "outcome": test.outcome,
                    "duration": test.duration,
                    "error": test.error_message
                })
            
            return {
                "ok": True,
                "summary": {
                    "total": run.tests_total,
                    "passed": run.tests_passed,
                    "failed": run.tests_failed,
                    "skipped": run.tests_skipped,
                    "duration": run.duration_seconds or 0
                },
                "tests": tests,
                "exitCode": 0 if run.tests_failed == 0 else 1
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STATISTICS ENDPOINT
# ============================================

@app.get("/api/runs/stats")
async def get_stats():
    """Get overall statistics"""
    try:
        with get_db() as session:
            total_runs = session.query(TestRun).count()
            completed_runs = session.query(TestRun).filter_by(status="completed").count()
            failed_runs = session.query(TestRun).filter_by(status="failed").count()
            
            total_tests = session.query(TestResult).count()
            passed_tests = session.query(TestResult).filter_by(outcome="passed").count()
            
            last_24h = datetime.now() - timedelta(hours=24)
            recent_runs = session.query(TestRun).filter(
                TestRun.created_at >= last_24h
            ).count()
            
            success_rate = round((completed_runs / total_runs) * 100, 1) if total_runs > 0 else 0
            overall_pass_rate = round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
            
            return {
                "total_runs": total_runs,
                "success_rate": success_rate,
                "overall_pass_rate": overall_pass_rate,
                "total_tests_executed": total_tests,
                "total_tests_passed": passed_tests,
                "recent_activity": {"runs_last_24h": recent_runs}
            }
            
    except Exception as e:
        log.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# TRENDS ENDPOINT
# ============================================

@app.get("/api/runs/trends")
async def get_trends(days: int = 7):
    """Get trends over time"""
    try:
        with get_db() as session:
            cutoff = datetime.now() - timedelta(days=days)
            
            runs = session.query(TestRun).filter(
                TestRun.created_at >= cutoff,
                TestRun.status.in_(["completed", "failed"])
            ).order_by(TestRun.created_at).all()
            
            data_points = []
            for run in runs:
                pass_rate = round((run.tests_passed / run.tests_total) * 100, 1) if run.tests_total > 0 else 0
                
                data_points.append({
                    "timestamp": run.created_at.isoformat(),
                    "pass_rate": pass_rate,
                    "duration_seconds": run.duration_seconds or 0,
                    "tests_passed": run.tests_passed,
                    "tests_failed": run.tests_failed
                })
            
            # Summary
            total_runs = len(runs)
            successful_runs = len([r for r in runs if r.status == "completed"])
            failed_runs = len([r for r in runs if r.status == "failed"])
            
            pass_rates = [p["pass_rate"] for p in data_points]
            durations = [p["duration_seconds"] for p in data_points]
            
            avg_pass_rate = round(sum(pass_rates) / len(pass_rates), 1) if pass_rates else 0
            median_pass_rate = round(sorted(pass_rates)[len(pass_rates) // 2], 1) if pass_rates else 0
            
            avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
            median_duration = round(sorted(durations)[len(durations) // 2], 1) if durations else 0
            
            import statistics
            pass_rate_stdev = round(statistics.stdev(pass_rates), 1) if len(pass_rates) > 1 else 0
            
            return {
                "data_points": data_points,
                "summary": {
                    "total_runs": total_runs,
                    "successful_runs": successful_runs,
                    "failed_runs": failed_runs,
                    "avg_pass_rate": avg_pass_rate,
                    "median_pass_rate": median_pass_rate,
                    "pass_rate_stdev": pass_rate_stdev,
                    "avg_duration": avg_duration,
                    "median_duration": median_duration,
                    "total_tests": sum(run.tests_total for run in runs),
                    "total_passed": sum(run.tests_passed for run in runs),
                    "total_failed": sum(run.tests_failed for run in runs),
                    "overall_pass_rate": avg_pass_rate,
                    "healing_used_count": len([r for r in runs if r.healing_attempts > 0])
                }
            }
            
    except Exception as e:
        log.error(f"Error getting trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FLAKY TESTS ENDPOINT
# ============================================

@app.get("/api/runs/flaky-tests")
async def get_flaky_tests(days: int = 7):
    """Get flaky tests"""
    try:
        with get_db() as session:
            cutoff = datetime.now() - timedelta(days=days)
            
            results = session.query(TestResult).join(TestRun).filter(
                TestRun.created_at >= cutoff
            ).all()
            
            test_stats = {}
            for result in results:
                name = result.nodeid
                if name not in test_stats:
                    test_stats[name] = {"passed": 0, "failed": 0, "total": 0}
                
                test_stats[name]["total"] += 1
                if result.outcome == "passed":
                    test_stats[name]["passed"] += 1
                else:
                    test_stats[name]["failed"] += 1
            
            flaky = []
            for name, stats in test_stats.items():
                if stats["passed"] > 0 and stats["failed"] > 0:
                    pass_rate = round((stats["passed"] / stats["total"]) * 100, 1)
                    
                    flakiness = abs(0.5 - (stats["passed"] / stats["total"]))
                    flakiness_score = round(1 - (flakiness * 2), 2)
                    
                    flaky.append({
                        "test_name": name,
                        "total_runs": stats["total"],
                        "passed": stats["passed"],
                        "failed": stats["failed"],
                        "pass_rate": pass_rate,
                        "flakiness_score": flakiness_score
                    })
            
            flaky.sort(key=lambda x: x["flakiness_score"], reverse=True)
            
            return {
                "flaky_tests_found": len(flaky),
                "tests": flaky
            }
            
    except Exception as e:
        log.error(f"Error getting flaky tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# COMPARE RUNS ENDPOINT
# ============================================

@app.get("/api/runs/compare")
async def compare_runs(run_ids: str):
    """Compare multiple runs"""
    try:
        ids = [rid.strip() for rid in run_ids.split(",")]
        
        if len(ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 run IDs required")
        
        if len(ids) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 runs")
        
        with get_db() as session:
            runs = []
            for run_id in ids:
                run = session.query(TestRun).filter_by(run_id=run_id).first()
                if run:
                    pass_rate = round((run.tests_passed / run.tests_total) * 100, 1) if run.tests_total > 0 else 0
                    
                    runs.append({
                        "run_id": run.run_id,
                        "target_url": run.target_url,
                        "status": run.status,
                        "created_at": run.created_at.isoformat(),
                        "duration_seconds": run.duration_seconds or 0,
                        "tests": {
                            "total": run.tests_total,
                            "passed": run.tests_passed,
                            "failed": run.tests_failed,
                            "pass_rate": pass_rate
                        }
                    })
            
            avg_pass_rate = round(sum(r["tests"]["pass_rate"] for r in runs) / len(runs), 1) if runs else 0
            avg_duration = round(sum(r["duration_seconds"] for r in runs) / len(runs), 1) if runs else 0
            
            return {
                "runs": runs,
                "summary": {
                    "total_runs": len(runs),
                    "avg_pass_rate": avg_pass_rate,
                    "avg_duration": avg_duration,
                    "common_failures": []
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error comparing runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ARTIFACTS ENDPOINT
# ============================================

@app.get("/api/run/{run_id}/artifacts/{filename}")
async def get_artifact(run_id: str, filename: str):
    """Serve artifact files"""
    artifact_path = Path(f"/tmp/uidai_runs/{run_id}/generator/artifacts/{filename}")
    
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return FileResponse(artifact_path)



from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio
import json

# ✅ CORRECT: Use plain Python dict, NOT a Pydantic model
active_connections: Dict[str, List[WebSocket]] = {}


# WebSocket endpoint
@app.websocket("/ws/run/{run_id}/progress")
async def websocket_progress(websocket: WebSocket, run_id: str):
    await websocket.accept()
    
    if run_id not in active_connections:
        active_connections[run_id] = []
    active_connections[run_id].append(websocket)
    
    log.info(f"✅ WebSocket connected for run {run_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
                
                # Send current progress
                with get_db() as session:
                    run = session.query(TestRun).filter_by(run_id=run_id).first()  # ✅ Fixed
                    if run:
                        progress_data = {
                            "phase": run.phase or "starting",
                            "status": run.status or "running",
                            "details": run.details or "Processing...",
                            "progress": run.progress or 0,
                        }
                        await websocket.send_json(progress_data)
                    
    except WebSocketDisconnect:
        log.info(f"WebSocket disconnected for run {run_id}")
        if run_id in active_connections:
            active_connections[run_id].remove(websocket)
            if not active_connections[run_id]:
                del active_connections[run_id]
# Helper function to broadcast progress updates
async def broadcast_progress(run_id: str, progress_data: dict):
    """
    Broadcast progress update to all connected clients for this run
    """
    if run_id in active_connections:
        disconnected = []
        for websocket in active_connections[run_id]:
            try:
                await websocket.send_json(progress_data)
                log.debug(f"📤 Sent progress to {run_id}: {progress_data}")
            except Exception as e:
                log.error(f"Failed to send to websocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            active_connections[run_id].remove(ws)
        
        if not active_connections[run_id]:
            del active_connections[run_id]
# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)