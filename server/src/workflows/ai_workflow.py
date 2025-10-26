# server/src/workflows/ai_workflow.py - REMOVE UNUSED IMPORT

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from pathlib import Path
import re

from ..state import TestRunState
from ..agents.discovery_agent import discovery_node
from ..agents.story_generator import story_generator_node
from ..agents.scenario_converter import scenario_converter_node
from ..agents.code_generator import code_generator_node
from ..tools.ollama_client_enhanced import ollama_client  # ← ADD THIS

log = logging.getLogger(__name__)

def create_ai_workflow():
    """Create LangGraph workflow for AI mode"""
    workflow = StateGraph(TestRunState)
    
    # Add async nodes
    workflow.add_node("discovery", discovery_node)
    workflow.add_node("story", story_generator_node)
    workflow.add_node("scenarios", scenario_converter_node)
    workflow.add_node("code", code_generator_node)
    workflow.add_node("execute", execution_node)
    workflow.add_node("heal", healing_node)
    
    # Set entry point
    workflow.set_entry_point("discovery")
    
    # Add edges
    workflow.add_edge("discovery", "story")
    workflow.add_edge("story", "scenarios")
    workflow.add_edge("scenarios", "code")
    workflow.add_edge("code", "execute")
    
    # Conditional edge for healing
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

async def execution_node(state: TestRunState) -> TestRunState:
    """Execute tests - ASYNC"""
    from ..tools.runner import run_playwright_tests
    
    run_id = state['run_id']
    tests_dir = state.get('tests_directory')
    execution_mode = state.get('execution_mode', 'headless')
    
    if not tests_dir:
        log.error(f"[{run_id}] No tests directory found")
        return {
            **state,
            'status': 'failed',
            'error_message': 'No tests directory',
            'phase': 'execution_failed',
            'tests_total': 0,
            'tests_passed': 0,
            'tests_failed': 0
        }
    
    # Get parent directory (remove /tests from end if present)
    gen_dir = str(Path(tests_dir).parent) if tests_dir.endswith('/tests') else tests_dir
    
    log.info(f"[{run_id}] 🧪 Executing tests ({execution_mode} mode)...")
    log.info(f"[{run_id}] Gen dir: {gen_dir}")
    
    try:
        # Run in thread pool since runner is sync
        import asyncio
        from functools import partial
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                run_playwright_tests,
                run_id=run_id,
                gen_dir=gen_dir,
                headed=(execution_mode == 'headed'),
                timeout_seconds=300
            )
        )
        
        # Parse summary
        if not result or not result.get('ok'):
            log.error(f"[{run_id}] Test execution failed: {result.get('error') if result else 'No result'}")
            return {
                **state,
                'execution_result': result or {},
                'tests_total': 0,
                'tests_passed': 0,
                'tests_failed': 0,
                'phase': 'execution_failed'
            }
        
        summary = result.get('summary', {})
        passed = int(summary.get('passed', 0))
        failed = int(summary.get('failed', 0))
        total = int(summary.get('total', 0))
        
        log.info(f"[{run_id}] ✅ Execution: {passed}/{total} passed")
        
        # Update state with results
        updated_state = {
            **state,
            'execution_result': result,
            'tests_passed': passed,
            'tests_failed': failed,
            'tests_total': total,
            'phase': 'execution_completed'
        }
        
        # Update database immediately after execution
        from ..database.state_updater import state_updater
        state_updater.update_from_state(run_id, updated_state)
        
        return updated_state
        
    except Exception as e:
        log.error(f"[{run_id}] Execution failed: {e}", exc_info=True)
        return {
            **state,
            'status': 'failed',
            'error_message': f"Execution failed: {str(e)}",
            'phase': 'execution_failed',
            'tests_total': 0,
            'tests_passed': 0,
            'tests_failed': 0
        }

# server/src/workflows/ai_workflow.py - FIX HEALING PATH

