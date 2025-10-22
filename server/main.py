# server/main.py
"""
FastAPI Backend for UIDAI Testing Automation MVP
Fixed imports for PYTHONPATH=server execution
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
import asyncio
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime

# Fixed imports for your project structure
from src.tools.discovery import discover
from src.tools.generator import generate_tests, SCENARIO_TEMPLATES
from src.tools.runner import run_playwright_tests
from src.tools.healer import get_heal_suggestions, apply_patch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="UIDAI Testing Automation API",
    version="1.0.0",
    description="Automated testing for UIDAI.gov.in portal"
)

# CORS - Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (use Redis/PostgreSQL for production)
RUNS_STORE = {}
LOGS_STORE = {}

# === Models matching UI expectations ===

class RunRequest(BaseModel):
    """Request model from RunCreator.jsx"""
    url: str  # Target URL
    mode: str = "headless"  # "headless" or "headed"
    preset: str = "balanced"  # "quick", "balanced", or "deep"
    useOllama: bool = True  # Always use Ollama for MVP
    runName: Optional[str] = None
    scenario: Optional[str] = None  # Template ID or empty for auto
    maxHealAttempts: int = 1

# === Utility Functions ===

def get_run_dir(run_id: str) -> Path:
    """Get run directory path"""
    return Path("/tmp/uidai_runs") / run_id

def add_log(run_id: str, message: str):
    """Add timestamped log message"""
    if run_id not in LOGS_STORE:
        LOGS_STORE[run_id] = []
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_msg = f"[{timestamp}] {message}"
    LOGS_STORE[run_id].append(log_msg)
    log.info(f"[{run_id}] {message}")

def get_preset_config(preset: str) -> Dict[str, Any]:
    """Convert preset to discovery configuration"""
    configs = {
        "quick": {"level": 1, "max_pages": 5, "timeout": 180},
        "balanced": {"level": 1, "max_pages": 15, "timeout": 300},
        "deep": {"level": 2, "max_pages": 30, "timeout": 600}
    }
    return configs.get(preset, configs["balanced"])

async def run_pipeline_background(run_id: str, config: dict):
    """
    Background task to execute the complete testing pipeline
    Matches the flow expected by UI components
    """
    try:
        url = config["url"]
        add_log(run_id, f"🚀 Starting pipeline for {url}")
        add_log(run_id, f"Preset: {config['preset']}, Mode: {config['mode']}")
        RUNS_STORE[run_id]["status"] = "running"
        
        # Get preset configuration
        preset_config = get_preset_config(config["preset"])
        
        # Phase 1: Discovery
        add_log(run_id, "📡 Phase 1: Discovery - Crawling UIDAI website...")
        RUNS_STORE[run_id]["phase"] = "discovery"
        
        discovery_result = discover(
            run_id=run_id,
            url=url,
            level=preset_config["level"],
            max_pages=preset_config["max_pages"]
        )
        
        pages = discovery_result.get("pages", [])
        add_log(run_id, f"✓ Discovery complete: {len(pages)} pages found")
        RUNS_STORE[run_id]["discovery"] = discovery_result
        
        if len(pages) == 0:
            raise Exception("No pages discovered. Website might be unreachable.")
        
        # Phase 2: Scenario Selection/Generation
        add_log(run_id, "🎯 Phase 2: Determining test scenario...")
        RUNS_STORE[run_id]["phase"] = "scenario"
        
        scenario_param = config.get("scenario", "").strip()
        
        if not scenario_param:
            add_log(run_id, "🤖 No scenario specified, using automatic detection")
            scenario_param = "auto"
        elif scenario_param in SCENARIO_TEMPLATES:
            template = SCENARIO_TEMPLATES[scenario_param]
            add_log(run_id, f"✓ Using template: {template['name']}")
        else:
            add_log(run_id, f"⚠️  Unknown scenario '{scenario_param}', using auto")
            scenario_param = "auto"
        
        # Phase 3: Test Generation
        add_log(run_id, "⚙️ Phase 3: Generating test code with AI...")
        RUNS_STORE[run_id]["phase"] = "generation"
        
        # Use Ollama models from your system
        models = ["mistral:latest", "llama3.2:latest", "deepseek-r1:7b"] if config["useOllama"] else []
        
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
        model_used = gen_result.get("metadata", {}).get("model", "unknown")

        scenario_obj = gen_result.get("scenario") or {}
        scenario_name = scenario_obj.get("name", "Unknown")
        
        add_log(run_id, f"✓ Generated {test_count} test file(s) using {model_used}")
        add_log(run_id, f"✓ Scenario: {scenario_name}")
        RUNS_STORE[run_id]["tests"] = gen_result
        
        # Phase 4: Test Execution
        add_log(run_id, "🧪 Phase 4: Executing tests with Playwright...")
        RUNS_STORE[run_id]["phase"] = "execution"
        
        tests_dir = get_run_dir(run_id) / "generator" / "tests"
        headed = config["mode"] == "headed"
        
        run_result = run_playwright_tests(
            run_id=run_id,
            gen_dir=str(tests_dir),
            headed=headed,
            timeout_seconds=preset_config["timeout"]
        )
        
        exit_code = run_result.get("exitCode", 1)
        
        # Parse results
        report = run_result.get("report", {})
        summary = report.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        
        if exit_code == 0:
            add_log(run_id, f"✅ All tests passed! ({passed}/{total})")
            RUNS_STORE[run_id]["status"] = "completed"
        else:
            add_log(run_id, f"❌ Some tests failed ({failed}/{total} failed)")
            
            # Phase 5: Self-Healing (only if configured and tests failed)
            if config.get("maxHealAttempts", 0) > 0:
                add_log(run_id, "🔧 Phase 5: Analyzing failures for self-healing...")
                RUNS_STORE[run_id]["phase"] = "healing"
                
                heal_result = get_heal_suggestions(
                    run_id=run_id,
                    failingTestInfo={"report": report},
                    generated_files=[t["path"] for t in gen_result.get("tests", [])],
                    models=models
                )
                
                RUNS_STORE[run_id]["healing"] = heal_result
                
                if heal_result.get("ok"):
                    suggestions = heal_result.get("suggestions", [])
                    add_log(run_id, f"💡 Generated {len(suggestions)} healing suggestion(s)")
                else:
                    add_log(run_id, "⚠️ Could not generate healing suggestions")
            
            RUNS_STORE[run_id]["status"] = "failed"
        
        RUNS_STORE[run_id]["results"] = run_result
        RUNS_STORE[run_id]["phase"] = "completed"
        RUNS_STORE[run_id]["completedAt"] = datetime.now().isoformat()
        
        add_log(run_id, "🏁 Pipeline completed")
        
    except Exception as e:
        log.exception(f"Pipeline failed for run {run_id}: {e}")
        add_log(run_id, f"💥 Pipeline failed: {str(e)}")
        RUNS_STORE[run_id]["status"] = "failed"
        RUNS_STORE[run_id]["phase"] = "failed"
        RUNS_STORE[run_id]["error"] = str(e)
        RUNS_STORE[run_id]["completedAt"] = datetime.now().isoformat()


# === API Endpoints ===

@app.get("/")
async def root():
    """API root - health check"""
    return {
        "service": "UIDAI Testing Automation API",
        "version": "1.0.0",
        "status": "running",
        "target": "https://uidai.gov.in/en/"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "runs": len(RUNS_STORE)
    }

@app.post("/api/run")
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Start a new test run
    Endpoint matching UI expectations from RunCreator.jsx
    """
    run_id = str(uuid.uuid4())
    run_name = request.runName or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Store run configuration
    RUNS_STORE[run_id] = {
        "runId": run_id,
        "runName": run_name,
        "targetUrl": request.url,
        "status": "queued",
        "phase": "queued",
        "createdAt": datetime.now().isoformat(),
        "config": {
            "url": request.url,
            "mode": request.mode,
            "preset": request.preset,
            "useOllama": request.useOllama,
            "scenario": request.scenario or "",
            "maxHealAttempts": request.maxHealAttempts
        }
    }
    
    LOGS_STORE[run_id] = []
    
    log.info(f"Created run: {run_id} for {request.url}")
    
    # Start background pipeline
    background_tasks.add_task(
        run_pipeline_background,
        run_id,
        RUNS_STORE[run_id]["config"]
    )
    
    return {
        "ok": True,
        "runId": run_id,
        "runName": run_name,
        "message": "Run started successfully"
    }

