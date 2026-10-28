"""Generic career-page adapter (Python port of the original Node.js scraper).

Tries a list of common listing selectors, falls back to whole-page text,
and keeps chunks that look fresher-relevant. Works on arbitrary career
pages, so results are less structured than the Greenhouse/Lever adapters.
"""

from __future__ import annotations

from src.adapters.base import AdapterResult, BaseAdapter, CompanyTarget, log
from src.extractors import parse_experience
from src.keywords import has_fresher_signal, has_senior_signal
from src.text_utils import clean_whitespace


class GenericCareerPageAdapter(BaseAdapter):
    name = "generic"

    def _listing_elements(self):
        for selector in self.config["listing_selectors"]:
            try:
                elements = self.page.query_selector_all(selector)
            except Exception:
                continue
            if self.config.get("min_elements", 1) <= len(elements) < self.config.get("max_elements", 500):
                with_text = [e for e in elements if clean_whitespace(e.inner_text())]
                if with_text:
                    return selector, with_text
        return None, []

    def collect(self, target: CompanyTarget) -> AdapterResult:
        result = AdapterResult(company=target.company_name)
        nav = self.browser.goto(target.url, settle_ms=self.config.get("wait_after_load_ms", 1500))
        if not nav.ok:
            result.status, result.error = "failed", nav.error
            return result
        selector, elements = self._listing_elements()
        rows: list[dict] = []
        if elements:
            for el in elements[: self.max_listings]:
                text = el.inner_text().strip()
                # Table cells arrive tab-separated; treat each cell like a line.
                lines = [clean_whitespace(part) for part in text.replace("\t", "\n").splitlines() if clean_whitespace(part)]
                if not lines:
                    continue
                title = lines[0][:150]
                min_exp = parse_experience(text, require_context=False)[0]
                entry_level = has_fresher_signal(text) or (min_exp is not None and min_exp <= 1)
                if has_senior_signal(title) or not (entry_level or self.detail_priority(title) is not None):
                    continue
                link = self._href(el, "a[href]")
                rows.append({
                    "title": title,
                    "company": target.company_name,
                    "location": self._text(el, "[class*='location']"),
                    "employment_hint": self._text(el, "[class*='type'], [class*='commitment']"),
                    "experience_text": self._text(el, "[class*='experience']"),
                    "description": "\n".join(lines[1:]),
                    "apply_url": link if link and link.split("#")[0] != self.page.url.split("#")[0] else "",
                    "_priority": 0 if has_fresher_signal(text) else 2,
                })
        else:
            # Last resort from the prototype: scan visible text lines.
            body = self.page.inner_text("body")
            for line in (clean_whitespace(x) for x in body.splitlines()):
                if len(line) > 20 and has_fresher_signal(line) and not has_senior_signal(line):
                    rows.append({"title": line[:150], "company": target.company_name, "description": line,
                                 "apply_url": "", "_priority": None})
            rows = rows[:25]
        result.listings_seen = len(elements) if elements else len(rows)
        result.detail_pages = self.visit_details(rows, "main, article, [class*='description']")
        for r in rows:  # jobs without their own link point to the career page itself
            if not r.get("apply_url"):
                r["apply_url"], r["url_is_shared"] = target.url, True
        result.raw_jobs = rows
        result.status = "success"
        log.info("[generic] %s: selector=%s, %d elements, %d fresher-relevant rows",
                 target.company_name, selector, result.listings_seen, len(rows))
        return result
