# server/src/agents/base_agent.py
"""
Base agent class with multi-model support
"""
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from ..config import config
from ..tools.ollama_client_enhanced import ollama_client

log = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, task_type: str):
        self.task_type = task_type
        self.models = config.MODEL_REGISTRY.get(task_type, [])
        
        if not self.models:
            log.warning(f"No models configured for task: {task_type}")
    
    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent logic
        
        Args:
            state: Current pipeline state
        
        Returns:
            Updated state dict
        """
        pass
    
    async def call_llm(
        self, 
        prompt: str, 
        format: str = "",
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Call LLM with automatic fallback
        
        Returns:
            Dict with 'ok', 'response', 'model', 'attempts'
        """
        result = ollama_client.generate_with_fallback(
            task=self.task_type,
            prompt=prompt,
            format=format,
            options={
                "temperature": temperature,
                "num_predict": 2000
            }
        )
        
        return result
    
    def log_progress(self, run_id: str, message: str):
        """Log progress to database"""
        from ..database.connection import get_db
        from ..database.models import RunLog
        
        try:
            with get_db() as db:
                log_entry = RunLog(run_id=run_id, message=message)
                db.add(log_entry)
                db.commit()
        except Exception as e:
            log.error(f"Failed to log progress: {e}")
        
        log.info(f"[{run_id}] {message}")