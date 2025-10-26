# server/src/workflows/record_workflow.py - COMPLETE FILE

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from pathlib import Path

from ..state import TestRunState
from ..agents.discovery_agent import discovery_node

log = logging.getLogger(__name__)

def create_record_workflow():
    """
    Create LangGraph workflow for Record mode
    User manually records test, system converts to code
    """
    workflow = StateGraph(TestRunState)
    
    # Add nodes
    workflow.add_node("discovery", discovery_node)
    workflow.add_node("record", recording_node)
    workflow.add_node("analyze", analyze_recording_node)
    workflow.add_node("generate_code", generate_from_recording_node)
    workflow.add_node("execute", execution_node)
    workflow.add_node("heal", healing_node)
    
    # Set entry point
    workflow.set_entry_point("discovery")
    
    # Add edges
    workflow.add_edge("discovery", "record")
    workflow.add_edge("record", "analyze")
    workflow.add_edge("analyze", "generate_code")
    workflow.add_edge("generate_code", "execute")
    
    # Conditional healing
    workflow.add_conditional_edges(
        "execute",
        should_heal,
        {
            "heal": "heal",
            "complete": END
        }
    )
    
    workflow.add_edge("heal", "execute")
    
    # Compile
    app = workflow.compile()
    return app

async def recording_node(state: TestRunState) -> TestRunState:
    """Start recording session - opens browser for user"""
    run_id = state['run_id']
    url = state['url']
    
    log.info(f"[{run_id}] 🎬 Starting recording session...")
    log.info(f"[{run_id}] Browser will open - perform your test actions")
    
    try:
        # Start recording (opens browser in headed mode)
        import asyncio
        from functools import partial
        
        loop = asyncio.get_event_loop()
        recording_result = await loop.run_in_executor(
            None,
            partial(_start_recording_sync, run_id, url)
        )
        
        if not recording_result.get('ok'):
            raise Exception(recording_result.get('error', 'Recording failed'))
        
        recorded_path = recording_result.get('test_file')
        
        log.info(f"[{run_id}] ✅ Recording complete: {recorded_path}")
        
        return {
            **state,
            'recorded_test_path': recorded_path,
            'phase': 'recording_completed'
        }
        
    except Exception as e:
        log.error(f"[{run_id}] Recording failed: {e}", exc_info=True)
        return {
            **state,
            'status': 'failed',
            'error_message': f"Recording failed: {str(e)}",
            'phase': 'recording_failed'
        }

def _start_recording_sync(run_id: str, url: str) -> Dict:
    """Synchronous recording function"""
    import subprocess
    
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

async def analyze_recording_node(state: TestRunState) -> TestRunState:
    """Analyze recorded test to understand what was tested"""
    run_id = state['run_id']
    recorded_path = state.get('recorded_test_path')
    
    if not recorded_path:
        log.error(f"[{run_id}] No recorded test path")
        return {
            **state,
            'status': 'failed',
            'error_message': 'No recorded test',
            'phase': 'analysis_failed'
        }
    
    log.info(f"[{run_id}] 🔍 Analyzing recorded test...")
    
    try:
        # Read recorded code
        recorded_code = Path(recorded_path).read_text()
        
        # Simple analysis - count actions
        actions = []
        for line in recorded_code.split('\n'):
            line = line.strip()
            if 'page.goto' in line:
                actions.append({'type': 'navigation', 'line': line})
            elif 'page.click' in line:
                actions.append({'type': 'click', 'line': line})
            elif 'page.fill' in line:
                actions.append({'type': 'input', 'line': line})
            elif 'page.select_option' in line:
                actions.append({'type': 'select', 'line': line})
        
        analysis = {
            'actions_count': len(actions),
            'actions': actions,
            'has_navigation': any(a['type'] == 'navigation' for a in actions),
            'has_interactions': len(actions) > 1
        }
        
        log.info(f"[{run_id}] ✅ Analysis complete: {len(actions)} actions found")
        
        return {
            **state,
            'recording_analysis': analysis,
            'phase': 'analysis_completed'
        }
        
    except Exception as e:
        log.error(f"[{run_id}] Analysis failed: {e}", exc_info=True)
        return {
            **state,
            'recording_analysis': {'actions_count': 0, 'actions': []},
            'phase': 'analysis_completed'  # Continue anyway
        }

async def generate_from_recording_node(state: TestRunState) -> TestRunState:
    """Convert recorded test to proper test file"""
    run_id = state['run_id']
    recorded_path = state.get('recorded_test_path')
    
    if not recorded_path:
        return {
            **state,
            'status': 'failed',
            'error_message': 'No recorded test',
            'phase': 'code_generation_failed'
        }
    
    log.info(f"[{run_id}] 💻 Converting recorded test to proper format...")
    
    try:
        # Create tests directory
        gen_dir = Path(f"/tmp/uidai_runs/{run_id}/generator")
        tests_dir = gen_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        # Read and enhance recorded code
        recorded_file = Path(recorded_path)
        recorded_code = recorded_file.read_text()
        enhanced_code = _enhance_recorded_code(recorded_code, state['url'])
        
        # Save to tests directory
        test_file = tests_dir / "test_recorded.py"
        test_file.write_text(enhanced_code, encoding='utf-8')
        
        log.info(f"[{run_id}] ✅ Test file created: {test_file}")
        
        return {
            **state,
            'generated_tests': [{
                'scenario_name': 'Recorded Test',
                'filename': 'test_recorded.py',
                'path': str(test_file),
                'lines': len(enhanced_code.split('\n'))
            }],
            'tests_directory': str(gen_dir),
            'tests_count': 1,
            'phase': 'code_generated'
        }
        
    except Exception as e:
        log.error(f"[{run_id}] Code generation failed: {e}", exc_info=True)
        return {
            **state,
            'status': 'failed',
            'error_message': f"Code generation failed: {str(e)}",
            'phase': 'code_generation_failed'
        }



def _enhance_recorded_code(code: str, url: str) -> str:
    """Enhance recorded code with better selectors"""
    
    enhanced = """import pytest
import os
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_recorded_workflow():
    \"\"\"Recorded user workflow\"\"\"
    artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    headed_mode = os.getenv("HEADED", "0") == "1"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not headed_mode,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            print("🎬 Running recorded workflow")
            
"""
    
    # Process each line and fix ambiguous selectors
    for line in code.split('\n'):
        line = line.strip()
        if line.startswith('page.') or line.startswith('await page.'):
            if not line.startswith('await'):
                line = 'await ' + line
            
            # ← FIX: Add .first for get_by_role to handle multiple matches
            if 'get_by_role' in line and '.first' not in line:
                line = line.replace('.click()', '.first.click()')
                line = line.replace('.fill(', '.first.fill(')
            
            enhanced += f"            {line}\n"
    
    enhanced += """
            print("✅ Recorded workflow completed")
            await page.screenshot(path=os.path.join(artifacts_dir, "recorded_success.png"))
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await page.screenshot(path=os.path.join(artifacts_dir, "recorded_error.png"))
            raise
        finally:
            await context.close()
            await browser.close()
"""
    
    return enhanced

# Import execution and healing nodes from ai_workflow
from .ai_workflow import execution_node, healing_node, should_heal