# server/src/database/state_updater.py - FIXED VERSION

import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from .models import TestRun  # ✅ Changed from Run to TestRun
from .connection import get_db

log = logging.getLogger(__name__)

class StateUpdater:
    """Updates database from LangGraph state"""
    
    @staticmethod
    def update_from_state(run_id: str, state: Dict[str, Any]):
        """Update database run record from LangGraph state"""
        
        log.info(f"[{run_id}] Updating database from state (phase={state.get('phase')})")
        
        with get_db() as db:
            # ✅ FIXED: Query by run_id (UUID string) not id (integer)
            run = db.query(TestRun).filter_by(run_id=run_id).first()
            
            if not run:
                log.warning(f"[{run_id}] Run not found in database")
                # Debug: show what's actually in the database
                all_runs = db.query(TestRun).all()
                log.warning(f"Total runs in DB: {len(all_runs)}")
                if all_runs:
                    log.warning(f"Sample run IDs: {[r.run_id[:8] for r in all_runs[:3]]}")
                return
            
            # Update fields
            if 'status' in state:
                run.status = state['status']
            
            if 'phase' in state:
                run.phase = state['phase']
            
            if 'details' in state:
                run.details = state['details']
            
            if 'progress' in state:
                run.progress = state['progress']
            
            if 'error_message' in state:
                run.error_message = state['error_message']
            
            # Discovery
            if 'discovery_data' in state:
                run.discovery_data = state['discovery_data']
            
            if 'pages_discovered' in state:
                run.pages_discovered = state['pages_discovered']
            
            if 'elements_found' in state:
                run.elements_found = state['elements_found']
            
            # Tests
            if 'tests_passed' in state:
                run.tests_passed = state['tests_passed']
            
            if 'tests_failed' in state:
                run.tests_failed = state['tests_failed']
            
            if 'tests_total' in state:
                run.tests_total = state['tests_total']
            
            # Commit
            try:
                db.commit()
                log.info(f"[{run_id}] ✅ Database updated successfully")
            except Exception as e:
                log.error(f"[{run_id}] ❌ Failed to commit: {e}")
                db.rollback()
                raise
    
    @staticmethod
    def get_run_state(run_id: str) -> dict:
        """Get current state of a run"""
        try:
            with get_db() as session:
                run = session.query(TestRun).filter_by(run_id=run_id).first()
                if not run:
                    return None
                
                return {
                    'run_id': run.run_id,
                    'status': run.status,
                    'phase': run.phase,
                    'progress': run.progress,
                    'details': run.details,
                }
        except Exception as e:
            log.error(f"Error getting run state: {e}")
            return None

# Global instance
state_updater = StateUpdater()