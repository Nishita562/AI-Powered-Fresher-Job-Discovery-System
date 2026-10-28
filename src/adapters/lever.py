"""Adapter for public Lever job boards (jobs.lever.co/<token>)."""

from __future__ import annotations

from src.adapters.base import AdapterResult, BaseAdapter, CompanyTarget, log


class LeverAdapter(BaseAdapter):
    name = "lever"

    def collect(self, target: CompanyTarget) -> AdapterResult:
        cfg = self.config
        result = AdapterResult(company=target.company_name)
        nav = self.browser.goto(target.url or cfg["board_url"].format(token=target.token))
        if not nav.ok:
            result.status, result.error = "failed", nav.error
            return result
        rows: list[dict] = []
        seen: set[str] = set()
        for el in self.page.query_selector_all(cfg["listing_selector"])[: self.max_listings]:
            link = self._href(el, cfg["link_selector"])
            if not link or link in seen:
                continue
            seen.add(link)
            title = self._text(el, cfg["title_selector"])
            rows.append({
                "title": title,
                "company": target.company_name,
                "location": self._text(el, cfg["location_selector"]),
                "employment_hint": self._text(el, cfg["commitment_selector"]),
                "workplace_hint": self._text(el, cfg["workplace_selector"]).replace("—", "").strip(),
                "apply_url": link,
                "_priority": self.detail_priority(title),
            })
        result.listings_seen = len(rows)
        result.detail_pages = self.visit_details(rows, cfg["detail"]["description_selector"], cfg["detail"]["location_selector"])
        result.raw_jobs = [r for r in rows if r["_priority"] is not None and (r.get("description") or r["_priority"] <= 1)]
        result.status = "success"
        log.info("[lever] %s: %d listings, %d detail pages, %d kept",
                 target.company_name, len(rows), result.detail_pages, len(result.raw_jobs))
        return result
