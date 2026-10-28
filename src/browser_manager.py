"""Playwright browser lifecycle with polite, rule-respecting navigation.

* One Chromium instance and one page at a time — never hundreds of tabs.
* robots.txt is checked before every navigation (``RESPECT_ROBOTS_TXT``).
* A per-host delay is enforced (the larger of our setting and robots
  ``Crawl-delay``).
* HTTP 401/403/429 and CAPTCHA / anti-bot interstitials are treated as
  "access restricted": the page is skipped, never bypassed.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from config import settings
from src.logger import get_logger

log = get_logger("browser")

_BLOCK_MARKERS = ("captcha", "are you a robot", "verify you are human", "cf-challenge", "access denied",
                  "unusual traffic", "bot detection", "attention required")


@dataclass
class NavResult:
    ok: bool
    status: int | None = None
    final_url: str = ""
    error: str = ""


class RobotsCache:
    """Caches one robots.txt parser per host."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._parsers: dict[str, RobotFileParser | None] = {}

    def _parser(self, url: str) -> RobotFileParser | None:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            return None
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._parsers:
            rp = RobotFileParser()
            try:
                req = urllib.request.Request(f"{host}/robots.txt", headers={"User-Agent": self.user_agent})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    rp.parse(resp.read().decode("utf-8", "ignore").splitlines())
            except urllib.error.HTTPError as exc:
                # Per the robots convention: 4xx (no file) = allowed; 401/403 = treat as disallowed.
                rp.parse(["User-agent: *", "Disallow: /"] if exc.code in (401, 403) else [])
            except Exception as exc:  # network error: be conservative but do not crash
                log.warning("robots.txt unavailable for %s (%s); assuming allowed", host, exc)
                rp.parse([])
            self._parsers[host] = rp
        return self._parsers[host]

    def allowed(self, url: str) -> bool:
        rp = self._parser(url)
        return True if rp is None else rp.can_fetch(self.user_agent, url)

    def crawl_delay(self, url: str) -> float:
        rp = self._parser(url)
        if rp is None:
            return 0.0
        delay = rp.crawl_delay(self.user_agent)
        return float(delay) if delay else 0.0


class BrowserManager:
    """Context manager owning the Playwright driver, browser, context and page."""

    def __init__(self, headless: bool = settings.HEADLESS, nav_timeout_ms: int = settings.NAV_TIMEOUT_MS,
                 max_retries: int = settings.MAX_RETRIES, delay_seconds: float = settings.REQUEST_DELAY_SECONDS,
                 user_agent: str = settings.USER_AGENT, respect_robots: bool = settings.RESPECT_ROBOTS_TXT):
        self.headless = headless
        self.nav_timeout_ms = nav_timeout_ms
        self.max_retries = max(1, max_retries)
        self.delay_seconds = delay_seconds
        self.user_agent = user_agent
        self.respect_robots = respect_robots
        self.robots = RobotsCache(user_agent)
        self._last_hit: dict[str, float] = {}
        self._pw = self.browser = self.context = self.page = None
        self.pages_visited = 0

    def __enter__(self) -> "BrowserManager":
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        try:
            self.browser = self._pw.chromium.launch(headless=self.headless)
        except Exception as exc:
            self._pw.stop()
            raise RuntimeError(
                "Could not launch Chromium. Run `python -m playwright install chromium` and try again."
            ) from exc
        self.context = self.browser.new_context(user_agent=self.user_agent, viewport={"width": 1366, "height": 900})
        self.context.set_default_timeout(self.nav_timeout_ms)
        self.page = self.context.new_page()
        log.info("Chromium started (headless=%s)", self.headless)
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        for obj, name in ((self.context, "context"), (self.browser, "browser")):
            try:
                if obj is not None:
                    obj.close()
            except Exception as err:  # already closed / driver gone
                log.debug("Ignoring error while closing %s: %s", name, err)
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
        self._pw = self.browser = self.context = self.page = None
        log.info("Browser closed")

    # ------------------------------------------------------------ navigation
    def _wait_politely(self, url: str) -> None:
        host = urlsplit(url).netloc
        if not host:  # file:// fixtures need no delay
            return
        delay = max(self.delay_seconds, self.robots.crawl_delay(url) if self.respect_robots else 0.0)
        elapsed = time.monotonic() - self._last_hit.get(host, 0.0)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_hit[host] = time.monotonic()

    def _looks_blocked(self) -> bool:
        try:
            title = (self.page.title() or "").lower()
            body = (self.page.inner_text("body", timeout=3000) or "")[:3000].lower()
        except Exception:
            return False
        return any(marker in title or (marker in body and len(body) < 1500) for marker in _BLOCK_MARKERS)

    def goto(self, url: str, settle_ms: int = 1200) -> NavResult:
        from playwright.sync_api import Error as PlaywrightError

        if self.respect_robots and not self.robots.allowed(url):
            log.info("Skipping %s — disallowed by robots.txt", url)
            return NavResult(False, error="Disallowed by robots.txt (skipped)")
        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            self._wait_politely(url)
            try:
                try:
                    response = self.page.goto(url, wait_until="domcontentloaded", timeout=self.nav_timeout_ms)
                except PlaywrightError as exc:
                    # A JavaScript redirect (e.g. to a regional site) aborts the first
                    # navigation; the page is reachable, so wait for the new one instead.
                    if "interrupted by another navigation" not in str(exc):
                        raise
                    self.page.wait_for_load_state("domcontentloaded", timeout=self.nav_timeout_ms)
                    response = None
                self.pages_visited += 1
                status = response.status if response else None
                if status in (401, 403, 429):
                    return NavResult(False, status, self.page.url, f"HTTP {status}: access restricted (not bypassed)")
                if status is not None and status >= 500:
                    last_error = f"HTTP {status}"
                    raise PlaywrightError(last_error)
                if status == 404:
                    return NavResult(False, status, self.page.url, "HTTP 404: page not found")
                try:  # let client-side rendered boards populate
                    self.page.wait_for_load_state("networkidle", timeout=5000)
                except PlaywrightError:
                    pass
                if settle_ms:
                    self.page.wait_for_timeout(settle_ms)
                if self._looks_blocked():
                    return NavResult(False, status, self.page.url, "CAPTCHA / anti-bot page detected (skipped, not bypassed)")
                return NavResult(True, status, self.page.url)
            except PlaywrightError as exc:
                last_error = str(exc).splitlines()[0][:200]
                log.warning("Attempt %d/%d failed for %s: %s", attempt, self.max_retries, url, last_error)
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
        return NavResult(False, error=last_error or "navigation failed")
