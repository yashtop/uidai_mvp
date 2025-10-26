# server/src/agents/code_generator.py - FIX ERROR HANDLING

import logging
from pathlib import Path
from typing import Dict, Any, List
import re
import shutil

from ..state import TestRunState
from ..tools.ollama_client_enhanced import ollama_client

log = logging.getLogger(__name__)

async def code_generator_node(state: TestRunState) -> TestRunState:
    """Code Generator Node - ASYNC"""
    run_id = state['run_id']
    scenarios = state.get('scenarios', [])
    url = state['url']
    
    if not scenarios:
        log.error(f"[{run_id}] No scenarios available for code generation")
        return {
            **state,
            'status': 'failed',
            'error_message': 'No scenarios available',
            'phase': 'code_generation_failed'
        }
    
    log.info(f"[{run_id}] 💻 Generating code for {len(scenarios)} scenarios...")
    
    # Create tests directory
    gen_dir = Path(f"/tmp/uidai_runs/{run_id}/generator")
    tests_dir = gen_dir / "tests"
    
    # Clean old tests if they exist
    if tests_dir.exists():
        log.info(f"[{run_id}] Cleaning old tests directory...")
        shutil.rmtree(tests_dir)
    
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    generated_tests = []
    
    for i, scenario in enumerate(scenarios):
        try:
            log.info(f"[{run_id}]   → Test {i+1}/{len(scenarios)}: {scenario.get('name', 'Unnamed')}")
            
            # Build prompt
            prompt = _build_code_prompt(scenario, url)
            
            # Generate code using LLM
            try:
                result = ollama_client.generate_with_fallback(
                    task="code_generation",
                    prompt=prompt
                )
                
                # ← FIX: Handle both dict and string responses
                if isinstance(result, dict):
                    if result.get('ok'):
                        code = _clean_code(result.get('response', ''))
                        code = _ensure_headless(code)
                        if not code:
                            raise ValueError("Empty code from LLM")
                    else:
                        raise ValueError(result.get('error', 'Unknown error'))
                elif isinstance(result, str):
                    # If it returned a string directly, use it
                    code = _clean_code(result)
                    if not code:
                        raise ValueError("Empty code from LLM")
                else:
                    raise ValueError(f"Unexpected result type: {type(result)}")
                
            except Exception as e:
                log.warning(f"[{run_id}] LLM failed for test {i+1}: {e}")
                log.warning(f"[{run_id}] Using fallback code")
                code = _generate_fallback_code(scenario, url)
            
            # Ensure headless mode
            code = _ensure_headless(code)
            
            # Save to file
            
            filename = _create_filename(scenario.get('name', f'test_{i}'))
            is_valid, error_msg = _validate_code(code, filename)
            if not is_valid:
                log.warning(f"[{run_id}] Generated code invalid: {error_msg}")
                log.warning(f"[{run_id}] Using fallback instead")
                code = _generate_fallback_code(scenario, url)
            filepath = tests_dir / filename
            filepath.write_text(code, encoding='utf-8')
            
            generated_tests.append({
                'scenario_name': scenario.get('name', f'Test {i+1}'),
                'filename': filename,
                'path': str(filepath),
                'lines': len(code.split('\n'))
            })
            
            log.info(f"[{run_id}]     ✓ Generated: {filename}")
            
        except Exception as e:
            log.error(f"[{run_id}] Failed to generate test for '{scenario.get('name', 'Unknown')}': {e}", exc_info=True)
            
            # Try fallback one more time
            try:
                log.info(f"[{run_id}]     → Trying fallback for test {i+1}")
                code = _generate_fallback_code(scenario, url)
                code = _ensure_headless(code)
                
                filename = _create_filename(scenario.get('name', f'test_{i}'))
                filepath = tests_dir / filename
                filepath.write_text(code, encoding='utf-8')
                
                generated_tests.append({
                    'scenario_name': scenario.get('name', f'Test {i+1}'),
                    'filename': filename,
                    'path': str(filepath),
                    'lines': len(code.split('\n'))
                })
                
                log.info(f"[{run_id}]     ✓ Fallback succeeded: {filename}")
            except Exception as fallback_error:
                log.error(f"[{run_id}]     ✗ Fallback also failed: {fallback_error}")
                continue
    
    if not generated_tests:
        log.error(f"[{run_id}] No tests generated successfully")
        return {
            **state,
            'status': 'failed',
            'error_message': 'No tests generated',
            'phase': 'code_generation_failed'
        }
    
    log.info(f"[{run_id}] ✅ Generated {len(generated_tests)} test files")
    
    return {
        **state,
        'generated_tests': generated_tests,
        'tests_directory': str(gen_dir),  # Parent dir
        'tests_count': len(generated_tests),
        'phase': 'code_generated'
    }

