# server/src/queue_manager.py - FIXED CIRCULAR IMPORT

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from asyncio import Queue, Semaphore

from .config import config
from .database.connection import get_db
from .database.models import TestRun
from .pipeline_langgraph import langgraph_pipeline

log = logging.getLogger(__name__)

# ❌ REMOVE THIS LINE (causes circular import)
# from .main import broadcast_progress

class RunQueueManager:
    """Manages concurrent test run execution - ASYNC"""
    
    def __init__(self, max_concurrent: int = None):
        self.max_concurrent = max_concurrent or config.MAX_CONCURRENT_RUNS
        self.semaphore = Semaphore(self.max_concurrent)
        self.queue: Queue = Queue()
        self.active_runs: Dict[str, dict] = {}
        self.is_processing = False
        
        log.info(f"Queue Manager initialized (max_concurrent={self.max_concurrent})")
    
    async def enqueue_run(self, run_id: str, run_config: dict) -> dict:
        """Add run to queue"""
        await self.queue.put((run_id, run_config))
        
        # Update run status
        with get_db() as db:
            run = db.query(TestRun).filter_by(run_id=run_id).first()
            if run:
                run.status = "queued"
                run.phase = "queued"
                db.commit()
        
        queue_size = self.queue.qsize()
        position = queue_size
        estimated_wait_seconds = (position - 1) * 120 if position > 1 else 0
        
        log.info(f"Run {run_id} queued (position={position}, wait={estimated_wait_seconds}s)")
        
        # Start processing if not already running
        if not self.is_processing:
            asyncio.create_task(self.process_queue())
        
        return {
            "queued": True,
            "position": position,
            "queue_size": queue_size,
            "estimated_wait_seconds": estimated_wait_seconds,
            "active_runs": len(self.active_runs)
        }
    
    async def process_queue(self):
        """Process queued runs"""
        if self.is_processing:
            return
        
        self.is_processing = True
        log.info("Queue processor started")
        
        try:
            while True:
                async with self.semaphore:
                    if self.queue.empty():
                        break
                    
                    run_id, run_config = await self.queue.get()
                    
                    log.info(f"Starting run {run_id} (active={len(self.active_runs)}, queued={self.queue.qsize()})")
                    
                    # Update status
                    with get_db() as db:
                        run = db.query(TestRun).filter_by(run_id=run_id).first()
                        if run:
                            run.status = "running"
                            run.phase = "starting"
                            db.commit()
                    
                    # Track active run
                    self.active_runs[run_id] = {
                        "started_at": datetime.utcnow(),
                        "config": run_config
                    }
                    
                    # Execute run in background
                    asyncio.create_task(self._execute_run(run_id, run_config))
                    
                    await asyncio.sleep(1)
        
        finally:
            self.is_processing = False
            log.info("Queue processor stopped")
            
            if not self.queue.empty():
                asyncio.create_task(self.process_queue())
    
    async def _execute_run(self, run_id: str, run_config: dict):
        """Execute a single run - FULLY ASYNC"""
        try:
            # Update progress: starting
            await self._update_progress(run_id, {
                "phase": "starting",
                "status": "running",
                "details": "Initializing browser...",
                "progress": 5
            })
            
            # Run async pipeline
            result = await langgraph_pipeline.run(run_id, run_config)
            
            # Pipeline handles its own progress updates via state_updater
            # So we just need to send final WebSocket update
            
            if result.get('status') == 'completed':
                await self._update_progress(run_id, {
                    "phase": "completed",
                    "status": "completed",
                    "details": "All tests completed!",
                    "progress": 100
                })
            elif result.get('status') == 'failed':
                await self._update_progress(run_id, {
                    "phase": "failed",
                    "status": "failed",
                    "details": result.get('error_message', 'Test run failed'),
                    "progress": 0
                })
            
        except Exception as e:
            log.error(f"Run {run_id} failed: {e}", exc_info=True)
            
            # Update status in database
            with get_db() as db:
                run = db.query(TestRun).filter_by(run_id=run_id).first()
                if run:
                    run.status = "failed"
                    run.error_message = str(e)
                    run.completed_at = datetime.utcnow()
                    db.commit()
            
            # Broadcast failure
            await self._update_progress(run_id, {
                "phase": "failed",
                "status": "failed",
                "details": str(e),
                "progress": 0
            })
        
        finally:
            self.active_runs.pop(run_id, None)
            log.info(f"Run {run_id} completed (active={len(self.active_runs)})")
    
    async def _update_progress(self, run_id: str, progress_data: dict):
        """
        Update progress in database and broadcast to WebSocket
        """
        # Update database
        with get_db() as session:
            run = session.query(TestRun).filter_by(run_id=run_id).first()
            if run:
                run.phase = progress_data.get("phase", run.phase)
                run.status = progress_data.get("status", run.status)
                run.details = progress_data.get("details", run.details)
                run.progress = progress_data.get("progress", run.progress)
                session.commit()
        
        # ✅ FIXED: Import locally to avoid circular import
        try:
            # Import here instead of at module level
            import importlib
            main_module = importlib.import_module('main')
            broadcast_progress = getattr(main_module, 'broadcast_progress', None)
            
            if broadcast_progress:
                await broadcast_progress(run_id, progress_data)
            else:
                log.warning("broadcast_progress function not found in main module")
        except Exception as e:
            log.warning(f"Could not broadcast progress: {e}")
        
        log.info(f"📊 Progress update for {run_id}: {progress_data}")
    
    def get_status(self) -> dict:
        """Get current queue status"""
        return {
            "max_concurrent": self.max_concurrent,
            "active_runs": len(self.active_runs),
            "queued_runs": self.queue.qsize(),
            "is_processing": self.is_processing,
            "active_run_ids": list(self.active_runs.keys())
        }
    
    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a queued or running run"""
        with get_db() as db:
            run = db.query(TestRun).filter_by(run_id=run_id).first()
            if run and run.status in ["queued", "running"]:
                run.status = "cancelled"
                run.phase = "cancelled"
                run.completed_at = datetime.utcnow()
                db.commit()
                
                log.info(f"Run {run_id} cancelled")
                return True
        
        return False

# Global queue manager
queue_manager = RunQueueManager()