# server/main.py - ENHANCED VERSION
import uuid, json, time, os
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from src.tools.langchain_tools import pipeline_run
from src.tools.healer import apply_patch
import logging

log = logging.getLogger(__name__)

app = FastAPI(title="UIDAI Agentic Runner - Enhanced")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNS_META = {}
RUNS_LOGS = {}
BASE_RUN_DIR = Path(os.getenv("UIDAI_RUNS_DIR", "/tmp/uidai_runs"))

def append_log(run_id, level, msg, meta=None):
    entry = {"time": time.time(), "level": level, "msg": msg, "meta": meta}
    RUNS_LOGS.setdefault(run_id, []).append(entry)

class RunRequest(BaseModel):
    url: str
    mode: str = "headless"  # headless | headed
    preset: str = "balanced"  # quick | balanced | deep
    useOllama: bool = True
    runName: str = None
    maxHealAttempts: int = 1
    scenario: str = None  # NEW: scenario/seed support

def work_run(run_id, payload):
    """Background task that executes the pipeline"""
    try:
        append_log(run_id, "info", "Starting pipeline")
        
        # Map UI params to backend params
        level = 1 if payload.get("preset") == "quick" else (2 if payload.get("preset") == "balanced" else 3)
        headed = payload.get("mode") == "headed"
        seed = payload.get("scenario")  # Pass scenario as seed to generator
        
        # Execute pipeline
        res = pipeline_run(
            run_id,
            payload["url"],
            level=level,
            headed=headed,
            heal="auto",  # Enable auto-healing
            models=None,  # Use default models
        )
        
        # Update metadata
        success = any(
            s["step"] == "runner" and s["result"].get("exitCode", 1) == 0
            for s in res["steps"]
        )
        
        RUNS_META[run_id].update({
            "status": "completed" if success else "failed",
            "result": res,
            "completedAt": time.time()
        })
        
        append_log(run_id, "info", "Pipeline finished", {
            "summary": RUNS_META[run_id]["status"],
            "exitCode": res.get("steps", [{}])[-1].get("result", {}).get("exitCode")
        })
        
    except Exception as e:
        log.exception("Pipeline error for run %s: %s", run_id, e)
        RUNS_META[run_id].update({"status": "failed", "error": str(e)})
        append_log(run_id, "error", f"Pipeline error: {e}")


# ===========================
# EXISTING ENDPOINTS (Updated)
# ===========================

@app.post("/api/run")
def create_run(req: RunRequest, background_tasks: BackgroundTasks):
    """Create and start a new test run"""
    run_id = str(uuid.uuid4())
    meta = {
        "runId": run_id,
        "targetUrl": req.url,
        "mode": req.mode,
        "preset": req.preset,
        "scenario": req.scenario,
        "createdAt": time.time(),
        "status": "running",
    }
    RUNS_META[run_id] = meta
    RUNS_LOGS[run_id] = []
    append_log(run_id, "info", "Run queued", {"url": req.url})
    background_tasks.add_task(work_run, run_id, req.dict())
    return {"runId": run_id, "status": "running"}


@app.get("/api/run/{run_id}")
def get_run(run_id: str):
    """Get run metadata (includes full result if completed)"""
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="Run not found")
    return RUNS_META[run_id]


@app.get("/api/run/{run_id}/logs/stream")
def stream_logs(run_id: str):
    """Stream logs via Server-Sent Events"""
    if run_id not in RUNS_LOGS:
        raise HTTPException(status_code=404, detail="Run not found")
    
    def event_stream():
        last = 0
        while True:
            entries = RUNS_LOGS.get(run_id, [])
            while last < len(entries):
                e = entries[last]
                last += 1
                # Format log line for display
                line = f"[{e['level'].upper()}] {e['msg']}"
                yield f"data: {json.dumps({'line': line, 'raw': e})}\n\n"
            
            status = RUNS_META.get(run_id, {}).get("status")
            if status in ("completed", "failed"):
                break
            time.sleep(0.5)
        
        # Send final logs
        entries = RUNS_LOGS.get(run_id, [])
        while last < len(entries):
            e = entries[last]
            last += 1
            line = f"[{e['level'].upper()}] {e['msg']}"
            yield f"data: {json.dumps({'line': line, 'raw': e})}\n\n"
        
        yield f"data: {json.dumps({'line': '=== Stream closed ==='})}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ===========================
# NEW ENDPOINTS FOR UI
# ===========================

