# server/src/tools/progress_tracker.py
"""
Real-time progress tracking using WebSocket
"""
import json
import logging
from typing import Dict, Any, Set
from datetime import datetime

log = logging.getLogger(__name__)

class ProgressTracker:
    """Manages real-time progress updates for test runs"""
    
    def __init__(self):
        self.connections: Dict[str, Set] = {}  # run_id -> set of websockets
        self.progress_data: Dict[str, Dict] = {}  # run_id -> progress info
    
    def register_connection(self, run_id: str, websocket):
        """Register a WebSocket connection for a run"""
        if run_id not in self.connections:
            self.connections[run_id] = set()
        self.connections[run_id].add(websocket)
        log.info(f"Client connected to run {run_id}")
    
    def unregister_connection(self, run_id: str, websocket):
        """Unregister a WebSocket connection"""
        if run_id in self.connections:
            self.connections[run_id].discard(websocket)
            if not self.connections[run_id]:
                del self.connections[run_id]
        log.info(f"Client disconnected from run {run_id}")
    
    async def broadcast_progress(self, run_id: str, progress: Dict[str, Any]):
        """Broadcast progress update to all connected clients"""
        if run_id not in self.connections:
            return
        
        # Store latest progress
        self.progress_data[run_id] = {
            **progress,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = json.dumps(self.progress_data[run_id])
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.connections[run_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                log.error(f"Error sending to websocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.connections[run_id].discard(ws)
    
    def get_progress(self, run_id: str) -> Dict[str, Any]:
        """Get current progress for a run"""
        return self.progress_data.get(run_id, {})
    
    def update_phase(self, run_id: str, phase: str, status: str = "running", 
                     details: str = "", progress_percent: int = 0):
        """Helper to update phase progress"""
        return {
            "phase": phase,
            "status": status,
            "details": details,
            "progress": progress_percent,
            "timestamp": datetime.utcnow().isoformat()
        }

# Global tracker instance
progress_tracker = ProgressTracker()