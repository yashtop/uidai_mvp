# server/src/agents/scenario_converter.py - FIXED

import logging
import json
from typing import Dict, Any, List

from ..state import TestRunState
from ..tools.ollama_client_enhanced import ollama_client

log = logging.getLogger(__name__)

def scenario_converter_node(state: TestRunState) -> TestRunState:
    """
    Scenario Converter Node - LangGraph compatible
    Converts story to structured scenarios
    """
    run_id = state['run_id']
    story = state.get('final_story')
    discovery_data = state.get('discovery_data', {})
    url = state['url']
    
    if not story:
        log.error(f"[{run_id}] No story available for scenario conversion")
        return {
            **state,
            'status': 'failed',
            'error_message': 'No story available',
            'phase': 'scenario_conversion_failed'
        }
    
    log.info(f"[{run_id}] ⚙️ Converting story to scenarios...")
    
    prompt = _build_scenario_prompt(story, discovery_data, url)
    
    try:
        result = ollama_client.generate_with_fallback(
            task="scenario_conversion",
            prompt=prompt,
            format="json"
        )
        
        if not result.get('ok'):
            raise Exception(result.get('error', 'Scenario conversion failed'))
        
        scenarios = _parse_scenarios(result['response'])
        
        if not scenarios:
            raise Exception("No valid scenarios parsed")
        
        log.info(f"[{run_id}] ✅ Generated {len(scenarios)} scenarios")
        
        return {
            **state,
            'scenarios': scenarios,
            'scenarios_count': len(scenarios),
            'scenario_model': result['model'],
            'phase': 'scenarios_ready'
        }
        
    except Exception as e:
        log.error(f"[{run_id}] Scenario conversion failed: {e}", exc_info=True)
        
        # Fallback scenarios
        fallback_scenarios = _create_fallback_scenarios(url, discovery_data)
        
        return {
            **state,
            'scenarios': fallback_scenarios,
            'scenarios_count': len(fallback_scenarios),
            'scenario_model': 'fallback',
            'phase': 'scenarios_ready'
        }

def _build_scenario_prompt(story: str, discovery_data: Dict, url: str) -> str:
    """Build prompt for scenario conversion"""
    return f"""Convert story to test scenarios.

Story: {story}
URL: {url}

Return JSON with scenarios array containing name, steps, and validations."""

def _parse_scenarios(response: str) -> List[Dict]:
    """Parse scenarios from JSON response"""
    try:
        response = response.strip()
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        
        data = json.loads(response)
        return data.get('scenarios', [])
    except Exception as e:
        log.error(f"Failed to parse scenarios: {e}")
        return []

def _create_fallback_scenarios(url: str, discovery_data: Dict) -> List[Dict]:
    """Fallback scenarios"""
    return [{
        "id": "fallback_1",
        "name": "Basic Page Load Test",
        "steps": [f"Navigate to {url}", "Verify page loads"],
        "validations": ["Page loads successfully"],
        "target_pages": [url]
    }]