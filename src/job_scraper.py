"""Crawl orchestration: catalogue -> adapters -> extraction -> de-duplication -> SQLite.

Companies are processed sequentially inside fixed-size batches using a
single browser page. Results are saved after every batch, so stopping a
crawl (or a website failing) never loses work that already succeeded.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from config import settings
from src.adapters import ADAPTERS, CompanyTarget
from src.browser_manager import BrowserManager
from src.company_catalog import crawlable, load_catalogue
from src.deduplication import deduplicate
from src.extractors import build_job_record
from src.logger import get_logger
from src.models import JobRecord
from src.storage import JobStore

log = get_logger("scraper")


def load_source_config() -> dict:
    return json.loads(Path(settings.SOURCES_JSON).read_text(encoding="utf-8"))


def fixture_targets() -> list[CompanyTarget]:
    """Local demo career pages (fictional companies) for offline Playwright runs."""
    index = json.loads((settings.FIXTURE_DIR / "index.json").read_text(encoding="utf-8"))
    return [
        CompanyTarget(company_name=e["company"], platform=e["platform"],
                      url=(settings.FIXTURE_DIR / e["file"]).resolve().as_uri(),
                      company_id=e.get("id", ""), data_mode="demo_fixture")
        for e in index["pages"]
    ]


def live_targets(company_names: list[str] | None = None, limit: int | None = None,
                 catalogue: pd.DataFrame | None = None) -> list[CompanyTarget]:
    """Build targets from the catalogue. Public Greenhouse/Lever boards are preferred."""
    cfg = load_source_config()
    df = crawlable(catalogue if catalogue is not None else load_catalogue())
    if company_names:
        wanted = {n.lower() for n in company_names}
        df = df[df["company_name"].str.lower().isin(wanted)]
    targets = []
    for _, row in df.iterrows():
        platform = row["ats_platform"] if row["ats_platform"] in ("greenhouse", "lever") and row["ats_board_token"] else "generic"
        url = cfg[platform]["board_url"].format(token=row["ats_board_token"]) if platform != "generic" else row["career_url"]
        targets.append(CompanyTarget(company_name=row["company_name"], platform=platform, url=url,
                                     company_id=row["company_id"], token=row["ats_board_token"], data_mode="live"))
    return targets[:limit] if limit else targets


@dataclass
class CrawlSummary:
    mode: str
    run_id: int | None = None
    companies_attempted: int = 0
    companies_succeeded: int = 0
    companies_failed: int = 0
    listings_seen: int = 0
    jobs_saved: int = 0
    new_jobs: int = 0
    duplicates_removed: int = 0
    pages_visited: int = 0
    seconds: float = 0.0
    status: str = "running"
    errors: list[dict] = field(default_factory=list)
    per_company: list[dict] = field(default_factory=list)


def _source_label(target: CompanyTarget) -> str:
    if target.data_mode == "demo_fixture":
        return f"Demo fixture page ({target.platform} layout)"
    return {"greenhouse": "Greenhouse public board", "lever": "Lever public board"}.get(target.platform, "Company career page")


def run_crawl(
    targets: list[CompanyTarget],
    mode: str,
    store: JobStore | None = None,
    batch_size: int = settings.BATCH_SIZE,
    max_detail_pages: int = settings.MAX_DETAIL_PAGES_PER_COMPANY,
    headless: bool = settings.HEADLESS,
    progress: Callable[[dict], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    browser_kwargs: dict | None = None,
) -> CrawlSummary:
    store = store or JobStore()
    cfg = load_source_config()
    summary = CrawlSummary(mode=mode, run_id=store.start_run(mode))
    started = time.monotonic()

    def report(current: str = "") -> None:
        if progress:
            progress({**summary.__dict__, "total": len(targets), "current_company": current,
                      "done": summary.companies_attempted})

    report()
    try:
        with BrowserManager(headless=headless, **(browser_kwargs or {})) as browser:
            for start in range(0, len(targets), batch_size):
                batch = targets[start:start + batch_size]
                batch_records: list[JobRecord] = []
                for target in batch:
                    if should_stop and should_stop():
                        summary.status = "stopped"
                        break
                    report(target.company_name)
                    adapter_cls = ADAPTERS.get(target.platform, ADAPTERS["generic"])
                    adapter = adapter_cls(browser, cfg[adapter_cls.name], max_detail_pages, settings.MAX_LISTINGS_PER_COMPANY)
                    error = ""
                    try:
                        res = adapter.collect(target)
                    except Exception as exc:  # one bad page must not stop the crawl
                        log.exception("Adapter crashed for %s", target.company_name)
                        res = None
                        error = f"{type(exc).__name__}: {str(exc)[:150]}"
                    summary.companies_attempted += 1
                    if res is None or res.status != "success":
                        summary.companies_failed += 1
                        err = error if res is None else res.error
                        summary.errors.append({"company": target.company_name, "error": err})
                        summary.per_company.append({"company": target.company_name, "status": "failed", "error": err, "jobs": 0})
                        continue
                    summary.companies_succeeded += 1
                    summary.listings_seen += res.listings_seen
                    records = [r for r in (build_job_record(raw, source=_source_label(target), source_type=target.platform,
                                                            data_mode=target.data_mode) for raw in res.raw_jobs) if r]
                    batch_records.extend(records)
                    summary.per_company.append({"company": target.company_name, "status": "success",
                                                "listings": res.listings_seen, "jobs": len(records),
                                                "detail_pages": res.detail_pages})
                unique, dups = deduplicate(batch_records)
                saved, new = store.upsert_jobs(unique)
                summary.duplicates_removed += dups
                summary.jobs_saved += saved
                summary.new_jobs += new
                summary.pages_visited = browser.pages_visited
                report()
                if summary.status == "stopped":
                    break
        if summary.status == "running":
            summary.status = "completed"
    except Exception as exc:
        log.exception("Crawl aborted")
        summary.status = "failed"
        summary.errors.append({"company": "-", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        summary.seconds = round(time.monotonic() - started, 1)
        store.finish_run(summary.run_id, companies_attempted=summary.companies_attempted,
                         companies_succeeded=summary.companies_succeeded, companies_failed=summary.companies_failed,
                         listings_seen=summary.listings_seen, jobs_saved=summary.jobs_saved, new_jobs=summary.new_jobs,
                         duplicates_removed=summary.duplicates_removed, status=summary.status, errors=summary.errors)
        report()
    return summary
