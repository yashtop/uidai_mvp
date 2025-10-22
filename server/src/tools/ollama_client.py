# server/src/tools/ollama_client.py
import os
import json
import logging
import subprocess
import requests

log = logging.getLogger(__name__)
OLLAMA_HTTP = os.getenv("OLLAMA_HTTP", "http://localhost:11434")  # change if different
OLLAMA_CLI = os.getenv("OLLAMA_CLI", "ollama")  # if you have ollama CLI

def generate_with_model(model: str, payload: dict | None = None, format: str = "json", timeout: int = 30, **kwargs):
    """
    Flexible Ollama call.

    You can call either:
      - generate_with_model("mistral:latest", payload={"instruction": "...", "url": "..."} )
    or
      - generate_with_model("mistral:latest", url="...", pages=[...], instruction="...")

    Returns parsed JSON when possible, or raw text.
    """
    # Normalize payload: explicit payload param has priority; else build from kwargs
    input_payload = payload if payload is not None else kwargs

    # Prepare HTTP request to Ollama (common Ollama HTTP API shape)
    try:
        url = f"{OLLAMA_HTTP}/api/generate"
        body = {"model": model, "input": input_payload, "format": format}
        log.debug("OLLAMA HTTP request body: %s", json.dumps(body)[:2000])
        resp = requests.post(url, json=body, timeout=timeout)
        resp.raise_for_status()
        # Try to parse JSON, otherwise return raw text
        try:
            data = resp.json()
        except Exception:
            return resp.text

        # Normalization for common shapes
        if isinstance(data, dict) and "content" in data:
            content = data["content"]
            if format == "json":
                if isinstance(content, dict):
                    return content
                try:
                    return json.loads(content)
                except Exception:
                    return content
            return data
        return data
    except Exception as e:
        log.debug("HTTP Ollama failed (%s), will try CLI fallback", e)

    # CLI fallback
    try:
        # Build CLI input: send JSON that includes 'input' so CLI can read it
        cli_input = json.dumps({"input": input_payload, "format": format})
        p = subprocess.Popen(
            [OLLAMA_CLI, "generate", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out, err = p.communicate(cli_input, timeout=timeout)
        if p.returncode != 0:
            raise RuntimeError(f"ollama cli err: {err}")
        try:
            return json.loads(out)
        except Exception:
            return out
    except Exception as e:
        log.exception("Ollama CLI generate failed: %s", e)
        raise RuntimeError("Ollama invocation failed; ensure ollama is running or configure OLLAMA_HTTP/CLI") from e
