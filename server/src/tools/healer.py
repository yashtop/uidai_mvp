# server/src/tools/healer.py
import os
import json
import logging
import requests
import ast
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
    
    models = models or ["qwen2.5-coder:14b"]
    
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
    
    # Get the original test file content
    test_file_content = ""
    test_file_path = None
    if generated_files:
        try:
            test_file_path = Path(generated_files[0])
            if test_file_path.exists():
                test_file_content = test_file_path.read_text()
        except Exception as e:
            log.warning(f"Could not read test file: {e}")
    
    prompt = f"""You are a Python test repair expert. Fix this broken test.

CURRENT BROKEN TEST CODE:
```python
{test_file_content[:2000] if test_file_content else "# No code available"}
```

ERROR:
{failures_text}

TASK: Generate COMPLETE, VALID, RUNNABLE Python code that fixes the test.

REQUIREMENTS:
1. Return ONLY valid Python code (no markdown, no explanations)
2. Include ALL necessary imports
3. Keep pytest decorators (@pytest.mark.asyncio)
4. Fix the specific error (timeout, selector, syntax)
5. Code MUST be syntactically valid Python
6. Use proper string quotes and escaping
7. Common fixes:
   - Increase timeout to 60000
   - Use wait_until="domcontentloaded" instead of "networkidle"
   - Add try-except for resilience
   - Add wait times with await page.wait_for_timeout(1000)

Return ONLY the complete fixed Python code, nothing else:"""
    
    for model in models:
        try:
            log.info(f"🔧 Requesting healing from {model}...")
            
            response = requests.post(
                f"{OLLAMA_HTTP}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 2000}
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Save raw response
                (out_dir / f"{model.replace(':', '_')}.raw.txt").write_text(response_text)
                
                # Extract code from markdown if present
                code = extract_code_from_response(response_text)
                
                if code and validate_python_syntax(code):
                    log.info(f"✅ Got valid Python code from {model}")
                    return {
                        "ok": True,
                        "suggestions": [{
                            "issue": "Test failure",
                            "fix": code,
                            "priority": "high",
                            "confidence": 0.85
                        }],
                        "fromModel": model
                    }
                else:
                    log.warning(f"Invalid Python code from {model}, trying basic fix")
                    
        except Exception as e:
            log.error(f"Healing model {model} failed: {e}")
            continue
    
    # Fallback: Apply basic automated fixes
    if test_file_content:
        log.info("Applying basic automated fixes...")
        basic_fix = apply_basic_fixes(test_file_content, failures_text)
        if basic_fix and validate_python_syntax(basic_fix):
            return {
                "ok": True,
                "suggestions": [{
                    "issue": "Timeout or navigation issue",
                    "fix": basic_fix,
                    "priority": "medium",
                    "confidence": 0.7
                }],
                "fromModel": "basic_fixer"
            }
    
    return {"ok": False, "message": "All healing attempts failed"}

def extract_code_from_response(response: str) -> str:
    """Extract Python code from LLM response, handling markdown code blocks"""
    # Try to find code between ```python and ```
    if "```python" in response:
        start = response.find("```python") + 9
        end = response.find("```", start)
        if end > start:
            code = response[start:end].strip()
            return code
    
    # Try to find code between ``` and ```
    if "```" in response:
        parts = response.split("```")
        if len(parts) >= 3:
            code = parts[1].strip()
            # Remove language identifier if present
            if code.startswith("python\n"):
                code = code[7:]
            return code
    
    # If no code blocks, assume entire response is code
    return response.strip()

def validate_python_syntax(code: str) -> bool:
    """Validate that code is syntactically valid Python"""
    try:
        ast.parse(code)
        log.info("✓ Code is syntactically valid Python")
        return True
    except SyntaxError as e:
        log.error(f"✗ Syntax error in generated code: {e}")
        return False
    except Exception as e:
        log.error(f"✗ Error parsing code: {e}")
        return False

def apply_basic_fixes(test_code: str, failures_text: str) -> str:
    """
    Apply common automated fixes to test code
    """
    fixed_code = test_code
    
    # Fix 1: Increase all timeouts
    if "Timeout" in failures_text or "timeout" in failures_text:
        fixed_code = fixed_code.replace('timeout=30000', 'timeout=60000')
        fixed_code = fixed_code.replace('timeout=30_000', 'timeout=60_000')
        
        # Add timeout to page.goto if missing
        if 'await page.goto(' in fixed_code:
            lines = fixed_code.split('\n')
            new_lines = []
            for line in lines:
                if 'await page.goto(' in line and 'timeout=' not in line:
                    # Add timeout before closing paren
                    if line.rstrip().endswith(')'):
                        line = line.rstrip()[:-1] + ', timeout=60000)'
                    elif line.rstrip().endswith(','):
                        line = line.rstrip() + ' timeout=60000'
                new_lines.append(line)
            fixed_code = '\n'.join(new_lines)
    
    # Fix 2: Change networkidle to domcontentloaded (more reliable)
    if "networkidle" in fixed_code:
        fixed_code = fixed_code.replace(
            'wait_until="networkidle"', 
            'wait_until="domcontentloaded"'
        )
        fixed_code = fixed_code.replace(
            "wait_until='networkidle'", 
            "wait_until='domcontentloaded'"
        )
    
    # Fix 3: Add wait after navigation
    if 'await page.goto(' in fixed_code and 'await page.wait_for_timeout' not in fixed_code:
        lines = fixed_code.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if 'await page.goto(' in line:
                # Add wait after goto
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + 'await page.wait_for_timeout(2000)  # Wait for page to stabilize')
        fixed_code = '\n'.join(new_lines)
    
    return fixed_code

def apply_patch(patch: dict, generated_tests_dir: str):
    """Apply healing patch to test file"""
    file_rel = patch.get("file")
    if not file_rel:
        # Find the test file in the directory
        test_dir = Path(generated_tests_dir)
        test_files = list(test_dir.glob("test_*.py"))
        if not test_files:
            raise ValueError("No test files found in directory")
        file_rel = test_files[0].name
    
    file_path = Path(generated_tests_dir) / file_rel
    
    # Backup original
    if file_path.exists():
        backup = file_path.with_suffix(file_path.suffix + ".bak")
        try:
            if backup.exists():
                backup.unlink()
            file_path.rename(backup)
            log.info(f"Backed up {file_path} to {backup}")
        except Exception as e:
            log.warning(f"Could not backup file: {e}")
    
    content = patch.get("content") or patch.get("fix") or patch.get("patch")
    if content is None:
        raise ValueError("patch missing 'content', 'fix', or 'patch' field")
    
    # CRITICAL: Validate Python syntax before applying
    if not validate_python_syntax(content):
        log.error("Patch contains invalid Python code, rejecting")
        # Restore from backup
        if backup.exists():
            backup.rename(file_path)
        raise ValueError("Patch content has syntax errors")
    
    # Validate it looks like a test
    if "def test_" not in content and "async def test_" not in content:
        log.error("Patch doesn't contain a test function")
        if backup.exists():
            backup.rename(file_path)
        raise ValueError("Patch doesn't contain valid test function")
    
    # Write the fixed content
    file_path.write_text(content, encoding="utf-8")
    log.info(f"Applied patch to {file_path} ({len(content)} chars)")
    
    return {"ok": True, "file": str(file_path)}