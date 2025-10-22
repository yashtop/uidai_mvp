# server/src/tools/ollama_client.py
import os
import json
import logging
import requests

log = logging.getLogger(__name__)
OLLAMA_HTTP = os.getenv("OLLAMA_HTTP", "http://localhost:11434")

def build_optimized_prompt(url: str, pages: list = None, scenario_text: str = None) -> str:
    """
    Build production-grade prompt with few-shot learning for Playwright test generation
    """
    
    # Extract discovered page information
    page_context = ""
    if pages:
        page_context = "\n\nDISCOVERED PAGE INFORMATION:"
        for i, page in enumerate(pages[:2]):  # Limit to 2 pages
            page_context += f"\n- URL: {page.get('url', 'N/A')}"
            page_context += f"\n  Title: {page.get('title', 'N/A')}"
            
            # Get key selectors
            selectors = page.get('selectors', [])[:8]
            if selectors:
                selector_list = [s.get('selector', '') for s in selectors if s.get('selector')]
                page_context += f"\n  Key elements: {', '.join(selector_list[:5])}"
    
    test_requirements = scenario_text if scenario_text else "Test the homepage and verify it loads correctly with key elements present."
    
    # OPTIMIZED PROMPT with few-shot examples
    prompt = f"""You are an expert Python Playwright test engineer. Generate a COMPLETE, PRODUCTION-READY test.

TARGET URL: {url}

TEST REQUIREMENTS:
{test_requirements}
{page_context}

═══════════════════════════════════════════════════════════════
LEARN FROM THESE EXAMPLES (FOLLOW THIS EXACT PATTERN):
═══════════════════════════════════════════════════════════════

EXAMPLE 1 - Basic Homepage Test (CORRECT ✅):

import pytest
from playwright.async_api import async_playwright
import os

@pytest.mark.asyncio
async def test_homepage():
    # Setup artifacts directory FIRST (before async context)
    artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()  # Note: snake_case
        
        try:
            # Navigate and test
            await page.goto("https://example.com", wait_until="networkidle", timeout=30000)
            
            # Assertions with descriptive messages
            title = await page.title()
            assert "Example" in title, f"Expected 'Example' in title, got: {{title}}"
            
            content = await page.content()
            assert len(content) > 1000, f"Page content too short: {{len(content)}} bytes"
            
            # Count elements
            links = await page.query_selector_all("a")
            print(f"✓ Found {{len(links)}} links")
            
            # Success screenshot
            await page.screenshot(path=os.path.join(artifacts_dir, "success.png"))
            print("✓ Test passed")
            
        except Exception as e:
            # Failure screenshot
            await page.screenshot(path=os.path.join(artifacts_dir, "failure.png"))
            print(f"✗ Test failed: {{e}}")
            raise
        finally:
            await browser.close()


EXAMPLE 2 - Test with Element Interaction (CORRECT ✅):

import pytest
from playwright.async_api import async_playwright
import os

@pytest.mark.asyncio
async def test_navigation():
    artifacts_dir = os.getenv("ARTIFACTS_DIR", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto("https://example.com", wait_until="networkidle", timeout=30000)
            
            # Check for navigation menu
            nav = await page.query_selector("nav")
            assert nav is not None, "Navigation menu should exist"
            
            # Get all nav links
            nav_links = await page.query_selector_all("nav a")
            assert len(nav_links) > 3, f"Expected multiple nav links, found {{len(nav_links)}}"
            
            print(f"✓ Navigation verified with {{len(nav_links)}} links")
            
            await page.screenshot(path=os.path.join(artifacts_dir, "success.png"))
            
        except Exception as e:
            await page.screenshot(path=os.path.join(artifacts_dir, "failure.png"))
            print(f"✗ Navigation test failed: {{e}}")
            raise
        finally:
            await browser.close()


═══════════════════════════════════════════════════════════════
CRITICAL PYTHON PLAYWRIGHT API RULES (MUST FOLLOW):
═══════════════════════════════════════════════════════════════

✅ CORRECT Python API (snake_case):
   - browser.new_page()
   - browser.new_context()
   - page.query_selector()
   - page.query_selector_all()
   - page.wait_for_selector()
   - page.wait_for_timeout()
   - page.text_content()
   - await page.screenshot(path="file.png")
   - os.path.join(artifacts_dir, "file.png")

❌ WRONG JavaScript API (camelCase) - DO NOT USE:
   - browser.newPage()  ❌
   - page.querySelector()  ❌
   - page.waitForSelector()  ❌
   - await page.screenshot({{"path": "file.png"}})  ❌

MANDATORY CODE STRUCTURE:
1. Define artifacts_dir BEFORE async with statement
2. Use os.getenv("ARTIFACTS_DIR", "artifacts")
3. Create directory with os.makedirs(artifacts_dir, exist_ok=True)
4. Always use try/except/finally block
5. Take screenshots in both success and failure cases
6. Close browser in finally block
7. Use descriptive assert messages with f-strings
8. Add print statements for test progress

═══════════════════════════════════════════════════════════════
NOW GENERATE TEST FOR: {url}
Requirements: {test_requirements}
═══════════════════════════════════════════════════════════════

CRITICAL RESPONSE RULES:
- Return ONLY Python code
- NO markdown code blocks (no ```python```)
- NO explanations before or after code
- Start directly with: import pytest
- Follow the EXACT pattern shown in examples above

Generate the complete test code now:"""
    
    return prompt

