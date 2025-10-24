# server/src/tools/recorder.py
"""
Visual Test Recorder using Playwright Codegen
FIXED: Generates Python code, not JavaScript
"""

import subprocess
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def launch_codegen_recorder(run_id: str, url: str, output_dir: Path) -> dict:
    """
    Launch Playwright Codegen for interactive visual recording
    Generates PYTHON code in pytest format
    """
    # FIXED: Use .py extension, not .spec.js
    output_file = output_dir / "recorded_test.py"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    log.info(f"[{run_id}] 🎥 Launching Playwright Codegen...")
    
    print("\n" + "="*70)
    print("🎥 PLAYWRIGHT CODEGEN - INTERACTIVE RECORDER")
    print("="*70)
    print(f"Recording URL: {url}")
    print(f"Output file: {output_file}")
    print("\n📋 Instructions:")
    print("  1. Browser will open with recording toolbar")
    print("  2. Perform your test actions (click, type, navigate)")
    print("  3. All actions are automatically recorded")
    print("  4. Close browser when done")
    print("="*70 + "\n")
    
    try:
        # FIXED: Use "python" target to generate Python code
        cmd = [
            "playwright",
            "codegen",
            url,
            "--target", "python",  # ← PYTHON, not python-pytest or javascript
            "--output", str(output_file)
        ]
        
        log.info(f"[{run_id}] Running: {' '.join(cmd)}")
        
        # Run codegen - blocks until user closes browser
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            # Check if file was created
            if output_file.exists():
                file_size = output_file.stat().st_size
                
                # Convert to pytest format
                log.info(f"[{run_id}] Converting to pytest format...")
                convert_to_pytest_format(output_file)
                
                log.info(f"[{run_id}] ✅ Recording saved: {output_file} ({file_size} bytes)")
                
                print("\n✅ Recording complete!")
                print(f"📁 Saved to: {output_file}")
                print(f"📊 File size: {file_size} bytes\n")
                
                return {
                    "ok": True,
                    "message": "Recording complete",
                    "output_file": str(output_file),
                    "file_size": file_size
                }
            else:
                log.warning(f"[{run_id}] ⚠️ Codegen completed but no file created")
                return {
                    "ok": False,
                    "message": "No recording file created (did you close without recording?)"
                }
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            log.error(f"[{run_id}] ❌ Codegen failed: {error_msg}")
            return {
                "ok": False,
                "message": f"Codegen failed: {error_msg}"
            }
            
    except subprocess.TimeoutExpired:
        log.error(f"[{run_id}] ⏱️ Codegen timeout (10 minutes)")
        return {
            "ok": False,
            "message": "Recording timed out after 10 minutes"
        }
    except FileNotFoundError:
        log.error(f"[{run_id}] ❌ Playwright not found in PATH")
        return {
            "ok": False,
            "message": "Playwright not installed. Run: playwright install"
        }
    except Exception as e:
        log.error(f"[{run_id}] ❌ Recorder error: {e}")
        return {
            "ok": False,
            "message": str(e)
        }


def convert_to_pytest_format(file_path: Path):
    """
    Convert sync Playwright code to pytest-compatible format
    """
    try:
        content = file_path.read_text()
        
        # Playwright codegen generates sync code like:
        # from playwright.sync_api import sync_playwright
        # with sync_playwright() as playwright:
        #     browser = playwright.chromium.launch(headless=False)
        #     ...
        
        # We need to wrap it in a test function
        pytest_code = """import pytest
from playwright.sync_api import sync_playwright, Page, expect

def test_recorded(page: Page):
    \"\"\"Recorded test from Playwright Codegen\"\"\"
"""
        
        # Extract the code inside sync_playwright context
        lines = content.split('\n')
        in_context = False
        indent_level = 0
        
        for line in lines:
            # Skip import lines
            if 'import' in line or 'from' in line:
                continue
            
            # Skip 'with sync_playwright()' line
            if 'with sync_playwright()' in line:
                in_context = True
                continue
            
            # Skip browser and context creation (pytest-playwright provides page)
            if 'browser = ' in line or '.launch(' in line:
                continue
            if 'context = ' in line or '.new_context(' in line:
                continue
            if 'page = ' in line and '.new_page()' in line:
                continue
            if '.close()' in line and ('browser' in line or 'context' in line):
                continue
            
            # Add remaining lines with proper indentation
            if in_context and line.strip():
                # Remove one level of indentation
                if line.startswith('    '):
                    pytest_code += line[4:] + '\n'
                else:
                    pytest_code += '    ' + line.strip() + '\n'
        
        # Write back
        file_path.write_text(pytest_code)
        log.info(f"Converted {file_path} to pytest format")
        
    except Exception as e:
        log.error(f"Error converting to pytest format: {e}")
        # If conversion fails, keep original file


def launch_inspector_recorder(run_id: str, url: str, output_dir: Path) -> dict:
    """
    Alternative: Launch browser with Inspector using Playwright API
    """
    from playwright.sync_api import sync_playwright
    
    log.info(f"[{run_id}] 🎥 Launching Inspector Recorder...")
    
    print("\n" + "="*70)
    print("🎥 PLAYWRIGHT INSPECTOR - INTERACTIVE MODE")
    print("="*70)
    print(f"URL: {url}")
    print("\n📋 Instructions:")
    print("  1. Browser and Inspector will open")
    print("  2. Click 'Record' button in Inspector")
    print("  3. Perform your test actions in browser")
    print("  4. Click 'Resume' in Inspector when done")
    print("="*70 + "\n")
    
    try:
        with sync_playwright() as p:
            # Launch with inspector
            browser = p.chromium.launch(
                headless=False,
                slow_mo=500,  # Slow down for visibility
                args=['--start-maximized']
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_video_dir=str(output_dir / "videos")
            )
            
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            print("\n✅ Browser opened!")
            print("🔴 Recording... (Inspector should be visible)")
            print("⏸️  Click 'Resume' in Inspector when done\n")
            
            # Pause for user interaction - opens Inspector
            page.pause()
            
            print("\n✅ Recording complete!")
            
            # Close gracefully
            context.close()
            browser.close()
            
            return {
                "ok": True,
                "message": "Recording complete",
                "videos": str(output_dir / "videos")
            }
            
    except Exception as e:
        log.error(f"[{run_id}] ❌ Inspector error: {e}")
        return {
            "ok": False,
            "message": str(e)
        }