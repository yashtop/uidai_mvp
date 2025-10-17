# server/src/tools/langchain_tools.py
from .discovery import discover
from .generator import generate_tests
from .runner import run_playwright_tests
from .healer import get_heal_suggestions, apply_patch

def pipeline_run(run_id, url, level=1, headed=False, heal="manual", models=None):
    # Simple sequential pipeline (no LLM planner) that returns structured progress
    out = {"runId": run_id, "steps": []}
    # 1. discovery
    disc = discover(run_id, url, level=level, out_dir="/tmp/uidai_runs")
    out["steps"].append({"step": "discovery", "result": disc})
    # 2. generator
    gen = generate_tests(run_id, url, disc.get("pages", []), models=models, out_dir="/tmp/uidai_runs")
    out["steps"].append({"step": "generator", "result": gen})
    if not gen.get("ok"):
        return out
    gen_dir = "/tmp/uidai_runs/{}/generator/tests".format(run_id)
    # 3. runner
    runres = run_playwright_tests(run_id, gen_dir, headed)
    out["steps"].append({"step": "runner", "result": runres})
    # 4. healer (only if failed)
    if runres.get("exitCode", 1) != 0:
        # prepare failingTestInfo stub from report
        failing = {"report": runres.get("report")}
        heal_res = get_heal_suggestions(run_id, failing, [p["path"] for p in gen.get("tests", [])], models=models, out_dir="/tmp/uidai_runs")
        out["steps"].append({"step": "healer", "result": heal_res})
    return out