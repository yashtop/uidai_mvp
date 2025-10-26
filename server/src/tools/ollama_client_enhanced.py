# server/src/tools/ollama_client_enhanced.py
"""
Enhanced Ollama client with retry logic, fallback, and error handling
Optimized for Apple M1 Pro
"""
import os
import json
import logging
import requests
import time
from typing import Optional, Dict, Any, List
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from ..config import config

log = logging.getLogger(__name__)

# Custom exceptions
class OllamaError(Exception):
    """Base Ollama error"""
    pass

class OllamaConnectionError(OllamaError):
    """Ollama server not reachable"""
    pass

class OllamaModelNotFoundError(OllamaError):
    """Model not loaded"""
    pass

class OllamaTimeoutError(OllamaError):
    """Request timeout"""
    pass

class OllamaServerError(OllamaError):
    """Server error (500)"""
    pass


class OllamaClient:
    """Enhanced Ollama client with retry and fallback"""
    
    def __init__(self):
        self.base_url = config.OLLAMA_HTTP
        self.timeout = config.OLLAMA_TIMEOUT
        self.models_cache = None
        self.last_cache_time = 0
        self.cache_ttl = 60  # Cache for 60 seconds
    
    def _check_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(
                f"{self.base_url}/api/version",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self, force_refresh: bool = False) -> List[str]:
        """Get list of available models (cached)"""
        now = time.time()
        
        if not force_refresh and self.models_cache and (now - self.last_cache_time) < self.cache_ttl:
            return self.models_cache
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                self.models_cache = [m["name"] for m in models]
                self.last_cache_time = now
                return self.models_cache
            else:
                log.warning(f"Failed to get models: {response.status_code}")
                return []
        except Exception as e:
            log.error(f"Error getting models: {e}")
            return []
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model is loaded"""
        available = self.get_available_models()
        return model_name in available
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OllamaConnectionError, OllamaTimeoutError, OllamaServerError)),
        before_sleep=before_sleep_log(log, logging.WARNING)
    )
    def _make_request(self, model: str, prompt: str, format: str = "", options: Dict = None) -> Dict[str, Any]:
        """Make request with retry logic"""
        
        # Check if model is available
        if not self.is_model_available(model):
            raise OllamaModelNotFoundError(f"Model '{model}' not found. Available: {self.get_available_models()}")
        
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options or {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "num_predict": 2000,
                "repeat_penalty": 1.1
            }
        }
        
        if format:
            body["format"] = format
        
        try:
            log.info(f"Calling Ollama {model} (timeout={self.timeout}s)...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=body,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                log.info(f"✅ Ollama responded in {duration:.1f}s ({len(response_text)} chars)")
                
                return {
                    "ok": True,
                    "response": response_text,
                    "model": model,
                    "duration": duration
                }
            
            elif response.status_code == 404:
                raise OllamaModelNotFoundError(f"Model not found: {model}")
            
            elif response.status_code == 500:
                raise OllamaServerError(f"Ollama server error: {response.text}")
            
            else:
                raise OllamaError(f"Unexpected status {response.status_code}: {response.text}")
        
        except requests.exceptions.Timeout:
            raise OllamaTimeoutError(f"Request timeout after {self.timeout}s")
        
        except requests.exceptions.ConnectionError as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}")
    
    def generate_with_fallback(
        self,
        task: str,
        prompt: str,
        format: str = "",
        options: Dict = None
    ) -> Dict[str, Any]:
        """
        Generate with automatic fallback to secondary models
        
        Args:
            task: Task type (e.g., "story_generation", "code_generation")
            prompt: The prompt to send
            format: Response format (e.g., "json")
            options: Ollama options
        
        Returns:
            Dict with 'ok', 'response', 'model', 'attempts'
        """
        models = config.MODEL_REGISTRY.get(task, [])
        
        if not models:
            return {
                "ok": False,
                "error": f"No models configured for task: {task}"
            }
        
        errors = []
        
        for attempt, model in enumerate(models):
            try:
                log.info(f"Attempt {attempt + 1}/{len(models)}: Using {model} for {task}")
                
                result = self._make_request(model, prompt, format, options)
                
                return {
                    **result,
                    "attempts": attempt + 1,
                    "task": task
                }
            
            except OllamaModelNotFoundError as e:
                log.warning(f"Model {model} not available, trying next...")
                errors.append(f"{model}: not found")
                continue
            
            except (OllamaTimeoutError, OllamaServerError) as e:
                log.warning(f"Model {model} failed: {e}, trying next...")
                errors.append(f"{model}: {str(e)}")
                continue
            
            except OllamaConnectionError as e:
                # Connection error - don't try other models
                return {
                    "ok": False,
                    "error": f"Ollama not reachable: {e}",
                    "task": task
                }
            
            except Exception as e:
                log.error(f"Unexpected error with {model}: {e}")
                errors.append(f"{model}: {str(e)}")
                continue
        
        # All models failed
        return {
            "ok": False,
            "error": "All models failed",
            "task": task,
            "attempts": len(models),
            "errors": errors
        }

# Global client instance
ollama_client = OllamaClient()

# Convenience functions
def generate_with_model(model: str, prompt: str, format: str = "", **kwargs) -> Optional[str]:
    """
    Simple generate function (backward compatible)
    """
    result = ollama_client._make_request(model, prompt, format)
    return result.get("response") if result.get("ok") else None

def generate_with_fallback(task: str, prompt: str, format: str = "") -> Dict[str, Any]:
    """
    Generate with automatic fallback
    """
    return ollama_client.generate_with_fallback(task, prompt, format)