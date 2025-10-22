# server/src/tools/healer.py
import os
import json
import logging
import requests
from typing import List, Dict, Any
from pathlib import Path

log = logging.getLogger(__name__)
OLLAMA_HTTP = os.getenv("OLLAMA_HTTP", "http://localhost:11434")

def get_heal_suggestions(
    run_id: str, 
    failingTestInfo: dict, 
    generated_files: list, 
    models: list = None, 
    out_dir: str = "/tmp/uidai_runs"
) -> Dict[str, Any]:
    """
    Generate healing suggestions using Ollama
    """
    out_dir = Path(out_dir) / run_id / "healer"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    models = models or ["mistral:latest"]
    
    # Build prompt from failures
    failing_tests = failingTestInfo.get("report", {}).get("tests", [])
    if not failing_tests:
        return {"ok": False, "message": "No test info available"}
    
    failures_text = "\n\n".join([
        f"Test: {test.get('nodeid', 'unknown')}\n"
        f"Outcome: {test.get('outcome', 'unknown')}\n"
        f"Error: {test.get('call', {}).get('longrepr', 'No error')[:500]}"
        for test in failing_tests[:3] if test.get('outcome') == 'failed'
    ])
    
    if not failures_text:
        return {"ok": False, "message": "No failures found"}
    
    prompt = f"""Analyze these test failures and provide fixes:

{failures_text}

Provide 3 specific suggestions as JSON:
{{
  "suggestions": [
    {{"issue": "description", "fix": "solution", "priority": "high", "confidence": 0.8}},
    ...
  ]
}}
"""
    
    for model in models:
        try:
            log.info(f"🔧 Requesting healing from {model}...")
            
            response = requests.post(
                f"{OLLAMA_HTTP}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.3, "num_predict": 500}
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Save raw response
                (out_dir / f"{model.replace(':', '_')}.raw.txt").write_text(response_text)
                
                # Parse suggestions
                try:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        parsed = json.loads(response_text[json_start:json_end])
                        suggestions = parsed.get("suggestions", [])
                        
                        if suggestions:
                            log.info(f"✅ Got {len(suggestions)} suggestions from {model}")
                            return {
                                "ok": True,
                                "suggestions": suggestions,
                                "fromModel": model
                            }
                except:
                    pass
                
                # Fallback: create generic suggestion
                return {
                    "ok": True,
                    "suggestions": [{
                        "issue": "Test failures detected",
                        "fix": response_text[:300],
                        "priority": "medium",
                        "confidence": 0.5
                    }],
                    "fromModel": model
                }
                    
        except Exception as e:
            log.error(f"Healing model {model} failed: {e}")
            continue
    
    return {"ok": False, "message": "All models failed"}

def apply_patch(patch: dict, generated_tests_dir: str):
    """Apply healing patch to test file"""
    file_rel = patch.get("file")
    if not file_rel:
        raise ValueError("patch missing 'file'")

    file_path = Path(generated_tests_dir) / file_rel
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Backup original
    if file_path.exists():
        backup = file_path.with_suffix(file_path.suffix + ".bak")
        file_path.rename(backup)
    
    content = patch.get("content") or patch.get("patch")
    if content is None:
        raise ValueError("patch missing 'content'")
    
    file_path.write_text(content, encoding="utf-8")
    return {"ok": True, "file": str(file_path)}