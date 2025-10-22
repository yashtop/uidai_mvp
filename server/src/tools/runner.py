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

    # CRITICAL: Create artifacts folder in run_dir (not inside tests)
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    log.info(f"Artifacts directory: {artifacts_dir}")

    env = os.environ.copy()
    env["UIDAI_HEADED"] = "1" if headed else "0"
    # Set environment variable so tests know where to save artifacts
    env["ARTIFACTS_DIR"] = str(artifacts_dir)

    json_report = run_dir / "report.json"
    
    # run pytest with json-report plugin
    cmd = [
        sys.executable, "-m", "pytest",
        str(dest_tests),
        "-q",
        "--json-report",
        f"--json-report-file={json_report}",
        f"--alluredir={run_dir / 'allure-results'}",
    ]

    log.info("Running tests: %s", " ".join(cmd))
    log.info(f"Working directory: {run_dir}")
    
    proc = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        env=env, 
        text=True,
        cwd=str(run_dir)  # Run from run_dir so relative paths work
    )
    
    stdout = []
    try:
        out, _ = proc.communicate(timeout=timeout_seconds)
        if out:
            stdout = out.splitlines()
            # Print last 20 lines to logs
            for line in stdout[-20:]:
                log.info(f"TEST: {line}")
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        stdout = out.splitlines() if out else []
    
    exit_code = proc.returncode if proc.returncode is not None else 1

    # Upload artifacts
    uploaded = []
    if artifacts_dir.exists() and any(artifacts_dir.iterdir()):
        try:
            log.info(f"Uploading artifacts from: {artifacts_dir}")
            uploaded = upload_dir(run_id, str(artifacts_dir))
            log.info(f"Uploaded {len(uploaded)} artifacts")
        except Exception as e:
            log.exception("MinIO upload artifacts failed: %s", e)
    else:
        log.warning(f"No artifacts found at: {artifacts_dir}")

    # Upload report
    if json_report.exists():
        try:
            log.info(f"Uploading report from: {json_report}")
            report_key = upload_file(run_id, str(json_report))
            if report_key:
                uploaded.append(report_key)
        except Exception as e:
            log.exception("MinIO upload report failed: %s", e)

    # Parse JSON report
    report_json = None
    summary = None
    if json_report.exists():
        try:
            report_json = json.loads(json_report.read_text(encoding="utf-8"))
            # Extract summary
            if report_json and "summary" in report_json:
                summary = {
                    "total": int(report_json["summary"].get("total", 0)),
                    "passed": int(report_json["summary"].get("passed", 0)),
                    "failed": int(report_json["summary"].get("failed", 0)),
                    "skipped": int(report_json["summary"].get("skipped", 0)),
                    "duration": float(report_json["summary"].get("duration", 0)),
                }
        except Exception as e:
            log.exception("Failed to parse json report: %s", e)

    result = {
        "ok": exit_code == 0,
        "exitCode": exit_code,
        "summary": summary,
        "tests": report_json.get("tests", []) if report_json else [],
        "stdout": "\n".join(stdout[-500:]),
        "artifacts": uploaded,
        "reportPath": f"{run_id}/report.json" if json_report.exists() else None,
    }
    return result