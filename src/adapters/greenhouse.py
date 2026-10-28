"""Adapter for public Greenhouse job boards (job-boards.greenhouse.io/<token>)."""

from __future__ import annotations

from src.adapters.base import AdapterResult, BaseAdapter, CompanyTarget, log


class GreenhouseAdapter(BaseAdapter):
    name = "greenhouse"

    def collect(self, target: CompanyTarget) -> AdapterResult:
        cfg = self.config
        result = AdapterResult(company=target.company_name)
        base_url = target.url or cfg["board_url"].format(token=target.token)
        rows: list[dict] = []
        seen_urls: set[str] = set()
        for page_no in range(1, int(cfg.get("max_pages", 1)) + 1):
            url = base_url if page_no == 1 else f"{base_url}{'&' if '?' in base_url else '?'}page={page_no}"
            nav = self.browser.goto(url)
            if not nav.ok:
                if page_no == 1:
                    result.status, result.error = "failed", nav.error
                    return result
                break
            new_on_page = 0
            for el in self.page.query_selector_all(cfg["listing_selector"]):
                link = self._href(el, cfg["link_selector"])
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)
                title = self._text(el, cfg["title_selector"])
                rows.append({
                    "title": title,
                    "company": target.company_name,
                    "location": self._text(el, cfg["location_selector"]),
                    "apply_url": link,
                    "_priority": self.detail_priority(title),
                })
                new_on_page += 1
            if new_on_page == 0 or len(rows) >= self.max_listings:
                break
        result.listings_seen = len(rows)
        result.detail_pages = self.visit_details(rows, cfg["detail"]["description_selector"], cfg["detail"]["location_selector"])
        # Keep jobs that are plausibly fresher-relevant: visited detail pages and fresher-titled rows.
        result.raw_jobs = [r for r in rows if r["_priority"] is not None and (r.get("description") or r["_priority"] <= 1)]
        result.status = "success"
        log.info("[greenhouse] %s: %d listings, %d detail pages, %d kept",
                 target.company_name, len(rows), result.detail_pages, len(result.raw_jobs))
        return result
