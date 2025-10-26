# server/src/pipeline_langgraph.py - UPDATE

import logging
from datetime import datetime
from typing import Dict, Any

from .state import TestRunState
from .workflows.ai_workflow import create_ai_workflow
from .workflows.record_workflow import create_record_workflow
from .workflows.hybrid_workflow import create_hybrid_workflow
from .database.state_updater import state_updater  # ← ADD THIS

log = logging.getLogger(__name__)

class LangGraphPipeline:
    """LangGraph-based test pipeline"""
    
    def __init__(self):
        self.ai_workflow = create_ai_workflow()
        self.record_workflow = create_record_workflow()
        self.hybrid_workflow = create_hybrid_workflow()
    
    async def run(self, run_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run pipeline with appropriate workflow"""
        
        # Build initial state
        initial_state: TestRunState = {
            'run_id': run_id,
            'url': config['url'],
            'test_creation_mode': config.get('testCreationMode', 'ai'),
            'execution_mode': config.get('mode', 'headless'),
            'preset': config.get('preset', 'balanced'),
            'user_story': config.get('story'),
            'max_heal_attempts': config.get('maxHealAttempts', 3),
            'auto_heal': config.get('autoHeal', True),
            'status': 'running',
            'phase': 'starting',
            'started_at': datetime.utcnow(),
            'healing_attempts': 0,
            'is_healed': False
        }
        
        # Update database with initial state
        state_updater.update_from_state(run_id, initial_state)
        
        # Select workflow
        mode = initial_state['test_creation_mode']
        
        if mode == 'ai':
            workflow = self.ai_workflow
        elif mode == 'record':
            workflow = self.record_workflow
        elif mode == 'hybrid':
            workflow = self.hybrid_workflow
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        log.info(f"[{run_id}] Starting {mode} mode pipeline")
        
        try:
            # Run workflow with async invocation
            final_state = await workflow.ainvoke(initial_state)
            
            # Mark as completed
            final_state['status'] = 'completed'
            final_state['completed_at'] = datetime.utcnow()
            
            # ← ADD: Update database with final state
            state_updater.update_from_state(run_id, final_state)
            
            log.info(f"[{run_id}] Pipeline completed successfully")
            
            return final_state
            
        except Exception as e:
            log.error(f"[{run_id}] Pipeline failed: {e}", exc_info=True)
            
            # Return failed state
            failed_state = {
                **initial_state,
                'status': 'failed',
                'error_message': str(e),
                'completed_at': datetime.utcnow()
            }
            
            # ← ADD: Update database with failed state
            state_updater.update_from_state(run_id, failed_state)
            
            return failed_state

# Global pipeline instance
langgraph_pipeline = LangGraphPipeline()