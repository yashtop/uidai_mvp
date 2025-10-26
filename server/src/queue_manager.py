# server/src/queue_manager.py - ASYNC VERSION

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from asyncio import Queue, Semaphore

from .config import config
from .database.connection import get_db
from .database.models import Run

log = logging.getLogger(__name__)

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
            run = db.query(Run).filter(Run.id == run_id).first()
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
                        run = db.query(Run).filter(Run.id == run_id).first()
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
            # Import pipeline
            from .pipeline_langgraph import langgraph_pipeline
            
            # Run async pipeline directly (no thread pool needed)
            await langgraph_pipeline.run(run_id, run_config)
            
        except Exception as e:
            log.error(f"Run {run_id} failed: {e}", exc_info=True)
            
            # Update status in database
            with get_db() as db:
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    run.status = "failed"
                    run.error_message = str(e)
                    run.completed_at = datetime.utcnow()
                    db.commit()
        
        finally:
            self.active_runs.pop(run_id, None)
            log.info(f"Run {run_id} completed (active={len(self.active_runs)})")
    
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
            run = db.query(Run).filter(Run.id == run_id).first()
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