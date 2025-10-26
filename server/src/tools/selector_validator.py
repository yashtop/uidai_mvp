# server/src/tools/selector_validator.py - NEW FILE

import logging
from playwright.async_api import async_playwright

log = logging.getLogger(__name__)

async def validate_and_fix_selectors(test_code: str, url: str) -> str:
    """
    Validate selectors in test code and fix ambiguous ones
    """
    
    log.info("Validating selectors...")
    
    # Extract selectors from code
    import re
    selectors = re.findall(r'get_by_role\([^)]+\)', test_code)
    
    if not selectors:
        return test_code
    
    # Test each selector
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        
        for selector in selectors:
            try:
                # Count how many elements match
                count = await page.locator(f"role={selector}").count()
                
                if count > 1:
                    log.warning(f"Ambiguous selector found: {selector} matches {count} elements")
                    # Add .first to handle multiple matches
                    test_code = test_code.replace(
                        f"{selector}.click()",
                        f"{selector}.first.click()"
                    )
                    test_code = test_code.replace(
                        f"{selector}.fill(",
                        f"{selector}.first.fill("
                    )
            except Exception as e:
                log.warning(f"Could not validate selector {selector}: {e}")
        
        await browser.close()
    
    return test_code