def _build_code_prompt(scenario: Dict, url: str) -> str:
    """Build prompt for code generation"""
    name = scenario.get('name', 'Test')
    steps = scenario.get('steps', [])
    validations = scenario.get('validations', [])
    
    # Extract validation descriptions
    validation_text = []
    for v in validations:
        if isinstance(v, dict):
            validation_text.append(v.get('description', ''))
        else:
            validation_text.append(str(v))
    
    return f"""Generate a Playwright Python test for this scenario.

Scenario: {name}
URL: {url}
Steps: {', '.join(steps) if steps else 'Navigate to URL and verify page loads'}
Validations: {', '.join(validation_text) if validation_text else 'Verify page loads successfully'}

Requirements:
- Use pytest with @pytest.mark.asyncio decorator
- Use async/await with async_playwright
- CRITICAL: Read HEADED env var, default to headless
- Launch: headless=not (os.getenv("HEADED", "0") == "1")
- Use realistic user agent
- Add 5-10 second wait after page load for Cloudflare
- Use networkidle and 60s timeout
- Save screenshots to os.getenv("ARTIFACTS_DIR")
- Handle exceptions with try/except/finally

Return ONLY the complete Python test code with no explanations:"""

def _clean_code(code: str) -> str:
    """Clean generated code"""
    if not code:
        return ""
    
    code = str(code).strip()
    
    # Extract from markdown code blocks
    if '```python' in code:
        parts = code.split('```python')
        if len(parts) > 1:
            code = parts[1].split('```')[0]
    elif '```' in code:
        parts = code.split('```')
        if len(parts) >= 3:
            code = parts[1]
        elif len(parts) == 2:
            code = parts[1]
    
    return code.strip()



def _generate_fallback_code(scenario: Dict, url: str) -> str:
    """Generate simple fallback test"""
    safe_name = re.sub(r'[^a-z0-9_]', '_', scenario.get('name', 'test').lower())
    
    return f'''import pytest
import os
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_{safe_name}():
    """
    {scenario.get('name', 'Test')}
    """
    # Get configuration from environment
    artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    # Check if headed mode requested (default: headless)
    headed_mode = os.getenv("HEADED", "0") == "1"
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=not headed_mode,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={{'width': 1920, 'height': 1080}},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        # Anti-detection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => undefined
            }});
        """)
        
        try:
            print(f"🚀 Test: {scenario.get('name', 'Test')} (headless={{not headed_mode}})")
            
            # Navigate
            await page.goto("{url}", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            
            title = await page.title()
            print(f"📄 Title: {{title}}")
            
            # Check Cloudflare
            if "Just a moment" in title:
                await page.wait_for_timeout(10000)
                title = await page.title()
            
            # Assertions
            assert len(title) > 0, "Page should have title"
            assert "Just a moment" not in title, "Cloudflare blocking"
            
            content = await page.content()
            assert len(content) > 1000, "Page should have content"
            
            print("✅ Test passed")
            
            # Screenshot
            await page.screenshot(path=os.path.join(artifacts_dir, "{safe_name}_success.png"))
            
        except Exception as e:
            print(f"❌ Error: {{e}}")
            await page.screenshot(path=os.path.join(artifacts_dir, "{safe_name}_error.png"))
            raise
            
        finally:
            await context.close()
            await browser.close()
'''

def _create_filename(name: str) -> str:
    """Create safe filename"""
    safe = re.sub(r'[^a-z0-9_]', '_', name.lower())[:50]
    return f"test_{safe}.py"
# server/src/agents/code_generator.py - ADD _ensure_imports FUNCTION

def _ensure_imports(code: str) -> str:
    """Ensure all required imports are present"""
    
    required_imports = {
        'pytest': 'import pytest',
        'os': 'import os',
        'async_playwright': 'from playwright.async_api import async_playwright'
    }
    
    # Check which imports are missing
    missing_imports = []
    
    if 'import pytest' not in code and 'pytest' not in code.split('\n')[0]:
        missing_imports.append('import pytest')
    
    if 'import os' not in code:
        missing_imports.append('import os')
    
    if 'async_playwright' not in code:
        missing_imports.append('from playwright.async_api import async_playwright')
    
    # Add missing imports at the top
    if missing_imports:
        imports_block = '\n'.join(missing_imports) + '\n\n'
        
        # Find first line that's not a comment or blank
        lines = code.split('\n')
        insert_index = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
                insert_index = i
                break
        
        # Insert imports at the beginning
        if insert_index == 0:
            code = imports_block + code
        else:
            code = '\n'.join(lines[:insert_index]) + '\n' + imports_block + '\n'.join(lines[insert_index:])
    
    return code

def _ensure_headless(code: str) -> str:
    """Ensure code uses headless mode from environment"""
    
    # First, ensure all imports are present
    code = _ensure_imports(code)
    
    # Replace any hardcoded headless=False
    code = code.replace('headless=False', 'headless=not (os.getenv("HEADED", "0") == "1")')
    
    # If launch() doesn't have headless parameter, add it
    if 'launch(' in code and 'headless=' not in code:
        code = code.replace(
            'launch(',
            'launch(\n            headless=not (os.getenv("HEADED", "0") == "1"),'
        )
    
    return code

def _validate_code(code: str, filename: str) -> tuple[bool, str]:
    """
    Validate generated code
    Returns: (is_valid, error_message)
    """
    
    # Check for required imports
    required = ['import pytest', 'async_playwright', '@pytest.mark.asyncio']
    missing = []
    
    for req in required:
        if req not in code:
            missing.append(req)
    
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    
    # Check for async def test_
    if 'async def test_' not in code:
        return False, "No async test function found"
    
    # Check for browser launch
    if 'launch(' not in code:
        return False, "No browser launch found"
    
    return True, ""