@app.get("/api/runs")
async def list_runs():
    """
    Get list of all runs
    Used by RunsDashboard.jsx
    """
    runs = [
        {
            "runId": r["runId"],
            "runName": r.get("runName", r["runId"][:8]),
            "targetUrl": r["targetUrl"],
            "status": r["status"],
            "phase": r.get("phase", "unknown"),
            "createdAt": r["createdAt"],
            "completedAt": r.get("completedAt")
        }
        for r in sorted(
            RUNS_STORE.values(),
            key=lambda x: x["createdAt"],
            reverse=True
        )
    ]
    return {"runs": runs}

@app.get("/api/run/{run_id}")
async def get_run(run_id: str):
    """Get detailed run information"""
    if run_id not in RUNS_STORE:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RUNS_STORE[run_id]

@app.get("/api/run/{run_id}/discovery")
async def get_discovery(run_id: str):
    """
    Get discovery results
    Used by DiscoveryView.jsx
    """
    if run_id not in RUNS_STORE:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = RUNS_STORE[run_id]
    
    if "discovery" not in run:
        return {"ok": False, "message": "Discovery not yet completed"}
    
    discovery = run["discovery"]
    return {
        "ok": True,
        "pages": discovery.get("pages", []),
        "metadata": discovery.get("metadata", {})
    }

