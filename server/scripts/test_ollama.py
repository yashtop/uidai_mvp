# scripts/test_ollama.py
"""
Quick test script to validate Ollama invocation + parser.
Usage:
  python scripts/test_ollama.py
"""

import os
from src.ollama_client import call_ollama_with_failover, parse_generator_output

PROMPT = """
You are a test generator. Produce JSON with a top-level "files" array where each item is {"filename":"...","content":"..."}.
Create one file smoke.basic.spec.js with a simple Playwright test that opens https://example.cypress.io and expects the title to be truthy.
Return only JSON (no surrounding text or commentary).
"""

def main():
    models = os.environ.get("OLLAMA_MODELS", "llama3.2:latest,deepseek-r1:7b,mistral:latest").split(",")
    res = call_ollama_with_failover(prompt=PROMPT, models=models, run_folder="./runs/tmp", seed="basic-smoke")
    print("RESULT:", "OK" if res.get("ok") else "FAIL", "model:", res.get("model"))
    if res.get("ok"):
        txt = res.get("text")
        print("raw length:", len(txt) if txt else 0)
        parsed = parse_generator_output(txt)
        print("parse:", parsed.get("ok"), parsed.get("error") or (parsed.get("value") and len(parsed.get("value").get("files",[]))))
    else:
        print("error:", res.get("error"), "models tried:", res.get("models_tried"))

if __name__ == "__main__":
    main()