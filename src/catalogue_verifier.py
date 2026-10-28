"""Checks whether catalogue URLs respond, and records the outcome in companies.csv.

``verified``   – the URL answered with HTTP 2xx/3xx on ``last_checked``.
``unverified`` – not yet checked, timed out, or refused automated access
                 (HTTP 401/403/429 often means bot protection, not a dead link).
``missing``    – no URL is known for the company.

"Verified" only means the official URL was reachable on that date; it does
not mean the company has vacancies.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd

from config import settings
from src.company_catalog import load_catalogue
from src.logger import get_logger

log = get_logger("verifier")
_HEADERS = {"User-Agent": settings.USER_AGENT, "Accept": "text/html,application/xhtml+xml"}


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # installed with many packages; falls back to system store

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def check_url_http(url: str, timeout: float = 12.0) -> tuple[str, str]:
    """Return ``(status, detail)`` for one URL using a single polite GET request."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS, method="GET")
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            final = resp.geturl()
            detail = f"HTTP {resp.status}" + (f" → {final}" if final.rstrip('/') != url.rstrip('/') else "")
            return "verified", detail
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 429):
            return "unverified", f"HTTP {exc.code} (automated access refused)"
        return "unverified", f"HTTP {exc.code}"
    except Exception as exc:
        return "unverified", f"{type(exc).__name__}: {str(exc)[:80]}"


def check_urls_playwright(urls: list[str]) -> dict[str, tuple[str, str]]:
    """Re-check URLs with a real browser (sequential, polite). Used for sites that reject plain HTTP clients."""
    from src.browser_manager import BrowserManager

    results = {}
    with BrowserManager(delay_seconds=0.5, max_retries=1, respect_robots=False) as bm:
        # robots.txt governs crawling content; a single homepage reachability check is not a crawl.
        for url in urls:
            nav = bm.goto(url, settle_ms=0)
            results[url] = ("verified", f"HTTP {nav.status} (browser)") if nav.ok else ("unverified", nav.error + " (browser)")
    return results


def verify_catalogue(limit: int | None = None, engine: str = "http", workers: int = 12,
                     only_unverified: bool = False, path=None) -> dict:
    path = path or settings.COMPANIES_CSV
    df = load_catalogue(path)
    todo = df[df["career_url"] != ""]
    if only_unverified:
        todo = todo[todo["verification_status"] != "verified"]
    if limit:
        todo = todo.head(limit)
    urls = todo["career_url"].tolist()
    log.info("Checking %d URLs with %s engine", len(urls), engine)
    if engine == "playwright":
        results = check_urls_playwright(urls)
    else:
        results = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(check_url_http, u): u for u in urls}
            for fut in as_completed(futures):
                results[futures[fut]] = fut.result()
    today = date.today().isoformat()
    for idx, row in todo.iterrows():
        status, detail = results[row["career_url"]]
        df.at[idx, "verification_status"] = status
        df.at[idx, "verification_detail"] = detail
        df.at[idx, "last_checked"] = today
    df.to_csv(path, index=False)
    counts = pd.Series([r[0] for r in results.values()]).value_counts().to_dict()
    return {"checked": len(results), **counts}