def generate_with_model(model: str, payload: dict = None, format: str = "", timeout: int = 120, **kwargs):
    """
    Call Ollama API to generate Playwright test code with optimized prompt
    """
    # Merge payload and kwargs
    input_payload = payload if payload is not None else kwargs
    
    # Build specialized Playwright prompt
    if isinstance(input_payload, dict):
        url = input_payload.get('url', '')
        pages = input_payload.get('pages', [])
        scenario_text = input_payload.get('scenario_text', '')
        instruction = input_payload.get('instruction', '')
        
        if instruction:
            # Custom instruction provided (for non-Playwright use cases)
            prompt = instruction
            if url:
                prompt += f"\n\nURL: {url}"
        else:
            # Build optimized Playwright prompt with examples
            prompt = build_optimized_prompt(url, pages, scenario_text)
    else:
        prompt = str(input_payload)
    
    if not prompt:
        log.error("Empty prompt generated")
        return None
    
    try:
        url_endpoint = f"{OLLAMA_HTTP}/api/generate"
        
        # Optimized parameters for code generation
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,      # Low temperature for consistent, deterministic code
                "top_p": 0.95,           # Nucleus sampling
                "top_k": 40,             # Top-k sampling
                "num_predict": 2500,     # Allow longer responses
                "repeat_penalty": 1.1,   # Discourage repetition
                "stop": ["```\n\n", "---", "###", "EXAMPLE"]  # Stop tokens
            }
        }
        
        log.info(f"🔄 Calling Ollama {model}...")
        log.debug(f"Prompt length: {len(prompt)} chars")
        
        response = requests.post(url_endpoint, json=body, timeout=timeout)
        
        if response.status_code != 200:
            log.error(f"Ollama returned status {response.status_code}")
            log.error(f"Response: {response.text[:500]}")
            return None
        
        data = response.json()
        response_text = data.get("response", "")
        
        if not response_text:
            log.error("Ollama returned empty response")
            return None
        
        log.info(f"✓ Got {len(response_text)} chars from {model}")
        
        # Clean up response
        code = response_text.strip()
        
        # Remove markdown code blocks if present
        if "```python" in code:
            parts = code.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
        elif "```" in code:
            parts = code.split("```")
            if len(parts) >= 3:
                code = parts[1]
        
        # Remove any explanatory text before first import
        lines = code.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')):
                code = '\n'.join(lines[i:])
                break
        
        # If format is json, try to parse
        if format == "json":
            try:
                json_start = code.find('{')
                json_end = code.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    return json.loads(code[json_start:json_end])
            except json.JSONDecodeError:
                pass
        
        return code.strip()
        
    except requests.exceptions.Timeout:
        log.error(f"Ollama timeout after {timeout}s")
        return None
    except requests.exceptions.ConnectionError as e:
        log.error(f"Cannot connect to Ollama at {OLLAMA_HTTP}: {e}")
        return None
    except Exception as e:
        log.exception(f"Ollama error: {e}")
        return None