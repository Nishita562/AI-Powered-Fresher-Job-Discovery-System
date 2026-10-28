"""Integration test: real Chromium automation against the local demo career pages."""

import pytest

from src.browser_manager import RobotsCache
from src.job_scraper import fixture_targets, run_crawl


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.integration
needs_browser = pytest.mark.skipif(not _chromium_available(), reason="Playwright Chromium not installed")


@needs_browser
def test_fixture_crawl_end_to_end(store):
    summary = run_crawl(fixture_targets(), mode="fixtures", store=store, batch_size=5, max_detail_pages=5)
    assert summary.status == "completed"
    assert summary.companies_succeeded == 5 and summary.companies_failed == 0
    assert summary.duplicates_removed == 1          # featured listing repeated on the Nimbus page
    jobs = store.load_jobs()
    assert len(jobs) == 14
    titles = set(jobs["title"])
    # senior roles are skipped, JavaScript-rendered and Greenhouse/Lever-style layouts are read
    assert not {"Senior Data Engineer", "Engineering Manager", "Principal Research Scientist", "Staff Backend Engineer"} & titles
    assert {"NLP Engineer Intern", "Software Engineer – New Grad", "Business Analyst Intern"} <= titles
    assert set(jobs["data_mode"]) == {"demo_fixture"}
    ml = jobs[jobs["title"] == "Machine Learning Intern"].iloc[0]
    assert ml["work_mode"] == "Remote" and ml["salary"] == "₹20,000 per month"
    runs = store.load_runs()
    assert runs.iloc[0]["status"] == "completed"


@needs_browser
def test_stop_request_is_honoured(store):
    summary = run_crawl(fixture_targets(), mode="fixtures", store=store, should_stop=lambda: True)
    assert summary.status == "stopped" and summary.companies_attempted == 0


def test_robots_cache_allows_local_files():
    robots = RobotsCache("test-agent")
    assert robots.allowed("file:///tmp/page.html")
    assert robots.crawl_delay("file:///tmp/page.html") == 0.0
