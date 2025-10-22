# server/src/tools/generator.py
"""
Test Generator for UIDAI MVP
Generates Playwright tests based on discovered pages and scenario templates from UI
"""

import json
import logging
import uuid
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from .ollama_client import generate_with_model
import os
log = logging.getLogger(__name__)

# UIDAI Scenario Templates (matching UI - RunCreator.jsx)
SCENARIO_TEMPLATES = {
    "uidai-homepage-navigation": {
        "id": "uidai-homepage-navigation",
        "name": "1. UIDAI Homepage & Main Navigation",
        "description": "Test UIDAI English homepage structure and primary navigation",
        "steps": [
            "Navigate to https://uidai.gov.in/en/",
            "Handle language selection page",
            "Verify UIDAI logo and main navigation",
            "Check My Aadhaar menu items",
            "Verify footer with helpline 1947",
            "Test accessibility features"
        ],
        "key_selectors": ["nav", "a[href*='my-aadhaar']", "footer", ".logo", "button"],
        "validations": [
            "Page title contains 'UIDAI'",
            "Helpline 1947 is displayed",
            "Email help@uidai.gov.in present"
        ]
    },
    "uidai-my-aadhaar-services": {
        "id": "uidai-my-aadhaar-services",
        "name": "2. My Aadhaar Services Discovery",
        "description": "Test My Aadhaar section and service pages",
        "steps": [
            "Navigate to My Aadhaar section",
            "Check Download Aadhaar service",
            "Check Update Aadhaar options",
            "Verify Aadhaar verification service",
            "Check forms and downloads"
        ],
        "key_selectors": ["a[href*='download']", "a[href*='update']", "form", ".service"],
        "validations": [
            "Download Aadhaar link exists",
            "Update options visible",
            "Forms page accessible"
        ]
    },
    "uidai-about-contact": {
        "id": "uidai-about-contact",
        "name": "3. About UIDAI & Contact Pages",
        "description": "Test About UIDAI and Contact/Support pages",
        "steps": [
            "Navigate to About UIDAI",
            "Verify vision and mission",
            "Check organization structure",
            "Navigate to Contact & Support",
            "Verify helpline and email",
            "Check grievance redressal"
        ],
        "key_selectors": ["a[href*='about']", "a[href*='contact']", ".faq", ".grievance"],
        "validations": [
            "About page loads",
            "Contact details present",
            "Grievance link exists"
        ]
    },
    "uidai-enrolment-centers": {
        "id": "uidai-enrolment-centers",
        "name": "4. Locate Enrolment Centers",
        "description": "Test enrolment center locator functionality",
        "steps": [
            "Navigate to Locate Enrolment Center",
            "Check state dropdown",
            "Check district dropdown",
            "Test search functionality",
            "Verify search results display"
        ],
        "key_selectors": ["select#state", "select#district", "input[type='search']", "button[type='submit']"],
        "validations": [
            "Locator page loads",
            "Dropdowns populated",
            "Search works"
        ]
    },
    "uidai-faqs-help": {
        "id": "uidai-faqs-help",
        "name": "5. FAQs & Help Resources",
        "description": "Test FAQ section and help resources",
        "steps": [
            "Navigate to FAQs section",
            "Check FAQ categories",
            "Test FAQ accordion",
            "Test search functionality",
            "Verify help resources"
        ],
        "key_selectors": [".faq-accordion", ".faq-category", "input[type='search']", ".help-resource"],
        "validations": [
            "FAQs page loads",
            "Categories displayed",
            "Accordion works"
        ]
    },
    "uidai-downloads-resources": {
        "id": "uidai-downloads-resources",
        "name": "6. Downloads & Resources Section",
        "description": "Test downloads, forms, and resource materials",
        "steps": [
            "Navigate to Downloads section",
            "Check enrolment forms",
            "Test form downloads",
            "Verify supporting documents",
            "Check PDF accessibility"
        ],
        "key_selectors": ["a[href$='.pdf']", ".download-section", ".form-category"],
        "validations": [
            "Downloads page accessible",
            "Forms listed",
            "PDF links work"
        ]
    }
}