async def healing_node(state: TestRunState) -> TestRunState:
    """Self-healing node - ASYNC"""
    run_id = state['run_id']
    healing_attempts = state.get('healing_attempts', 0)
    tests_dir = state.get('tests_directory')
    execution_result = state.get('execution_result', {})
    
    log.info(f"[{run_id}] 🔧 Healing attempt {healing_attempts + 1}...")
    
    if not tests_dir:
        log.error(f"[{run_id}] No tests directory for healing")
        return {
            **state,
            'healing_attempts': healing_attempts + 1,
            'is_healed': False
        }
    
    try:
        failed_tests = [
            test for test in execution_result.get('tests', [])
            if test.get('outcome') == 'failed'
        ]
        
        if not failed_tests:
            log.info(f"[{run_id}] No failed tests to heal")
            return {
                **state,
                'healing_attempts': healing_attempts + 1,
                'is_healed': True
            }
        
        log.info(f"[{run_id}] Analyzing {len(failed_tests)} failed tests...")
        
        healing_suggestions = []
        
        for test in failed_tests[:3]:
            test_file = test.get('nodeid', '').split('::')[0]
            error = test.get('call', {}).get('longrepr', '') if test.get('call') else ''
            
            # ← FIX: Build correct path
            # tests_dir is /tmp/.../generator
            # test_file is relative: test_something.py
            test_path = Path(tests_dir) / "tests" / test_file  # ✅ Correct path
            
            if not test_path.exists():
                log.warning(f"[{run_id}] Test file not found: {test_path}")
                continue
            
            # Read test code
            test_code = test_path.read_text()
            
            # Generate fix
            fix_prompt = f"""Fix this failed Playwright test.

Test file: {test_file}
Error: {error[:500]}

Original code:
```python
{test_code[:2000]}
```

Common fixes:
- If "strict mode violation" (multiple elements): Add .first or use more specific selector
- If "Timeout": Increase timeout, add waits
- If element not found: Use better selectors, add waits

Provide ONLY the complete fixed Python code:"""
            
            result = ollama_client.generate_with_fallback(
                task="code_generation",
                prompt=fix_prompt
            )
            
            if isinstance(result, dict) and result.get('ok'):
                fixed_code = _clean_code(result.get('response', ''))
            elif isinstance(result, str):
                fixed_code = _clean_code(result)
            else:
                continue
            
            if not fixed_code:
                continue
            
            # Write fixed code
            test_path.write_text(fixed_code, encoding='utf-8')
            
            healing_suggestions.append({
                'test': test_file,
                'fixed': True,
                'model': result.get('model') if isinstance(result, dict) else 'unknown'
            })
            
            log.info(f"[{run_id}]   ✅ Fixed: {test_file}")
        
        healed = len(healing_suggestions) > 0
        
        healing_result = {
            'ok': healed,
            'suggestions': healing_suggestions,
            'healed_tests': len(healing_suggestions)
        }
        
        updated_state = {
            **state,
            'healing_attempts': healing_attempts + 1,
            'is_healed': healed,
            'healing_result': healing_result
        }
        
        from ..database.state_updater import state_updater
        state_updater.update_from_state(run_id, updated_state)
        
        return updated_state
        
    except Exception as e:
        log.error(f"[{run_id}] Healing failed: {e}", exc_info=True)
        return {
            **state,
            'healing_attempts': healing_attempts + 1,
            'is_healed': False,
            'healing_result': {
                'ok': False,
                'error': str(e)
            }
        }
def _clean_code(code: str) -> str:
    """Clean generated code"""
    if '```python' in code:
        code = code.split('```python')[1].split('```')[0]
    elif '```' in code:
        parts = code.split('```')
        if len(parts) >= 3:
            code = parts[1]
    
    return code.strip()

def should_heal(state: TestRunState) -> str:
    """Decide whether to heal or complete"""
    auto_heal = state.get('auto_heal', True)
    max_attempts = state.get('max_heal_attempts', 3)
    healing_attempts = state.get('healing_attempts', 0)
    tests_failed = state.get('tests_failed', 0)
    
    # Don't heal if:
    # - Auto-heal is disabled
    # - No failed tests
    # - Max attempts reached
    if not auto_heal or tests_failed == 0 or healing_attempts >= max_attempts:
        return "complete"
    
    return "heal"