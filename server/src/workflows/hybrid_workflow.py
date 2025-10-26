# server/src/workflows/hybrid_workflow.py - COMPLETE IMPLEMENTATION

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from ..state import TestRunState
from ..agents.discovery_agent import discovery_node
from ..agents.scenario_converter import scenario_converter_node
from ..agents.code_generator import code_generator_node

log = logging.getLogger(__name__)

def create_hybrid_workflow():
    """
    Create LangGraph workflow for Hybrid mode
    Combines user recording with AI-generated tests
    """
    workflow = StateGraph(TestRunState)
    
    # Add nodes
    workflow.add_node("discovery", discovery_node)
    workflow.add_node("record", recording_node)
    workflow.add_node("analyze", analyze_recording_node)
    workflow.add_node("story", story_from_recording_node)
    workflow.add_node("scenarios", scenario_converter_node)
    workflow.add_node("code", code_generator_with_recording_node)
    workflow.add_node("execute", execution_node)
    workflow.add_node("heal", healing_node)
    
    # Set entry point
    workflow.set_entry_point("discovery")
    
    # Add edges
    workflow.add_edge("discovery", "record")
    workflow.add_edge("record", "analyze")
    workflow.add_edge("analyze", "story")
    workflow.add_edge("story", "scenarios")
    workflow.add_edge("scenarios", "code")
    workflow.add_edge("code", "execute")
    
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

# Import nodes from record_workflow
from .record_workflow import recording_node, analyze_recording_node, _enhance_recorded_code

async def story_from_recording_node(state: TestRunState) -> TestRunState:
    """Generate story from recorded test + user input"""
    from ..tools.ollama_client_enhanced import ollama_client
    
    run_id = state['run_id']
    user_story = state.get('user_story')
    recording_analysis = state.get('recording_analysis', {})
    recorded_path = state.get('recorded_test_path')
    
    log.info(f"[{run_id}] 📝 Generating enhanced story from recording...")
    
    try:
        # Read recorded test
        recorded_code = ""
        if recorded_path:
            from pathlib import Path
            recorded_code = Path(recorded_path).read_text()
        
        # Build prompt
        prompt = f"""Analyze this recorded Playwright test and create an enhanced test story.

Recorded Test:
```python
{recorded_code[:2000]}
```

User Request: {user_story or "Generate additional test scenarios"}

Create a comprehensive test story that:
1. Describes what the recorded workflow does
2. Suggests edge cases to test
3. Identifies negative test scenarios
4. Recommends boundary condition tests

Write a clear test story (no code, just description):"""
        
        result = ollama_client.generate_with_fallback(
            task="story_generation",
            prompt=prompt
        )
        
        if isinstance(result, dict) and result.get('ok'):
            enhanced_story = result['response'].strip()
            model_used = result['model']
        elif isinstance(result, str):
            enhanced_story = result.strip()
            model_used = "unknown"
        else:
            enhanced_story = f"Enhanced test scenarios for recorded workflow. {user_story or ''}"
            model_used = "fallback"
        
        log.info(f"[{run_id}] ✅ Story generated using {model_used}")
        
        return {
            **state,
            'final_story': enhanced_story,
            'story_source': 'recording_enhanced',
            'story_model': model_used,
            'phase': 'story_ready'
        }
        
    except Exception as e:
        log.error(f"[{run_id}] Story generation failed: {e}", exc_info=True)
        
        fallback = f"Test the recorded workflow and add edge cases. {user_story or ''}"
        
        return {
            **state,
            'final_story': fallback,
            'story_source': 'fallback',
            'phase': 'story_ready'
        }

async def code_generator_with_recording_node(state: TestRunState) -> TestRunState:
    """Generate AI tests + include recorded test"""
    run_id = state['run_id']
    recorded_path = state.get('recorded_test_path')
    
    # First, generate AI tests
    ai_result = await code_generator_node(state)
    
    if ai_result.get('status') == 'failed':
        return ai_result
    
    # Then add recorded test
    try:
        from pathlib import Path
        import shutil
        
        tests_dir = Path(ai_result['tests_directory']) / "tests"
        
        if recorded_path and Path(recorded_path).exists():
            # Copy and enhance recorded test
            recorded_code = Path(recorded_path).read_text()
            enhanced_code = _enhance_recorded_code(recorded_code, state['url'])
            
            recorded_test = tests_dir / "test_recorded_workflow.py"
            recorded_test.write_text(enhanced_code, encoding='utf-8')
            
            # Add to generated tests list
            generated_tests = list(ai_result.get('generated_tests', []))
            generated_tests.insert(0, {
                'scenario_name': 'Recorded Workflow',
                'filename': 'test_recorded_workflow.py',
                'path': str(recorded_test),
                'lines': len(enhanced_code.split('\n'))
            })
            
            log.info(f"[{run_id}] ✅ Added recorded test to suite")
            
            return {
                **ai_result,
                'generated_tests': generated_tests,
                'tests_count': len(generated_tests)
            }
    
    except Exception as e:
        log.warning(f"[{run_id}] Could not add recorded test: {e}")
    
    return ai_result

# Import other nodes
from .ai_workflow import execution_node, healing_node, should_heal