def clean_generated_code(raw_code: str) -> str:
    """Aggressively clean generated code from various formats"""
    if not isinstance(raw_code, str):
        raw_code = str(raw_code)
    
    code = raw_code.strip()
    
    # Remove markdown code blocks
    if "```python" in code:
        parts = code.split("```python")
        if len(parts) > 1:
            code = parts[1].split("```")[0]
    elif "```" in code:
        parts = code.split("```")
        if len(parts) >= 3:
            code = parts[1]
    
    # Remove common AI prefixes
    prefixes = ["Here's the code:", "Here is", "```python", "python"]
    for prefix in prefixes:
        if code.lower().startswith(prefix.lower()):
            code = code[len(prefix):].strip()
    
    # Find first import or async def
    lines = code.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith(('import ', 'from ', 'async def', '@pytest')):
            code = '\n'.join(lines[i:])
            break
    
    return code.strip()

def validate_test_code(code: str) -> bool:
    """Validate generated code looks like valid Playwright test"""
    if not code or len(code) < 100:
        return False
    
    required = ['playwright', 'async def test_', 'await page.']
    for pattern in required:
        if pattern.lower() not in code.lower():
            log.warning(f"Missing: {pattern}")
            return False
    
    return True
def get_scenario_by_id(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Get scenario template by ID"""
    return SCENARIO_TEMPLATES.get(scenario_id)


def detect_uidai_scenario(pages: List[Dict]) -> str:
    """
    Detect most appropriate UIDAI scenario based on discovered pages
    For UIDAI, we analyze URLs and content
    """
    all_urls = " ".join([page.get("url", "") for page in pages]).lower()
    all_text = " ".join([
        " ".join([sel.get("text", "") for sel in page.get("selectors", [])])
        for page in pages
    ]).lower()
    
    # Detection based on URL patterns and content
    if "my-aadhaar" in all_urls or "download" in all_text or "update" in all_text:
        return "uidai-my-aadhaar-services"
    elif "about" in all_urls or "vision" in all_text or "mission" in all_text:
        return "uidai-about-contact"
    elif "locate" in all_urls or "enrolment" in all_text or "center" in all_text:
        return "uidai-enrolment-centers"
    elif "faq" in all_urls or "help" in all_text:
        return "uidai-faqs-help"
    elif "download" in all_urls or "form" in all_text or "pdf" in all_text:
        return "uidai-downloads-resources"
    else:
        # Default to homepage navigation
        return "uidai-homepage-navigation"


def create_scenario_from_discovery_ai(
    pages: List[Dict],
    url: str,
    model: str = "mistral:latest"
) -> Dict[str, Any]:
    """
    Use AI to create custom test scenario from discovered pages
    Fallback to template detection if AI fails
    """
    # Prepare discovery data for AI
    discovered_data = []
    for page in pages[:5]:  # Top 5 pages
        selectors_summary = []
        for sel in page.get("selectors", [])[:10]:  # Top 10 elements per page
            sel_info = {
                "selector": sel.get("selector", ""),
                "text": sel.get("text", "")[:50]  # First 50 chars
            }
            selectors_summary.append(sel_info)
        
        discovered_data.append({
            "url": page.get("url"),
            "title": page.get("title", ""),
            "elements": selectors_summary
        })
    
    prompt = {
        "instruction": """You are a test scenario creator for government websites. 
        
Based on the discovered pages from UIDAI.gov.in, create a comprehensive test scenario.

Return ONLY valid JSON in this exact format:
{
  "name": "Scenario Name",
  "description": "Brief description",
  "steps": ["Step 1", "Step 2", "Step 3"],
  "key_selectors": ["selector1", "selector2"],
  "validations": ["validation 1", "validation 2"]
}

Focus on:
- Government website compliance (accessibility, security)
- User journey for Aadhaar services
- Navigation and information architecture
- Form interactions if present
- Critical user flows

Keep it practical and achievable.""",
        "url": url,
        "discovered_pages": discovered_data
    }
    
    try:
        log.info(f"Generating scenario with AI model: {model}")
        result = generate_with_model(model, prompt, format="json", timeout=60)
        
        if isinstance(result, dict) and "name" in result:
            log.info(f"✓ AI generated scenario: {result.get('name')}")
            return {
                "ok": True,
                "scenario": result,
                "source": "ai_generated",
                "model": model
            }
        elif isinstance(result, str):
            # Try to parse string response
            parsed = json.loads(result)
            if "name" in parsed:
                return {
                    "ok": True,
                    "scenario": parsed,
                    "source": "ai_generated",
                    "model": model
                }
    except Exception as e:
        log.warning(f"AI scenario generation failed: {e}")
    
    # Fallback to template detection
    log.info("Falling back to template detection")
    template_key = detect_uidai_scenario(pages)
    return {
        "ok": True,
        "scenario": SCENARIO_TEMPLATES[template_key],
        "source": "template_fallback",
        "template": template_key
    }


def generate_playwright_test_code(
    scenario: Dict[str, Any],
    pages: List[Dict],
    url: str,
    model: str = "mistral:latest"
) -> str:
    """
    Generate Playwright test code using AI based on scenario and discovered elements
    """
    # Prepare context for AI
    elements_by_page = {}
    for page in pages[:3]:  # Top 3 pages
        page_url = page.get("url", "")
        elements_by_page[page_url] = [
            {
                "selector": s.get("selector", ""),
                "text": s.get("text", "")[:30]
            }
            for s in page.get("selectors", [])[:15]  # Top 15 elements
        ]
    
    prompt = {
        "instruction": """You are an expert Playwright test code generator for Python.

Generate complete, runnable Python test code following these requirements:

MUST HAVE:
1. Use async/await pattern with playwright.async_api
2. Use pytest framework with @pytest.mark.asyncio
3. Include proper timeouts (30 seconds minimum)
4. Use wait_for_selector for all interactions
5. Add meaningful assertions
6. Handle errors gracefully with try/except
7. Take screenshot on failure
8. Add descriptive comments
9. Use robust selectors (prefer data-testid, id, then CSS)
10. NO markdown formatting - return pure Python code only

CODE STRUCTURE:
```python
import pytest
from playwright.async_api import async_playwright
import asyncio

@pytest.mark.asyncio
async def test_scenario_name():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Test steps here
            await page.goto("URL", wait_until="networkidle", timeout=30000)
            # More steps...
            
        except Exception as e:
            await page.screenshot(path="artifacts/failure.png")
            raise
        finally:
            await browser.close()
```

Return ONLY the Python code. No explanations, no markdown blocks.""",
        "scenario": {
            "name": scenario.get("name", "Test"),
            "steps": scenario.get("steps", []),
            "key_selectors": scenario.get("key_selectors", []),
            "validations": scenario.get("validations", [])
        },
        "base_url": url,
        "discovered_elements": elements_by_page
    }
    
    try:
        log.info(f"Generating test code with {model}")
        code = generate_with_model(model, prompt, format="", timeout=90)
        
        if not isinstance(code, str):
            code = str(code)
        
        # Clean up markdown code blocks if present
        code = code.strip()
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
        
        code = clean_generated_code(code)
        
        # Basic validation
        if validate_test_code(code):
            log.info(f"✓ Generated {len(code)} bytes of test code")
            return code
        else:
            log.warning("Generated code seems invalid, using stub")
            return generate_stub_test_uidai(url, scenario.get("name", "Test"))
            
    except Exception as e:
        log.exception(f"Test generation failed: {e}")
        return generate_stub_test_uidai(url, scenario.get("name", "Test"))


def generate_stub_test_uidai(url: str, test_name: str = "UIDAI Basic Test") -> str:
    """
    Generate conservative stub test for UIDAI when AI generation fails
    """
    safe_name = re.sub(r'[^a-z0-9_]', '_', test_name.lower())
    
    return f'''import pytest
from playwright.async_api import async_playwright
import asyncio
import os

@pytest.mark.asyncio
async def test_{safe_name}():
    """
    {test_name}
    Conservative stub test for UIDAI portal
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=os.getenv("UIDAI_HEADED") != "1"
        )
        context = await browser.new_context(
            viewport={{"width": 1920, "height": 1080}},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # Create artifacts directory
        os.makedirs("artifacts", exist_ok=True)
        
        try:
            # Navigate to UIDAI homepage
            print(f"Navigating to {{"{url}"}}...")
            await page.goto("{url}", wait_until="networkidle", timeout=30000)
            
            # Basic page load verification
            title = await page.title()
            assert title, "Page should have a title"
            print(f"✓ Page loaded: {{title}}")
            
            # Check if UIDAI content is present
            content = await page.content()
            assert len(content) > 1000, "Page should have substantial content"
            assert "UIDAI" in content or "Aadhaar" in content, "Page should contain UIDAI/Aadhaar references"
            print(f"✓ Page content verified ({{len(content)}} bytes)")
            
            # Check for interactive elements (more lenient than nav-only)
            links = await page.query_selector_all("a")
            buttons = await page.query_selector_all("button")
            inputs = await page.query_selector_all("input")
            
            total_interactive = len(links) + len(buttons) + len(inputs)
            assert total_interactive > 10, f"Page should have interactive elements, found {{total_interactive}}"
            print(f"✓ Found {{len(links)}} links, {{len(buttons)}} buttons, {{len(inputs)}} inputs")
            
            # Take success screenshot
            await page.screenshot(path="artifacts/success_screenshot.png", full_page=True)
            print("✓ Test completed successfully")
            
        except AssertionError as e:
            print(f"✗ Assertion failed: {{e}}")
            await page.screenshot(path="artifacts/failure_assertion.png", full_page=True)
            raise
            
        except Exception as e:
            print(f"✗ Test failed: {{e}}")
            await page.screenshot(path="artifacts/failure_exception.png", full_page=True)
            raise
            
        finally:
            await browser.close()
'''
def generate_scenario_stub(url: str, scenario: Dict[str, Any]) -> str:
    """
    Generate a CUSTOMIZED stub test based on the specific scenario template.
    """
    test_name = scenario['name']
    description = scenario.get('description', 'Test scenario')
    steps = scenario.get('steps', [])
    validations = scenario.get('validations', [])
    key_selectors = scenario.get('key_selectors', [])
    
    safe_name = re.sub(r'[^a-z0-9_]', '_', test_name.lower())
    
    # Build assertions (same as before - keep your existing code)
    unique_assertions = []
    for validation in validations[:6]:
        if "title" in validation.lower() and "uidai" in validation.lower():
            unique_assertions.append('            assert "UIDAI" in title or "Aadhaar" in title, "Page title should contain UIDAI or Aadhaar"')
        elif "1947" in validation or "helpline" in validation.lower():
            unique_assertions.append('            assert "1947" in content, "Helpline number 1947 should be displayed"')
        elif "email" in validation.lower() or "help@uidai" in validation.lower():
            unique_assertions.append('            assert "help@uidai.gov.in" in content, "Contact email should be present"')
    
    unique_selectors = []
    for selector in key_selectors[:8]:
        unique_selectors.append(f'''            try:
                elem = await page.query_selector("{selector}")
                if elem:
                    print(f"✓ Found: {selector}")
            except Exception as e:
                print(f"⚠ Error checking {selector}: {{e}}")''')
    
    step_comments = '\n'.join([f'# Step {i+1}: {step}' for i, step in enumerate(steps[:12])])
    assertions_code = '\n'.join(unique_assertions) if unique_assertions else '            pass'
    selectors_code = '\n'.join(unique_selectors) if unique_selectors else '            pass'
    
    # FIXED: Use environment variable for artifacts path
    return f'''import pytest
from playwright.async_api import async_playwright
import os
from pathlib import Path

@pytest.mark.asyncio
async def test_{safe_name}():
    """
    {test_name}
    
    {description}
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=os.getenv("UIDAI_HEADED") != "1"
        )
        context = await browser.new_context(
            viewport={{"width": 1920, "height": 1080}},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # CRITICAL: Get artifacts directory from environment
        artifacts_base = os.getenv("ARTIFACTS_DIR")
        if artifacts_base:
            artifacts_dir = Path(artifacts_base)
        else:
            # Fallback: create in current directory
            artifacts_dir = Path.cwd() / "artifacts"
        
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Artifacts: {{artifacts_dir}}")
        
        try:
            print(f"🚀 Starting: {test_name}")
            print(f"Navigating to {url}...")
            await page.goto("{url}", wait_until="networkidle", timeout=30000)
            
            title = await page.title()
            content = await page.content()
            print(f"✓ Page loaded: {{title}}")
            
            # Basic validation
            assert title, "Page should have a title"
            assert len(content) > 1000, "Page should have substantial content"
            print(f"✓ Content verified ({{len(content)}} bytes)")
            
            # Scenario validations
            print(f"\\n📋 Validations...")
{assertions_code}
            
            # Element checks
            print(f"\\n🔍 Element checks...")
{selectors_code}
            
            # Interactive elements
            links = await page.query_selector_all("a")
            buttons = await page.query_selector_all("button")
            inputs = await page.query_selector_all("input")
            
            total = len(links) + len(buttons) + len(inputs)
            assert total > 10, f"Should have interactive elements, found {{total}}"
            print(f"✓ Found {{len(links)}} links, {{len(buttons)}} buttons, {{len(inputs)}} inputs")
            
            # Success screenshot
            screenshot_path = artifacts_dir / "{safe_name}_success.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"✅ Test passed!")
            print(f"📸 Screenshot: {{screenshot_path}}")
            
        except AssertionError as e:
            print(f"❌ Assertion: {{e}}")
            screenshot_path = artifacts_dir / "{safe_name}_failure.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 Failure: {{screenshot_path}}")
            raise
            
        except Exception as e:
            print(f"❌ Exception: {{e}}")
            screenshot_path = artifacts_dir / "{safe_name}_exception.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 Exception: {{screenshot_path}}")
            raise
            
        finally:
            await browser.close()

# Scenario Steps:
{step_comments}
'''
def fix_common_playwright_mistakes(code: str) -> str:
    """
    Fix common mistakes LLMs make with Playwright Python API
    """
    # Fix JavaScript-style camelCase to Python snake_case
    fixes = {
        'browser.newPage()': 'browser.new_page()',
        'page.querySelector(': 'page.query_selector(',
        'page.querySelectorAll(': 'page.query_selector_all(',
        'page.waitForSelector(': 'page.wait_for_selector(',
        'page.waitForTimeout(': 'page.wait_for_timeout(',
        'page.waitForNavigation(': 'page.wait_for_navigation(',
        'page.waitForLoadState(': 'page.wait_for_load_state(',
    }
    
    for wrong, correct in fixes.items():
        code = code.replace(wrong, correct)
    
    return code
def generate_tests(
    run_id: str,
    url: str,
    pages: List[Dict],
    scenario: Optional[str] = None,
    custom_scenario: Optional[Dict[str, Any]] = None,
    models: Optional[List[str]] = None,
    out_dir: str = "/tmp/uidai_runs"
) -> Dict[str, Any]:
    """
    Main test generation function for UIDAI MVP
    """
    gen_dir = os.path.join(out_dir, run_id, "generator")
    os.makedirs(gen_dir, exist_ok=True)
    tests_dir = os.path.join(gen_dir, "tests")
    os.makedirs(tests_dir, exist_ok=True)

    # Load scenario template
    scenario_obj = None
    template_key = None
    
    if scenario and scenario in SCENARIO_TEMPLATES:
        scenario_obj = SCENARIO_TEMPLATES[scenario]
        template_key = scenario
        print(f"✓ Using scenario template: {scenario_obj['name']}")
    elif custom_scenario:
        scenario_obj = custom_scenario
        print(f"✓ Using custom scenario")
    else:
        print(f"ℹ No scenario - will use auto-discovery")

    # Try AI generation with Ollama models
    if models:
        for model in models:
            try:
                print(f"🤖 Attempting generation with {model}...")
                
                # Build scenario context for prompt
                scenario_context = ""
                if scenario_obj:
                    scenario_context = f"""
                        Test Scenario: {scenario_obj.get('name', 'Custom scenario')}
                        Description: {scenario_obj.get('description', '')}
                        Key Areas to Test:
                        {chr(10).join(['- ' + step for step in scenario_obj.get('steps', [])[:8]])}

                        Key Validations:
                        {chr(10).join(['- ' + val for val in scenario_obj.get('validations', [])[:5]])}

                        Key Selectors to Check:
                        {chr(10).join(['- ' + sel for sel in scenario_obj.get('key_selectors', [])[:5]])}
                        """

                try:
                    test_code = generate_with_model(
                        model=model,
                        url=url,
                        pages=pages[:3],
                        scenario_text=scenario_context if scenario_obj else None
                    )
                except Exception as e:
                    print(f"❌ Exception calling model: {e}")
                    test_code = None

                # DEBUG: Log what we got back
                if test_code:
                    # Clean and fix common mistakes
                    test_code = clean_generated_code(test_code)
                    test_code = fix_common_playwright_mistakes(test_code)  # ADD THIS LINE
                    
                    print(f"🧹 After cleaning (first 300 chars):")
                    print(test_code[:300])
                else:
                    print(f"❌ Model returned None")
                    continue
                if test_code and validate_test_code(test_code):
                    # Generate filename based on scenario
                    if scenario_obj:
                        safe_name = re.sub(r'[^a-z0-9_]', '_', scenario_obj['name'].lower())
                        test_filename = f"test_{safe_name}.py"
                    else:
                        test_filename = f"test_auto_{run_id[:8]}.py"
                    
                    test_path = os.path.join(tests_dir, test_filename)
                    
                    with open(test_path, "w", encoding="utf-8") as f:
                        f.write(test_code)
                    
                    lines = len(test_code.split('\n'))
                    print(f"✅ Generated test with {model}: {lines} lines")
                    
                    return {
                        "ok": True,
                        "tests": [{
                            "filename": test_filename,
                            "path": test_path,
                            "lines": lines,
                            "content": test_code,
                            "model": model,
                            "scenario": scenario_obj['name'] if scenario_obj else "Auto-discovery"
                        }],
                        "count": 1,
                        "scenario": scenario_obj,
                        "scenario_source": f"template:{template_key}" if template_key else "ai",
                        "metadata": {
                            "runId": run_id,
                            "url": url,
                            "models_tried": [model],
                            "model": model,
                            "seed": scenario_obj.get('name') if scenario_obj else None,
                            "scenario_id": template_key if template_key else "auto"
                        }
                    }
                else:
                    print(f"❌ Validation failed")
                    if test_code:
                        # Check what's missing
                        missing = []
                        if 'playwright' not in test_code.lower():
                            missing.append('playwright')
                        if 'async def test_' not in test_code.lower():
                            missing.append('async def test_')
                        if 'await page.' not in test_code.lower():
                            missing.append('await page.')
                        print(f"   Missing: {', '.join(missing)}")
                    continue  
            except Exception as e:
                print(f"❌ Model {model} failed: {e}")
                continue

    # Fallback: Generate scenario-specific stub
    print(f"⚠️ AI generation failed or disabled. Generating scenario-specific stub...")
    
    if scenario_obj:
        # CRITICAL: Generate DIFFERENT stub for each scenario
        test_name = scenario_obj['name']
        safe_name = re.sub(r'[^a-z0-9_]', '_', test_name.lower())
        test_filename = f"test_{safe_name}.py"
        
        # Generate customized stub based on scenario
        test_code = generate_scenario_stub(url, scenario_obj)
        
        print(f"✓ Generated scenario-specific stub: {test_name}")
    else:
        # Generic stub for auto-discovery
        test_name = "UIDAI Auto Discovery"
        test_filename = f"test_auto_discovery.py"
        test_code = generate_stub_test_uidai(url, test_name)
        
        print(f"✓ Generated generic auto-discovery stub")
    
    test_path = os.path.join(tests_dir, test_filename)
    
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_code)
    
    lines = len(test_code.split('\n'))
    
    return {
        "ok": True,
        "tests": [{
            "filename": test_filename,
            "path": test_path,
            "lines": lines,
            "content": test_code,
            "model": "stub",
            "scenario": scenario_obj['name'] if scenario_obj else "Auto-discovery"
        }],
        "count": 1,
        "scenario": scenario_obj,
        "scenario_source": f"template:{template_key}" if template_key else "stub",
        "metadata": {
            "runId": run_id,
            "url": url,
            "models_tried": [],
            "model": "stub",
            "seed": scenario_obj.get('name') if scenario_obj else None,
            "scenario_id": template_key if template_key else "auto"
        }
    }