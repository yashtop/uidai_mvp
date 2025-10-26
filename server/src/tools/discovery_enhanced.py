# server/src/tools/discovery_enhanced_py313.py
"""
Enhanced Discovery Module - Python 3.13 Compatible
Uses html.parser instead of lxml
"""
import logging
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright

log = logging.getLogger(__name__)

async def discover_with_selectors_async(run_id: str, url: str, level: int = 1, max_pages: int = 15):
    """
    Async discovery with Playwright
    Handles Cloudflare and bot detection
    """
    log.info(f"[{run_id}] Starting async discovery for {url}")
    
    discovered_pages = []
    
    async with async_playwright() as p:
        # Launch browser with anti-detection
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        # Create context with realistic settings
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US'
        )
        
        page = await context.new_page()
        
        # Add anti-detection script
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        try:
            log.info(f"[{run_id}] Navigating to {url}")
            
            # Navigate with network idle
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for potential Cloudflare check
            await page.wait_for_timeout(3000)
            
            # Get page info
            title = await page.title()
            log.info(f"[{run_id}] Page title: {title}")
            
            # Check if blocked by Cloudflare
            if "Just a moment" in title or "Cloudflare" in title:
                log.warning(f"[{run_id}] Cloudflare detected, waiting longer...")
                await page.wait_for_timeout(7000)
                title = await page.title()
                log.info(f"[{run_id}] After wait, title: {title}")
            
            # Extract selectors
            selectors = await page.evaluate('''() => {
                const elements = document.querySelectorAll('a, button, input, form, nav');
                return Array.from(elements).slice(0, 50).map(el => {
                    // Generate selector
                    let selector = '';
                    if (el.id) {
                        selector = `#${el.id}`;
                    } else if (el.className) {
                        const classes = el.className.split(' ').filter(c => c);
                        if (classes.length > 0) {
                            selector = `.${classes[0]}`;
                        }
                    }
                    if (!selector) {
                        selector = el.tagName.toLowerCase();
                    }
                    
                    return {
                        tag: el.tagName.toLowerCase(),
                        text: (el.textContent || '').trim().slice(0, 50),
                        selector: selector,
                        href: el.href || '',
                        type: el.type || ''
                    };
                }).filter(el => el.text || el.href);
            }''')
            
            log.info(f"[{run_id}] Extracted {len(selectors)} elements")
            
            # Extract forms
            forms = await page.evaluate('''() => {
                const formElements = document.querySelectorAll('form');
                return Array.from(formElements).map((form, idx) => ({
                    id: form.id || `form_${idx}`,
                    action: form.action || '',
                    method: form.method || 'get',
                    fields: Array.from(form.querySelectorAll('input, textarea, select')).map(field => ({
                        name: field.name || '',
                        type: field.type || '',
                        required: field.required
                    }))
                }));
            }''')
            
            log.info(f"[{run_id}] Found {len(forms)} forms")
            
            discovered_pages.append({
                'url': url,
                'title': title,
                'selectors': selectors,
                'forms': forms
            })
            
        except Exception as e:
            log.error(f"[{run_id}] Discovery error: {e}", exc_info=True)
            # Return minimal data on error
            discovered_pages.append({
                'url': url,
                'title': 'Error loading page',
                'selectors': [],
                'forms': [],
                'error': str(e)
            })
        finally:
            await context.close()
            await browser.close()
    
    return {
        'pages': discovered_pages,
        'total_pages': len(discovered_pages)
    }

# Keep the old sync function for backward compatibility (but don't use it in async context)
def discover_with_selectors(run_id: str, url: str, level: int = 1, max_pages: int = 15):
    """
    Sync wrapper - ONLY use this outside async context
    DO NOT use this in LangGraph nodes
    """
    import asyncio
    return asyncio.run(discover_with_selectors_async(run_id, url, level, max_pages))

def extract_page_info(page, url: str, run_id: str) -> Dict[str, Any]:
    """
    Extract comprehensive page information including real selectors
    Python 3.13 compatible - uses html.parser
    """
    # Get basic info
    title = page.title()
    html = page.content()
    
    # Parse HTML with html.parser (Python 3.13 compatible)
    # Changed from: soup = BeautifulSoup(html, 'lxml')
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract interactive elements with real selectors
    interactive_elements = extract_interactive_elements(page, soup)
    
    # Extract navigation elements
    navigation = extract_navigation(soup)
    
    # Extract forms
    forms = extract_forms(soup)
    
    # Get page structure
    structure = {
        "has_header": bool(soup.find(['header', 'div.header', 'div#header'])),
        "has_footer": bool(soup.find(['footer', 'div.footer', 'div#footer'])),
        "has_nav": bool(soup.find(['nav', 'div.nav', 'ul.menu'])),
        "has_search": bool(soup.find('input', type='search') or soup.find('input', attrs={'name': lambda x: x and 'search' in x.lower()})),
    }
    
    log.info(f"[{run_id}] Extracted {len(interactive_elements)} interactive elements from {url}")
    
    return {
        "url": url,
        "title": title,
        "selectors": interactive_elements[:50],  # Top 50 elements
        "navigation": navigation,
        "forms": forms,
        "structure": structure,
        "metadata": {
            "links_count": len(soup.find_all('a')),
            "buttons_count": len(soup.find_all('button')),
            "inputs_count": len(soup.find_all('input')),
            "images_count": len(soup.find_all('img')),
            "parser": "html.parser"
        }
    }

