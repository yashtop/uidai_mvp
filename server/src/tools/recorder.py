# server/src/tools/recorder.py - CREATE THIS FILE

import logging
import subprocess
from pathlib import Path
from typing import Dict

log = logging.getLogger(__name__)

async def start_recording_session(run_id: str, url: str) -> Dict:
    """
    Start Playwright codegen for user to record test
    Opens browser in headed mode
    """
    
    log.info(f"[{run_id}] Starting Playwright codegen...")
    
    # Create output directory
    output_dir = Path(f"/tmp/uidai_runs/{run_id}/recording")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "recorded_test.py"
    
    try:
        # Run playwright codegen - opens browser for user to record
        cmd = [
            'playwright',
            'codegen',
            url,
            '--output', str(output_file),
            '--target', 'python-async'
        ]
        
        log.info(f"[{run_id}] Running: {' '.join(cmd)}")
        log.info(f"[{run_id}] Browser will open - close it when done recording")
        
        # Run codegen (blocks until user closes browser)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            log.error(f"[{run_id}] Codegen failed: {result.stderr}")
            return {
                'ok': False,
                'error': result.stderr or 'Recording failed'
            }
        
        # Check if file was created
        if not output_file.exists():
            return {
                'ok': False,
                'error': 'No recording file generated'
            }
        
        log.info(f"[{run_id}] ✅ Recording saved: {output_file}")
        
        return {
            'ok': True,
            'test_file': str(output_file),
            'size': output_file.stat().st_size
        }
        
    except subprocess.TimeoutExpired:
        log.error(f"[{run_id}] Recording timed out")
        return {
            'ok': False,
            'error': 'Recording session timed out (10 minutes)'
        }
    except Exception as e:
        log.error(f"[{run_id}] Recording failed: {e}", exc_info=True)
        return {
            'ok': False,
            'error': str(e)
        }