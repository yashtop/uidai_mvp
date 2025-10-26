# server/src/agents/story_generator.py - FIX ASYNC CALLS

import logging
from typing import Dict, Any

from ..state import TestRunState
from ..tools.ollama_client_enhanced import ollama_client

log = logging.getLogger(__name__)

async def story_generator_node(state: TestRunState) -> TestRunState:
    """Story Generator Node - ASYNC"""
    run_id = state['run_id']
    user_story = state.get('user_story')
    
    # If user provided story, use it
    if user_story and len(user_story.strip()) > 20:
        log.info(f"[{run_id}] 📝 Using user-provided story")
        return {
            **state,
            'final_story': user_story,
            'story_source': 'user_provided',
            'phase': 'story_ready'
        }
    
    # Auto-generate story
    log.info(f"[{run_id}] 🤖 Generating story from discovery...")
    
    discovery_data = state.get('discovery_data', {})
    url = state['url']
    
    # Check if discovery data is valid
    if not discovery_data or not discovery_data.get('pages'):
        log.warning(f"[{run_id}] No discovery data, using minimal story")
        fallback_story = f"Test the website at {url}. Verify basic functionality."
        return {
            **state,
            'final_story': fallback_story,
            'story_source': 'fallback',
            'phase': 'story_ready'
        }
    
    prompt = _build_story_prompt(url, discovery_data)
    
    try:
        result = ollama_client.generate_with_fallback(
            task="story_generation",
            prompt=prompt
        )
        
        if not result.get('ok'):
            raise Exception(result.get('error', 'Story generation failed'))
        
        story = result['response'].strip()
        model_used = result['model']
        
        log.info(f"[{run_id}] ✅ Story generated using {model_used}")
        
        return {
            **state,
            'final_story': story,
            'story_source': 'ai_generated',
            'story_model': model_used,
            'phase': 'story_ready'
        }
        
    except Exception as e:
        log.error(f"[{run_id}] Story generation failed: {e}", exc_info=True)
        
        # Fallback story (sync - no await needed)
        fallback_story = _create_fallback_story(url, discovery_data)
        
        return {
            **state,
            'final_story': fallback_story,
            'story_source': 'fallback',
            'phase': 'story_ready'
        }

def _build_story_prompt(url: str, discovery_data: Dict) -> str:
    """Build prompt for story generation"""
    pages = discovery_data.get('pages', [])[:5]
    
    pages_summary = []
    for page in pages:
        page_info = f"- {page.get('url', 'Unknown')}"
        if page.get('title'):
            page_info += f" ({page['title']})"
        pages_summary.append(page_info)
    
    return f"""Analyze this website and write a test story.

URL: {url}
Pages discovered:
{chr(10).join(pages_summary)}

Write a comprehensive user story describing what should be tested. Focus on:
- Navigation and user flows
- Forms and input validation
- Key interactive elements
- Accessibility features

Write ONLY the story (no JSON, no code):"""

def _create_fallback_story(url: str, discovery_data: Dict) -> str:
    """Fallback story when LLM fails - SYNC FUNCTION"""
    pages_count = len(discovery_data.get('pages', []))
    return f"Test the website at {url}. Verify that {pages_count} pages load correctly and core functionality works. Test navigation, forms, and key user interactions."