def extract_interactive_elements(page, soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extract interactive elements with visibility and position info
    """
    elements = []
    
    # Execute JavaScript to get visibility info
    js_code = """
    () => {
        const getSelector = (el) => {
            if (el.id) return `#${el.id}`;
            if (el.className && typeof el.className === 'string') {
                const classes = el.className.trim().split(/\\s+/).filter(c => c);
                if (classes.length > 0) return `.${classes[0]}`;
            }
            return el.tagName.toLowerCase();
        };
        
        const isVisible = (el) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return rect.width > 0 && rect.height > 0 && 
                   style.visibility !== 'hidden' && 
                   style.display !== 'none' &&
                   style.opacity !== '0';
        };
        
        const elements = [];
        const tags = ['a', 'button', 'input', 'select', 'textarea', 'nav', 'header', 'footer'];
        
        tags.forEach(tag => {
            document.querySelectorAll(tag).forEach(el => {
                const rect = el.getBoundingClientRect();
                const selector = getSelector(el);
                elements.push({
                    tag: el.tagName.toLowerCase(),
                    selector: selector,
                    text: el.textContent?.trim().slice(0, 100) || '',
                    visible: isVisible(el),
                    position: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    requires_scroll: rect.y > window.innerHeight || rect.y < 0,
                    type: el.type || el.getAttribute('type') || '',
                    name: el.name || el.getAttribute('name') || '',
                    id: el.id || '',
                    classes: el.className || ''
                });
            });
        });
        
        return elements;
    }
    """
    
    try:
        elements = page.evaluate(js_code)
        # Filter out duplicates and sort by importance
        seen = set()
        unique_elements = []
        
        for elem in elements:
            key = (elem['selector'], elem['text'][:30])
            if key not in seen:
                seen.add(key)
                unique_elements.append(elem)
        
        return unique_elements
        
    except Exception as e:
        log.warning(f"Failed to extract elements with JS: {e}")
        # Fallback to simple extraction
        return extract_simple_selectors(soup)

def extract_simple_selectors(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Fallback: Simple selector extraction without visibility info
    Works with html.parser
    """
    elements = []
    
    # Links
    for link in soup.find_all('a', href=True):
        selector = f"a[href='{link['href']}']" if link.get('href') else 'a'
        elements.append({
            'tag': 'a',
            'selector': selector,
            'text': link.get_text(strip=True)[:100],
            'visible': True,  # Assume visible
            'type': 'link'
        })
    
    # Buttons
    for button in soup.find_all('button'):
        selector = f"#{button.get('id')}" if button.get('id') else 'button'
        elements.append({
            'tag': 'button',
            'selector': selector,
            'text': button.get_text(strip=True)[:100],
            'visible': True,
            'type': 'button'
        })
    
    # Inputs
    for input_elem in soup.find_all('input'):
        selector = f"input[name='{input_elem.get('name')}']" if input_elem.get('name') else 'input'
        elements.append({
            'tag': 'input',
            'selector': selector,
            'type': input_elem.get('type', 'text'),
            'name': input_elem.get('name', ''),
            'visible': True
        })
    
    return elements

def extract_navigation(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract navigation links - html.parser compatible"""
    nav_elements = soup.find_all(['nav']) or []
    
    # Also look for common navigation class names
    nav_elements.extend(soup.find_all('div', class_=lambda x: x and any(nav_class in x.lower() for nav_class in ['nav', 'menu', 'navigation'])))
    
    nav_links = []
    
    for nav in nav_elements:
        for link in nav.find_all('a', href=True):
            nav_links.append({
                'text': link.get_text(strip=True),
                'href': link['href'],
                'selector': f"nav a[href='{link['href']}']"
            })
    
    return nav_links[:20]  # Top 20 nav links

def extract_forms(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract form information - html.parser compatible"""
    forms = []
    
    for form in soup.find_all('form'):
        form_info = {
            'action': form.get('action', ''),
            'method': form.get('method', 'get').upper(),
            'inputs': []
        }
        
        for input_elem in form.find_all(['input', 'select', 'textarea']):
            form_info['inputs'].append({
                'type': input_elem.get('type', 'text'),
                'name': input_elem.get('name', ''),
                'id': input_elem.get('id', ''),
                'required': input_elem.has_attr('required')
            })
        
        forms.append(form_info)
    
    return forms