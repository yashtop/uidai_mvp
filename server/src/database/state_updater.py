# server/src/database/state_updater.py - ADD LOGGING

import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from .models import Run
from .connection import get_db

log = logging.getLogger(__name__)

class StateUpdater:
    """Updates database from LangGraph state"""
    
    @staticmethod
    def update_from_state(run_id: str, state: Dict[str, Any]):
        """Update database run record from LangGraph state"""
        
        log.info(f"[{run_id}] Updating database from state (phase={state.get('phase')})")
        
        with get_db() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            if not run:
                log.warning(f"[{run_id}] Run not found in database")
                return
            
            # Basic fields
            if 'status' in state:
                run.status = state['status']
                log.debug(f"[{run_id}] Status: {state['status']}")
            
            if 'phase' in state:
                run.phase = state['phase']
                log.debug(f"[{run_id}] Phase: {state['phase']}")
            
            if 'error_message' in state:
                run.error_message = state['error_message']
            
            # Test creation mode
            if 'test_creation_mode' in state:
                run.test_creation_mode = state['test_creation_mode']
            
            if 'execution_mode' in state:
                run.mode = state['execution_mode']
            
            # Story phase
            if 'user_story' in state:
                run.user_story = state['user_story']
            
            if 'final_story' in state:
                run.final_story = state['final_story']
            
            if 'story_source' in state:
                run.story_source = state['story_source']
            
            if 'story_model' in state:
                run.story_model = state['story_model']
            
            # Discovery phase
            if 'discovery_data' in state:
                run.discovery_result = state['discovery_data']
            
            if 'pages_count' in state:
                run.pages_discovered = state['pages_count']
                log.debug(f"[{run_id}] Pages discovered: {state['pages_count']}")
            
            if 'elements_count' in state:
                run.elements_discovered = state['elements_count']
                log.debug(f"[{run_id}] Elements discovered: {state['elements_count']}")
            
            # Scenario phase
            if 'scenarios' in state:
                run.generation_result = {
                    'scenarios': state['scenarios'],
                    'tests': state.get('generated_tests', [])
                }
            
            if 'scenarios_count' in state:
                run.scenarios_count = state['scenarios_count']
                log.debug(f"[{run_id}] Scenarios: {state['scenarios_count']}")
            
            if 'scenario_model' in state:
                run.scenario_model = state['scenario_model']
            
            # Code generation phase
            if 'generated_tests' in state:
                run.tests_count = len(state['generated_tests'])
                log.debug(f"[{run_id}] Tests generated: {len(state['generated_tests'])}")
            
            if 'code_model' in state:
                run.code_model = state['code_model']
            
            # Execution phase
            if 'execution_result' in state:
                run.execution_result = state['execution_result']
            
            if 'tests_passed' in state:
                run.tests_passed = state['tests_passed']
                log.debug(f"[{run_id}] Tests passed: {state['tests_passed']}")
            
            if 'tests_failed' in state:
                run.tests_failed = state['tests_failed']
                log.debug(f"[{run_id}] Tests failed: {state['tests_failed']}")
            
            if 'tests_total' in state:
                run.tests_total = state['tests_total']
                log.debug(f"[{run_id}] Tests total: {state['tests_total']}")
            
            # Timestamps
            if 'completed_at' in state:
                run.completed_at = state['completed_at']
                
                # Calculate total duration
                if run.created_at:
                    duration = (state['completed_at'] - run.created_at).total_seconds()
                    run.total_duration_seconds = int(duration)
                    log.info(f"[{run_id}] Total duration: {int(duration)}s")
            
            # Commit changes
            try:
                db.commit()
                log.info(f"[{run_id}] ✅ Database updated successfully")
            except Exception as e:
                log.error(f"[{run_id}] ❌ Failed to commit: {e}")
                db.rollback()
                raise
    # server/src/database/state_updater.py - ADD THIS METHOD

def get_run_state(self, run_id: str) -> dict:
    """Get current state of a run"""
    try:
        with self.db.get_session() as session:
            run = session.query(TestRun).filter_by(run_id=run_id).first()
            if not run:
                return None
            
            return {
                'run_id': run.run_id,
                'status': run.status,
                'phase': run.phase,
                'pages_discovered': run.pages_discovered,
                'scenarios_count': len(run.scenarios) if run.scenarios else 0,
                'tests_count': run.tests_total,
                'tests_passed': run.tests_passed,
                'tests_total': run.tests_total,
                'tests_failed': run.tests_failed,
            }
    except Exception as e:
        log.error(f"Error getting run state: {e}")
        return None

# Global instance
state_updater = StateUpdater()