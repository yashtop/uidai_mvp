# server/src/tools/discovery.py
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse
import os, json, time, logging
from pathlib import Path

log = logging.getLogger(__name__)

def _short_selector_candidate(el):
    if el is None:
        return None
    if el.has_attr("id"):
        return f"#{el['id']}"
    if el.has_attr("class"):
        # take up to 2 classes
        classes = ".".join([c for c in el.get("class")[:2]])
        return f"{el.name}.{classes}"
    return el.name

def extract_selectors(soup: BeautifulSoup) -> List[Dict[str, str]]:
    selectors = []
    for b in soup.select("button, a, input, form, h1, h2, h3"):
        text = b.get_text(strip=True)[:200] if b.get_text() else ""
        sel = _short_selector_candidate(b)
        selectors.append({"selector": sel, "text": text})
    return selectors

def discover(run_id: str, url: str, level: int = 1, max_pages: int = 10, out_dir: str = "/tmp/uidai_runs") -> Dict[str, Any]:
    out_base = Path(out_dir) / run_id / "discovery"
    out_base.mkdir(parents=True, exist_ok=True)
    visited = set()
    to_visit = [url]
    pages = []
    start = time.time()

    while to_visit and len(visited) < max_pages:
        cur = to_visit.pop(0)
        if cur in visited:
            continue
        try:
            resp = requests.get(cur, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title else ""
            sels = extract_selectors(soup)
            filename = f"page_{len(pages)}.html"
            (out_base / filename).write_text(resp.text, encoding="utf-8")
            pages.append({"url": cur, "title": title, "selectors": sels, "html_path": str(out_base/filename)})
            visited.add(cur)

            if level > 1:
                base = urlparse(url).netloc
                for a in soup.find_all("a", href=True):
                    href = urljoin(cur, a["href"])
                    if urlparse(href).netloc == base and href not in visited and href not in to_visit:
                        to_visit.append(href)
        except Exception as e:
            log.exception("Discovery error for %s: %s", cur, e)
            pages.append({"url": cur, "error": str(e)})
    meta = {"runId": run_id, "start": start, "end": time.time(), "count": len(pages)}
    (out_base / "summary.json").write_text(json.dumps({"pages": pages, "meta": meta}, default=str), encoding="utf-8")
    return {"pages": pages, "metadata": meta}