@app.get("/api/runs")
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query(None, regex="^(running|completed|failed|queued)$")
):
    """List all runs with pagination and filtering"""
    all_runs = list(RUNS_META.values())
    
    # Filter by status if provided
    if status:
        all_runs = [r for r in all_runs if r.get("status") == status]
    
    # Sort by creation time (newest first)
    all_runs.sort(key=lambda x: x.get("createdAt", 0), reverse=True)
    
    # Paginate
    total = len(all_runs)
    runs = all_runs[offset:offset + limit]
    
    return {
        "runs": runs,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/api/run/{run_id}/discovery")
def get_discovery(run_id: str):
    """Get discovery results (pages, selectors, elements)"""
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Read discovery summary from file
    discovery_file = BASE_RUN_DIR / run_id / "discovery" / "summary.json"
    
    if not discovery_file.exists():
        # Check if discovery step completed in metadata
        meta = RUNS_META[run_id]
        result = meta.get("result", {})
        steps = result.get("steps", [])
        disc_step = next((s for s in steps if s["step"] == "discovery"), None)
        
        if disc_step and disc_step.get("result"):
            return {
                "ok": True,
                "pages": disc_step["result"].get("pages", []),
                "metadata": disc_step["result"].get("metadata", {})
            }
        
        return {
            "ok": False,
            "message": "Discovery not yet completed or failed"
        }
    
    try:
        data = json.loads(discovery_file.read_text(encoding="utf-8"))
        return {
            "ok": True,
            "pages": data.get("pages", []),
            "metadata": data.get("meta", {})
        }
    except Exception as e:
        log.exception("Failed to read discovery file: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to read discovery: {e}")


@app.get("/api/run/{run_id}/tests")
def get_generated_tests(run_id: str):
    """Get generated test cases (before execution)"""
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Check metadata for generator step
    meta = RUNS_META[run_id]
    result = meta.get("result", {})
    steps = result.get("steps", [])
    gen_step = next((s for s in steps if s["step"] == "generator"), None)
    
    if not gen_step:
        return {
            "ok": False,
            "message": "Test generation not yet started"
        }
    
    gen_result = gen_step.get("result", {})
    
    if not gen_result.get("ok"):
        return {
            "ok": False,
            "message": "Test generation failed",
            "error": gen_result.get("message")
        }
    
    # Load actual test file contents
    tests = gen_result.get("tests", [])
    tests_with_content = []
    
    for t in tests:
        path = Path(t["path"])
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                tests_with_content.append({
                    "filename": t["filename"],
                    "path": str(path),
                    "content": content,
                    "lines": len(content.splitlines())
                })
            except Exception as e:
                log.warning("Failed to read test file %s: %s", path, e)
                tests_with_content.append({
                    "filename": t["filename"],
                    "path": str(path),
                    "error": str(e)
                })
    
    return {
        "ok": True,
        "tests": tests_with_content,
        "metadata": gen_result.get("metadata", {}),
        "count": len(tests_with_content)
    }


@app.get("/api/run/{run_id}/results")
def get_test_results(run_id: str):
    """Get test execution results (detailed pass/fail per test)"""
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Check metadata for runner step
    meta = RUNS_META[run_id]
    result = meta.get("result", {})
    steps = result.get("steps", [])
    run_step = next((s for s in steps if s["step"] == "runner"), None)
    
    if not run_step:
        return {
            "ok": False,
            "message": "Test execution not yet started"
        }
    
    run_result = run_step.get("result", {})
    
    # Parse JSON report if available
    report = run_result.get("report")
    
    if not report:
        return {
            "ok": False,
            "message": "Test execution completed but report not available",
            "exitCode": run_result.get("exitCode"),
            "stdout": run_result.get("stdout")
        }
    
    # Extract test results from pytest JSON report
    tests = []
    summary = report.get("summary", {})
    
    for test in report.get("tests", []):
        tests.append({
            "nodeid": test.get("nodeid"),
            "outcome": test.get("outcome"),  # passed | failed | skipped
            "duration": test.get("call", {}).get("duration", 0),
            "error": test.get("call", {}).get("longrepr") if test.get("outcome") == "failed" else None
        })
    
    return {
        "ok": True,
        "summary": {
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "duration": summary.get("duration", 0)
        },
        "tests": tests,
        "exitCode": run_result.get("exitCode"),
        "artifacts": run_result.get("artifacts", [])
    }


@app.get("/api/run/{run_id}/healing")
def get_healing_suggestions(run_id: str):
    """Get auto-healing suggestions"""
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Check metadata for healer step
    meta = RUNS_META[run_id]
    result = meta.get("result", {})
    steps = result.get("steps", [])
    heal_step = next((s for s in steps if s["step"] == "healer"), None)
    
    if not heal_step:
        return {
            "ok": False,
            "message": "Healing not triggered (no test failures)"
        }
    
    heal_result = heal_step.get("result", {})
    
    if not heal_result.get("ok"):
        return {
            "ok": False,
            "message": heal_result.get("message", "Healing failed")
        }
    
    return {
        "ok": True,
        "suggestions": heal_result.get("suggestions", []),
        "fromModel": heal_result.get("fromModel")
    }


@app.get("/api/run/{run_id}/report")
def get_report(run_id: str):
    """Get comprehensive report with all data"""
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="Run not found")
    
    meta = RUNS_META[run_id]
    
    if meta.get("status") not in ("completed", "failed"):
        return {
            "ok": False,
            "message": "Run not yet completed",
            "status": meta.get("status")
        }
    
    # Gather all data
    try:
        discovery_data = get_discovery(run_id)
    except:
        discovery_data = {"ok": False}
    
    try:
        tests_data = get_generated_tests(run_id)
    except:
        tests_data = {"ok": False}
    
    try:
        results_data = get_test_results(run_id)
    except:
        results_data = {"ok": False}
    
    try:
        healing_data = get_healing_suggestions(run_id)
    except:
        healing_data = {"ok": False}
    
    return {
        "runId": run_id,
        "targetUrl": meta.get("targetUrl"),
        "status": meta.get("status"),
        "createdAt": meta.get("createdAt"),
        "completedAt": meta.get("completedAt"),
        "duration": (meta.get("completedAt", time.time()) - meta.get("createdAt", time.time())),
        "discovery": discovery_data,
        "tests": tests_data,
        "results": results_data,
        "healing": healing_data,
        "scenario": meta.get("scenario"),
        "url": f"/report/{run_id}"  # For opening in new tab
    }


