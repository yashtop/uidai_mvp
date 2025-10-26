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



def run_playwright_tests(
    run_id: str,
    gen_dir: str,
    headed: bool = False,
    timeout_seconds: int = 900
) -> Dict:
    """
    Run Playwright tests with pytest
    """
    gen_path = Path(gen_dir)
    tests_dir = gen_path / "tests"
    
    if not tests_dir.exists():
        return {
            "ok": False,
            "error": f"Tests directory not found: {tests_dir}",
            "summary": {"total": 0, "passed": 0, "failed": 0}
        }
    
    # Create artifacts directory
    artifacts_dir = gen_path / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    log.info(f"Artifacts directory: {artifacts_dir}")
    log.info(f"Headed mode: {headed}")
    
    # Setup report paths
    report_file = gen_path / "report.json"
    allure_dir = gen_path / "allure-results"
    allure_dir.mkdir(exist_ok=True)
    
    # Setup pytest.ini in the run directory
    pytest_ini_content = """[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts = -v --tb=short
markers =
    asyncio: mark test as async
"""
    pytest_ini_path = gen_path / "pytest.ini"
    pytest_ini_path.write_text(pytest_ini_content)
    
    # Build pytest command
    python_path = os.path.join(os.environ.get('VIRTUAL_ENV', ''), 'bin', 'python3.13')
    if not os.path.exists(python_path):
        python_path = 'python3'
    
    cmd = [
        python_path,
        '-m', 'pytest',
        str(tests_dir),
        '-q',
        '--json-report',
        f'--json-report-file={report_file}',
        f'--alluredir={allure_dir}'
    ]
    
    log.info(f"Running tests: {' '.join(cmd)}")
    
    # Set environment variables
    env = os.environ.copy()
    env['ARTIFACTS_DIR'] = str(artifacts_dir)  # ← CRITICAL: Set this for tests
    env['HEADED'] = '1' if headed else '0'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    log.info(f"Environment: HEADED={env['HEADED']}, ARTIFACTS_DIR={env['ARTIFACTS_DIR']}")
    log.info(f"Working directory: {gen_path}")
    
    try:
        # Run pytest
        result = subprocess.run(
            cmd,
            cwd=str(gen_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        
        # Log output
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    log.info(f"TEST: {line}")
        
        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip():
                    log.warning(f"TEST ERROR: {line}")
        
        # Parse report
        if report_file.exists():
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            
            summary = report_data.get('summary', {})
            
            # Upload artifacts if they exist
            _upload_artifacts(run_id, artifacts_dir)
            
            # Upload report
            _upload_report(run_id, report_file)
            
            return {
                "ok": True,
                "summary": {
                    "total": summary.get('total', 0),
                    "passed": summary.get('passed', 0),
                    "failed": summary.get('failed', 0),
                    "skipped": summary.get('skipped', 0)
                },
                "tests": report_data.get('tests', []),
                "duration": report_data.get('duration', 0),
                "artifacts": [str(p) for p in list(artifacts_dir.glob("*.png")) + list(artifacts_dir.glob("*.webm"))],
                "reportPath": f"{run_id}/report.json"
            }
        else:
            log.warning(f"Report file not found: {report_file}")
            return {
                "ok": False,
                "error": "Report file not generated",
                "summary": {"total": 0, "passed": 0, "failed": 0},
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        log.error(f"Test execution timed out after {timeout_seconds}s")
        return {
            "ok": False,
            "error": f"Timeout after {timeout_seconds}s",
            "summary": {"total": 0, "passed": 0, "failed": 0}
        }
    except Exception as e:
        log.error(f"Test execution failed: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e),
            "summary": {"total": 0, "passed": 0, "failed": 0}
        }

def _upload_artifacts(run_id: str, artifacts_dir: Path):
    """Upload test artifacts to MinIO using upload_file() from minio_client"""
    if not artifacts_dir.exists():
        log.warning(f"No artifacts found at: {artifacts_dir}")
        return
    
    artifact_files = list(artifacts_dir.glob("*.png")) + \
                     list(artifacts_dir.glob("*.webm")) + \
                     list(artifacts_dir.glob("*.mp4"))
    
    if not artifact_files:
        log.info("No artifact files to upload")
        return

    uploaded = []
    for file_path in artifact_files:
        try:
            # upload_file signature: upload_file(run_id: str, local_path: str, content_type: str = None) -> str | None
            key = upload_file(run_id, str(file_path))
            if key:
                uploaded.append(key)
                log.info("Uploaded artifact %s -> s3://%s/%s", file_path.name, os.getenv("MINIO_BUCKET", "uidai-artifacts"), key)
            else:
                log.warning("upload_file returned None for %s", file_path)
        except Exception as e:
            log.exception("Failed to upload artifact %s: %s", file_path, e)
    
    log.info("Completed artifact uploads: %d uploaded", len(uploaded))


def _upload_report(run_id: str, report_file: Path):
    """Upload test report to MinIO using upload_file()"""
    if not report_file.exists():
        log.warning("Report file does not exist: %s", report_file)
        return
    
    try:
        key = upload_file(run_id, str(report_file))
        if key:
            log.info("Uploaded report -> s3://%s/%s", os.getenv("MINIO_BUCKET", "uidai-artifacts"), key)
        else:
            log.warning("upload_file returned None for report %s", report_file)
    except Exception as e:
        log.exception("Failed to upload report %s: %s", report_file, e)
