# server/src/tools/auto_healer.py
"""
Auto-Healing Module
Matches healer.py signature: apply_patch(patch, generated_tests_dir)
"""
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List

log = logging.getLogger(__name__)

def auto_heal_and_rerun(
    run_id: str,
    gen_dir: str,
    failed_tests: List[Dict[str, Any]],
    summary: Dict[str, int],
    generated_files: List[str],
    models: List[str],
    max_attempts: int = 3,
    headed: bool = False,
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    Auto-healing loop: Get suggestions, apply best fix, re-run, repeat
    
    Returns:
        {
            "ok": True/False,
            "attempts": [...],
            "final_result": {...},
            "healed": True/False,
            "healing_attempts": int
        }
    """
    log.info(f"[{run_id}] Starting auto-healing loop (max {max_attempts} attempts)")
    
    # Import here to avoid circular imports
    from .healer import get_heal_suggestions, apply_patch
    from .runner import run_playwright_tests
    
    attempts = []
    
    for attempt_num in range(1, max_attempts + 1):
        log.info(f"[{run_id}] Healing attempt {attempt_num}/{max_attempts}")
        
        # Get healing suggestions
        try:
            heal_result = get_heal_suggestions(
                run_id=run_id,
                failingTestInfo={
                    "report": {"tests": failed_tests},
                    "summary": summary
                },
                generated_files=generated_files,
                models=models
            )
        except Exception as e:
            log.error(f"[{run_id}] Failed to get healing suggestions: {e}")
            continue
        
        if not heal_result.get("ok") or not heal_result.get("suggestions"):
            log.warning(f"[{run_id}] No healing suggestions available")
            break
        
        suggestions = heal_result["suggestions"]
        log.info(f"[{run_id}] Got {len(suggestions)} healing suggestions")
        
        # Select best suggestion
        best_suggestion = select_best_suggestion(suggestions)
        confidence = best_suggestion.get('confidence', 'unknown')
        log.info(f"[{run_id}] Selected suggestion with confidence: {confidence}")
        
        # Create backup before applying patch
        backup_dir = Path(gen_dir).parent / f"tests_backup_attempt_{attempt_num}"
        try:
            shutil.copytree(gen_dir, backup_dir, dirs_exist_ok=True)
            log.info(f"[{run_id}] Backed up tests to {backup_dir}")
        except Exception as e:
            log.error(f"[{run_id}] Failed to backup: {e}")
        
        # Prepare patch dict for apply_patch
        # The healer's apply_patch expects: patch dict with 'file' and 'content' keys
        test_file = best_suggestion.get("file")
        if not test_file and generated_files:
            # If no file specified, use first generated file
            test_file = Path(generated_files[0]).name
        
        # Build patch dict matching what apply_patch expects
        patch_dict = {
            "file": test_file or "test_auto.py",
            "content": best_suggestion.get("fix", ""),  # Use 'fix' as content
            "issue": best_suggestion.get("issue", ""),
            "priority": best_suggestion.get("priority", "medium"),
            "confidence": best_suggestion.get("confidence", 0.5)
        }
        
        # If the suggestion has actual code/content, use it
        if "code" in best_suggestion:
            patch_dict["content"] = best_suggestion["code"]
        elif "patch" in best_suggestion:
            patch_dict["content"] = best_suggestion["patch"]
        
        # Apply the patch using correct signature: apply_patch(patch, generated_tests_dir)
        try:
            log.info(f"[{run_id}] Applying patch to {test_file}...")
            apply_result = apply_patch(patch_dict, gen_dir)
            
            if not apply_result.get("ok"):
                log.error(f"[{run_id}] Failed to apply patch: {apply_result.get('message')}")
                # Restore from backup
                if backup_dir.exists():
                    try:
                        shutil.rmtree(gen_dir)
                        shutil.copytree(backup_dir, gen_dir)
                        log.info(f"[{run_id}] Restored from backup")
                    except Exception as e:
                        log.error(f"[{run_id}] Failed to restore: {e}")
                continue
            
            log.info(f"[{run_id}] ✅ Successfully applied patch")
            
        except Exception as e:
            log.exception(f"[{run_id}] Error applying patch: {e}")
            # Restore from backup
            if backup_dir.exists():
                try:
                    shutil.rmtree(gen_dir)
                    shutil.copytree(backup_dir, gen_dir)
                    log.info(f"[{run_id}] Restored from backup")
                except Exception as e2:
                    log.error(f"[{run_id}] Failed to restore: {e2}")
            continue
        
        # Re-run tests
        log.info(f"[{run_id}] Re-running tests after healing...")
        try:
            rerun_result = run_playwright_tests(
                run_id=run_id,
                gen_dir=gen_dir,
                headed=headed,
                timeout_seconds=timeout_seconds
            )
        except Exception as e:
            log.error(f"[{run_id}] Failed to re-run tests: {e}")
            continue
        
        # Parse new results
        new_summary = rerun_result.get("summary", {})
        new_failed = int(new_summary.get("failed", 0))
        new_passed = int(new_summary.get("passed", 0))
        new_total = int(new_summary.get("total", 0))
        
        log.info(f"[{run_id}] Rerun results: {new_passed}/{new_total} passed, {new_failed} failed")
        
        # Record attempt
        attempts.append({
            "attempt": attempt_num,
            "healing": heal_result,
            "applied_fix": best_suggestion,
            "result": rerun_result,
            "summary": new_summary
        })
        
        # Check if all tests passed
        if new_failed == 0 and new_passed > 0:
            log.info(f"[{run_id}] ✅ All tests passed after {attempt_num} healing attempt(s)!")
            return {
                "ok": True,
                "healed": True,
                "attempts": attempts,
                "final_result": rerun_result,
                "healing_attempts": attempt_num
            }
        
        # Check if situation improved
        original_failed = len(failed_tests)
        if new_failed < original_failed:
            log.info(f"[{run_id}] Improved: {original_failed} → {new_failed} failures")
            # Update for next iteration
            all_tests = rerun_result.get("tests", [])
            failed_tests = [t for t in all_tests if t.get("outcome") == "failed"]
            summary = new_summary
        else:
            log.warning(f"[{run_id}] No improvement, still {new_failed} failures")
    
    # Max attempts reached without full success
    log.info(f"[{run_id}] Healing loop completed after {len(attempts)} attempts")
    
    return {
        "ok": True,
        "healed": False,
        "attempts": attempts,
        "final_result": attempts[-1]["result"] if attempts else None,
        "healing_attempts": len(attempts)
    }

def select_best_suggestion(suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Select the best healing suggestion based on confidence/priority
    """
    if not suggestions:
        return {}
    
    # Sort by confidence if available
    sorted_suggestions = sorted(
        suggestions,
        key=lambda s: float(s.get("confidence", 0.5)),
        reverse=True
    )
    
    return sorted_suggestions[0]