@app.get("/api/run/{run_id}/tests")
async def get_tests(run_id: str):
    """
    Get generated tests
    Used by TestsView.jsx
    """
    if run_id not in RUNS_STORE:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = RUNS_STORE[run_id]
    
    if "tests" not in run:
        return {"ok": False, "message": "Tests not yet generated"}
    
    tests_data = run["tests"]
    return {
        "ok": True,
        "tests": tests_data.get("tests", []),
        "count": tests_data.get("count", 0),
        "metadata": tests_data.get("metadata", {})
    }

@app.get("/api/run/{run_id}/results")
async def get_results(run_id: str):
    """
    Get test execution results
    Used by ResultsView.jsx
    """
    if run_id not in RUNS_STORE:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = RUNS_STORE[run_id]
    
    if "results" not in run:
        return {"ok": False, "message": "Results not yet available"}
    
    results = run["results"]
    report = results.get("report", {})
    
    tests = report.get("tests", [])
    summary = report.get("summary", {})
    
    return {
        "ok": True,
        "summary": summary,
        "tests": tests,
        "exitCode": results.get("exitCode", 1),
        "timestamp": results.get("timestamp")
    }

@app.get("/api/run/{run_id}/healing")
async def get_healing(run_id: str):
    """Get self-healing suggestions"""
    if run_id not in RUNS_STORE:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = RUNS_STORE[run_id]
    
    if "healing" not in run:
        return {"ok": False, "message": "No healing suggestions available"}
    
    return run["healing"]

@app.get("/api/run/{run_id}/logs/stream")
async def stream_logs(run_id: str):
    """
    Stream logs via Server-Sent Events
    Used by RunsDashboard.jsx for live log streaming
    """
    if run_id not in RUNS_STORE:
        raise HTTPException(status_code=404, detail="Run not found")
    
    async def event_generator():
        # Send existing logs first
        if run_id in LOGS_STORE:
            for log_line in LOGS_STORE[run_id]:
                yield f"data: {json.dumps({'line': log_line})}\n\n"
                await asyncio.sleep(0.01)
        
        # Stream new logs
        last_count = len(LOGS_STORE.get(run_id, []))
        
        while True:
            if run_id in LOGS_STORE:
                logs = LOGS_STORE[run_id]
                if len(logs) > last_count:
                    for log_line in logs[last_count:]:
                        yield f"data: {json.dumps({'line': log_line})}\n\n"
                    last_count = len(logs)
            
            # Check if run completed
            if run_id in RUNS_STORE:
                status = RUNS_STORE[run_id].get("status")
                if status in ["completed", "failed"]:
                    yield f"data: {json.dumps({'line': f'--- {status.upper()} ---'})}\n\n"
                    break
            
            await asyncio.sleep(0.5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/run/{run_id}/report")
async def get_full_report(run_id: str):
    """
    Get comprehensive report with all phases
    Used by ReportView.jsx
    """
    if run_id not in RUNS_STORE:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = RUNS_STORE[run_id]
    
    return {
        "ok": True,
        "runId": run_id,
        "runName": run.get("runName"),
        "status": run["status"],
        "targetUrl": run["targetUrl"],
        "phases": {
            "discovery": run.get("discovery"),
            "tests": run.get("tests"),
            "results": run.get("results"),
            "healing": run.get("healing")
        },
        "timeline": {
            "createdAt": run["createdAt"],
            "completedAt": run.get("completedAt")
        },
        "logs": LOGS_STORE.get(run_id, [])
    }

@app.get("/api/scenarios/templates")
async def get_scenario_templates():
    """
    Get available scenario templates
    Can be used by UI to show template options
    """
    return {
        "ok": True,
        "templates": [
            {
                "id": key,
                "name": val["name"],
                "description": val["description"],
                "steps": len(val.get("steps", []))
            }
            for key, val in SCENARIO_TEMPLATES.items()
        ]
    }

if __name__ == "__main__":
    import uvicorn
    log.info("Starting UIDAI Testing Automation API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)