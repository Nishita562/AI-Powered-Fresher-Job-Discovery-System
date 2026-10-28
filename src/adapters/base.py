"""Common adapter interface. Each website family gets a small adapter class
whose selectors come from ``config/sources.json``."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

from src.browser_manager import BrowserManager
from src.keywords import has_fresher_signal, has_role_signal, has_senior_signal
from src.logger import get_logger
from src.text_utils import clean_whitespace

log = get_logger("adapters")

# Joins the text of matching elements, skipping elements nested inside another
# match so the same paragraph is never captured twice.
_OUTERMOST_TEXT_JS = """(sel) => {
  const els = [...document.querySelectorAll(sel)];
  const top = els.filter(e => !els.some(o => o !== e && o.contains(e)));
  return top.map(e => e.innerText).join('\\n');
}"""
_BOILERPLATE_LINES = {"apply for this job", "apply", "apply now", "back to jobs"}


@dataclass
class CompanyTarget:
    company_name: str
    platform: str          # greenhouse | lever | generic
    url: str
    company_id: str = ""
    token: str = ""
    data_mode: str = "live"  # live | demo_fixture


@dataclass
class AdapterResult:
    company: str
    status: str = "pending"  # success | failed | skipped
    listings_seen: int = 0
    raw_jobs: list[dict] = field(default_factory=list)
    error: str = ""
    detail_pages: int = 0


class BaseAdapter:
    name = "base"

    def __init__(self, browser: BrowserManager, config: dict, max_detail_pages: int, max_listings: int):
        self.browser = browser
        self.config = config
        self.max_detail_pages = max_detail_pages
        self.max_listings = max_listings

    @property
    def page(self):
        return self.browser.page

    def collect(self, target: CompanyTarget) -> AdapterResult:  # pragma: no cover - interface
        raise NotImplementedError

    # ------------------------------------------------------------ helpers
    def _text(self, element, selector: str) -> str:
        try:
            el = element.query_selector(selector) if selector else None
            return clean_whitespace(el.inner_text()) if el else ""
        except Exception:
            return ""

    def _href(self, element, selector: str) -> str:
        try:
            el = element.query_selector(selector) if selector else element
            href = el.get_attribute("href") if el else ""
            return urljoin(self.page.url, href) if href else ""
        except Exception:
            return ""

    @staticmethod
    def detail_priority(title: str) -> int | None:
        """Decide which listings deserve a detail-page visit (lower = sooner).

        None = senior or unrelated title (skipped), 0 = entry-level *and*
        technical, 1 = entry-level, 2 = technical title with no stated level.
        """
        if has_senior_signal(title) and not has_fresher_signal(title):
            return None
        fresher, role = has_fresher_signal(title), has_role_signal(title)
        if fresher and role:
            return 0
        if fresher:
            return 1
        if role:
            return 2
        return None

    def visit_details(self, rows: list[dict], description_selector: str, location_selector: str = "") -> int:
        """Open up to ``max_detail_pages`` detail pages (fresher titles first) and add descriptions."""
        ranked = sorted(
            (r for r in rows if r.get("_priority") is not None and r.get("apply_url")),
            key=lambda r: r["_priority"],
        )[: self.max_detail_pages]
        visited = 0
        for row in ranked:
            nav = self.browser.goto(row["apply_url"], settle_ms=500)
            if not nav.ok:
                row["_detail_error"] = nav.error
                continue
            visited += 1
            detail = self.page.evaluate(_OUTERMOST_TEXT_JS, description_selector) or ""
            detail = "\n".join(l for l in detail.splitlines() if l.strip().lower() not in _BOILERPLATE_LINES)
            if detail.strip():
                existing = row.get("description", "")
                row["description"] = f"{existing}\n{detail}" if existing else detail
            if location_selector and not row.get("location"):
                row["location"] = self._text(self.page, location_selector)
        return visited