# ===========================
# HEALER ENDPOINTS (Updated)
# ===========================

class ApplyPatchBody(BaseModel):
    patchId: str

@app.post("/api/run/{run_id}/healer/apply")
def healer_apply(run_id: str, body: ApplyPatchBody, background_tasks: BackgroundTasks):
    """Manually approve and apply a healing patch"""
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="Run not found")
    
    healer_dir = BASE_RUN_DIR / run_id / "healer"
    if not healer_dir.exists():
        raise HTTPException(status_code=404, detail="No healer suggestions found")
    
    # Find suggestion with given patchId
    patch = None
    for f in healer_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            suggestions = data.get("suggestions", []) if isinstance(data, dict) else []
            for s in suggestions:
                if s.get("patchId") == body.patchId:
                    patch = s
                    break
            if patch:
                break
        except Exception:
            continue
    
    if not patch:
        raise HTTPException(status_code=404, detail="patchId not found")
    
    # Apply patch
    gen_dir = BASE_RUN_DIR / run_id / "generator" / "tests"
    if not gen_dir.exists():
        raise HTTPException(status_code=500, detail="Generated tests dir not found")
    
    try:
        apply_res = apply_patch(patch, str(gen_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Patch application failed: {e}")
    
    append_log(run_id, "info", f"Manual patch approved: {body.patchId}", {"apply_res": apply_res})
    
    # Create new run for retry
    new_run_id = f"{run_id}-healed-{int(time.time())}"
    new_meta = RUNS_META[run_id].copy()
    new_meta.update({
        "runId": new_run_id,
        "createdAt": time.time(),
        "status": "running",
        "parentRun": run_id
    })
    RUNS_META[new_run_id] = new_meta
    RUNS_LOGS[new_run_id] = []
    
    background_tasks.add_task(work_run, new_run_id, new_meta)
    
    return {"success": True, "newRunId": new_run_id}


# ===========================
# HEALTH CHECK
# ===========================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "runs": len(RUNS_META),
        "timestamp": time.time()
    }


@app.get("/")
def root():
    """API info"""
    return {
        "name": "UIDAI Agentic Test Runner API",
        "version": "2.0.0",
        "endpoints": {
            "runs": {
                "POST /api/run": "Create new test run",
                "GET /api/runs": "List all runs",
                "GET /api/run/{id}": "Get run metadata"
            },
            "data": {
                "GET /api/run/{id}/discovery": "Get discovery results",
                "GET /api/run/{id}/tests": "Get generated tests",
                "GET /api/run/{id}/results": "Get execution results",
                "GET /api/run/{id}/healing": "Get healing suggestions",
                "GET /api/run/{id}/report": "Get comprehensive report"
            },
            "streaming": {
                "GET /api/run/{id}/logs/stream": "Stream logs (SSE)"
            },
            "healing": {
                "POST /api/run/{id}/healer/apply": "Apply healing patch"
            }
        }
    }