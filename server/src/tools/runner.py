# server/src/tools/runner.py
import os
import sys
import subprocess
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from .minio_client import upload_dir, upload_file
import logging

log = logging.getLogger(__name__)

BASE_RUN_DIR = Path(os.getenv("UIDAI_RUNS_DIR", "/tmp/uidai_runs"))

def make_run_dir(run_id: str) -> Path:
    d = BASE_RUN_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def run_playwright_tests(run_id: str, gen_dir: str, headed: bool, playwright_options: Dict[str, Any]=None, timeout_seconds: int = 300) -> Dict[str, Any]:
    run_dir = make_run_dir(run_id)
    tests_dir = Path(gen_dir)

    if not tests_dir.exists():
        raise FileNotFoundError(f"generated tests dir not found: {tests_dir}")

    # copy tests to run workspace
    dest_tests = run_dir / "tests"
    if dest_tests.exists():
        shutil.rmtree(dest_tests)
    shutil.copytree(tests_dir, dest_tests)

    # ensure artifacts folder exists (tests should write there)
    artifacts_dir = dest_tests / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["UIDAI_HEADED"] = "1" if headed else "0"

    json_report = run_dir / "report.json"
    # run pytest with json-report plugin
    cmd = [
    sys.executable, "-m", "pytest",
    str(dest_tests),
    "-q",
    "--json-report",
    f"--json-report-file={str(run_dir / 'report.json')}",
    f"--alluredir={str(run_dir / 'allure-results')}",
    ]

    log.info("Running tests: %s", " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)
    stdout = []
    try:
        out, _ = proc.communicate(timeout=timeout_seconds)
        if out:
            stdout = out.splitlines()
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        stdout = out.splitlines() if out else []
    exit_code = proc.returncode if proc.returncode is not None else 1

    uploaded = []
    if artifacts_dir.exists():
        try:
            uploaded = upload_dir(str(artifacts_dir), f"{run_id}/artifacts")
        except Exception as e:
            log.exception("MinIO upload artifacts failed: %s", e)

    if json_report.exists():
        try:
            uploaded.append(upload_file(str(json_report), f"{run_id}/report.json"))
        except Exception as e:
            log.exception("MinIO upload report failed: %s", e)

    # attempt to parse JSON report for summary
    report_json = None
    if json_report.exists():
        try:
            report_json = json.loads(json_report.read_text(encoding="utf-8"))
        except Exception as e:
            log.exception("Failed to parse json report: %s", e)

    result = {
        "runId": run_id,
        "exitCode": exit_code,
        "stdout": "\n".join(stdout[-500:]),
        "artifacts": uploaded,
        "report": report_json,
        "reportPath": f"{run_id}/report.json" if json_report.exists() else None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    return result