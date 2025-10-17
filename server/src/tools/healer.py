# server/src/tools/healer.py
import uuid, json, logging
from pathlib import Path
from .ollama_client import generate_with_model

log = logging.getLogger(__name__)

def _make_prompt_for_heal(failing_info, files):
    # A short instructive prompt for a conservative repair. Keep simple for POC.
    return {
        "instruction": "You are a code repair assistant. Provide minimal, low-risk patches only (selectors robustness, add wait_for_selector, increase timeout). Return JSON: {\"suggestions\":[{file, patch, explanation, confidence}]}. Do not change flow logic.",
        "failing": failing_info,
        "files": [{"path": str(f), "content": Path(f).read_text(encoding='utf-8')} for f in files]
    }

def get_heal_suggestions(run_id: str, failingTestInfo: dict, generated_files: list, models: list = None, out_dir: str="/tmp/uidai_runs"):
    out_dir = Path(out_dir) / run_id / "healer"
    out_dir.mkdir(parents=True, exist_ok=True)
    models = models or ["mistral:latest", "llama3.2:latest"]
    prompt = _make_prompt_for_heal(failingTestInfo, generated_files)
    for model in models:
        try:
            raw = generate_with_model(model, prompt, format="json")
            Path(out_dir / f"{model.replace(':','_')}.raw.json").write_text(json.dumps(raw, default=str, indent=2), encoding="utf-8")
            parsed = raw if isinstance(raw, dict) else (json.loads(raw) if isinstance(raw, str) else None)
            if parsed and parsed.get("suggestions"):
                # ensure patchId presence
                for s in parsed["suggestions"]:
                    s["patchId"] = s.get("patchId") or str(uuid.uuid4())
                return {"ok": True, "suggestions": parsed["suggestions"], "fromModel": model}
        except Exception as e:
            log.exception("Healer model %s failed: %s", model, e)
    return {"ok": False, "message": "no suggestions", "raw": None}

def apply_patch(patch: dict, generated_tests_dir: str):
    """
    patch: {"file": "test_smoke.py", "content": "<full file content>"}
    For POC: support receiving full replacement content.
    """
    file_rel = patch.get("file")
    if not file_rel:
        raise ValueError("patch missing 'file'")

    file_path = Path(generated_tests_dir) / file_rel
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
    # backup original if exists
    if file_path.exists():
        backup = file_path.with_suffix(file_path.suffix + ".bak")
        file_path.rename(backup)
    content = patch.get("content") or patch.get("patch")
    if content is None:
        raise ValueError("patch missing 'content' or 'patch'")
    file_path.write_text(content, encoding="utf-8")
    return {"ok": True, "file": str(file_path)}