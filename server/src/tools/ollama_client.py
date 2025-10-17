# server/src/tools/ollama_client.py
import os
import json
import logging
import subprocess
import requests

log = logging.getLogger(__name__)
OLLAMA_HTTP = os.getenv("OLLAMA_HTTP", "http://localhost:11434")  # change if different
OLLAMA_CLI = os.getenv("OLLAMA_CLI", "ollama")  # if you have ollama CLI

def generate_with_model(model: str, payload: dict, format: str = "json", timeout: int = 30):
    """
    Try HTTP Ollama endpoint first. Expected shape of request may vary depending on local Ollama version.
    This function attempts a sensible default and returns parsed JSON when possible.
    """
    try:
        url = f"{OLLAMA_HTTP}/api/generate"  # adjust if your endpoint differs
        body = {"model": model, "input": payload, "format": format}
        resp = requests.post(url, json=body, timeout=timeout)
        resp.raise_for_status()
        try:
            data = resp.json()
        except Exception:
            return resp.text
        # try to normalize typical response shapes
        # if 'content' field present - return it
        if isinstance(data, dict) and "content" in data:
            content = data["content"]
            if format == "json":
                if isinstance(content, dict):
                    return content
                try:
                    return json.loads(content)
                except Exception:
                    # return raw string for upstream repair
                    return content
            return data
        return data
    except Exception as e:
        log.debug("HTTP Ollama failed, will try CLI fallback: %s", e)

    # CLI fallback: send JSON payload via subprocess (if ollama CLI supports)
    try:
        # Write payload to temp file and call `ollama` CLI generate if supported.
        p = subprocess.Popen(
            [OLLAMA_CLI, "generate", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        inp = json.dumps({"input": payload, "format": format})
        out, err = p.communicate(inp, timeout=timeout)
        if p.returncode != 0:
            raise RuntimeError(f"ollama cli err: {err}")
        try:
            return json.loads(out)
        except Exception:
            return out
    except Exception as e:
        log.exception("Ollama CLI generate failed: %s", e)
        raise RuntimeError("Ollama invocation failed; ensure ollama is running or configure OLLAMA_HTTP/CLI") from e