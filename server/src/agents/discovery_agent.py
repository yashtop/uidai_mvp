# server/src/agents/discovery_agent.py - ASYNC VERSION

import logging
from typing import Dict, Any

from ..state import TestRunState
from ..tools.discovery_enhanced import discover_with_selectors_async

log = logging.getLogger(__name__)

# server/src/agents/discovery_agent.py - ADD STATE UPDATES

async def discovery_node(state: TestRunState) -> TestRunState:
    """Discovery Node with database updates"""
    run_id = state['run_id']
    url = state['url']
    preset = state.get('preset', 'balanced')
    
    log.info(f"[{run_id}] 🔍 Discovery phase starting...")
    
    preset_config = _get_preset_config(preset)
    
    try:
        discovery_result = await discover_with_selectors_async(
            run_id=run_id,
            url=url,
            level=preset_config['level'],
            max_pages=preset_config['max_pages']
        )
        
        pages_count = len(discovery_result.get('pages', []))
        elements_count = sum(
            len(p.get('selectors', [])) 
            for p in discovery_result.get('pages', [])
        )
        
        log.info(f"[{run_id}] ✅ Discovery: {pages_count} pages, {elements_count} elements")
        
        # Update state
        updated_state = {
            **state,
            'discovery_data': discovery_result,
            'pages_count': pages_count,
            'elements_count': elements_count,
            'phase': 'discovery_completed'
        }
        
        # ← ADD: Persist to database
        from ..database.state_updater import state_updater
        state_updater.update_from_state(run_id, updated_state)
        
        return updated_state
        
    except Exception as e:
        log.error(f"[{run_id}] Discovery failed: {e}", exc_info=True)
        
        failed_state = {
            **state,
            'status': 'failed',
            'error_message': f"Discovery failed: {str(e)}",
            'phase': 'discovery_failed',
            'discovery_data': {},
            'pages_count': 0,
            'elements_count': 0
        }
        
        # ← ADD: Persist failure
        from ..database.state_updater import state_updater
        state_updater.update_from_state(run_id, failed_state)
        
        return failed_state

def _get_preset_config(preset: str) -> Dict[str, int]:
    """Get discovery configuration for preset"""
    configs = {
        "quick": {"level": 1, "max_pages": 5, "timeout": 180},
        "balanced": {"level": 1, "max_pages": 15, "timeout": 900},
        "deep": {"level": 2, "max_pages": 30, "timeout": 600}
    }
    return configs.get(preset, configs["balanced"])