# server/main.py
import uuid, json, time, os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
from src.tools.langchain_tools import pipeline_run
from src.tools.healer import apply_patch  # new import
import threading

app = FastAPI(title="UIDAI Agentic Runner")

RUNS_META = {}
RUNS_LOGS = {}

def append_log(run_id, level, msg, meta=None):
    entry = {"time": time.time(), "level": level, "msg": msg, "meta": meta}
    RUNS_LOGS.setdefault(run_id, []).append(entry)

class RunRequest(BaseModel):
    url: str
    level: int = 1
    preset: str = "quick"
    seed: str = None
    headed: bool = False
    heal: str = "manual"
    models: list = None

def work_run(run_id, payload):
    try:
        append_log(run_id, "info", "Starting pipeline")
        res = pipeline_run(run_id, payload["url"], level=payload.get("level",1), headed=payload.get("headed", False), heal=payload.get("heal", "manual"), models=payload.get("models"))
        # persist metadata
        RUNS_META[run_id].update({"status": "finished" if any(s["step"]=="runner" and s["result"].get("exitCode",1)==0 for s in res["steps"]) else "failed", "result": res})
        append_log(run_id, "info", "Pipeline finished", {"summary": RUNS_META[run_id]["status"]})
    except Exception as e:
        append_log(run_id, "error", f"pipeline error: {e}")

@app.post("/api/run")
def create_run(req: RunRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    meta = req.dict()
    meta.update({"runId": run_id, "createdAt": time.time(), "status": "queued"})
    RUNS_META[run_id] = meta
    RUNS_LOGS[run_id] = []
    append_log(run_id, "info", "Enqueued")
    background_tasks.add_task(work_run, run_id, meta)
    return {"runId": run_id, "status": "running"}

@app.get("/api/run/{run_id}")
def get_run(run_id: str):
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="not found")
    return RUNS_META[run_id]

@app.get("/api/run/{run_id}/logs/stream")
def stream_logs(run_id: str):
    if run_id not in RUNS_LOGS:
        raise HTTPException(status_code=404, detail="not found")
    def event_stream():
        last = 0
        while True:
            entries = RUNS_LOGS.get(run_id, [])
            while last < len(entries):
                e = entries[last]; last += 1
                yield f"data: {json.dumps(e)}\n\n"
            # finish when status set to finished/failed
            status = RUNS_META.get(run_id, {}).get("status")
            if status in ("finished","failed"):
                break
            time.sleep(0.5)
        entries = RUNS_LOGS.get(run_id, [])
        while last < len(entries):
            e = entries[last]; last += 1
            yield f"data: {json.dumps(e)}\n\n"
        yield f"data: {json.dumps({'msg':'stream closed'})}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

class ApplyPatchBody(BaseModel):
    patchId: str

@app.post("/api/run/{run_id}/healer/apply")
def healer_apply(run_id: str, body: ApplyPatchBody, background_tasks: BackgroundTasks):
    """
    Manual approve endpoint:
    - looks for healer suggestion file(s) under /tmp/uidai_runs/{run_id}/healer/*.json
    - finds the suggestion with matching patchId, applies it (apply_patch), and enqueues a rerun.
    """
    if run_id not in RUNS_META:
        raise HTTPException(status_code=404, detail="run not found")

    healer_dir = Path("/tmp/uidai_runs") / run_id / "healer"
    if not healer_dir.exists():
        raise HTTPException(status_code=404, detail="no healer suggestions found")

    # find suggestion with given patchId
    patch = None
    for f in healer_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for s in data.get("suggestions", []) if isinstance(data, dict) else []:
                if s.get("patchId") == body.patchId:
                    patch = s
                    break
            if patch:
                break
        except Exception:
            continue

    if not patch:
        raise HTTPException(status_code=404, detail="patchId not found in healer suggestions")

    # Determine generated tests dir from previous run metadata
    gen_dir = Path("/tmp/uidai_runs") / run_id / "generator" / "tests"
    if not gen_dir.exists():
        raise HTTPException(status_code=500, detail="generated tests dir not found to apply patch")

    # Apply patch (apply_patch writes file backups)
    try:
        apply_res = apply_patch(patch, str(gen_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"apply patch failed: {e}")

    append_log(run_id, "info", f"Manual patch approved: {body.patchId}", {"apply_res": apply_res})
    # enqueue a rerun using a new run id (so original run preserves history)
    new_run_id = run_id + "-rerun-" + str(int(time.time()))
    new_meta = RUNS_META[run_id].copy()
    new_meta.update({"runId": new_run_id, "createdAt": time.time(), "status": "queued"})
    RUNS_META[new_run_id] = new_meta
    RUNS_LOGS[new_run_id] = []
    background_tasks.add_task(work_run, new_run_id, new_meta)
    return {"success": True, "newRunId": new_run_id}