"""Collect Jobs: start/stop Playwright crawls in a background process and watch progress."""

from __future__ import annotations

import json

import streamlit as st

from config import settings
from src import crawl_runner
from src.company_catalog import crawlable
from src.job_scraper import fixture_targets
from ui import nav, state
from ui.components import fmt_datetime, notice, page_header


@st.fragment(run_every=2)
def _status_panel() -> None:
    status = crawl_runner.read_status()
    running = crawl_runner.is_running()
    if not status:
        st.caption("No crawl has been started yet.")
        return
    total, done = status.get("total") or 0, status.get("done") or 0
    s = status.get("state", "")
    if running:
        st.progress(min(done / total, 1.0) if total else 0.0,
                    text=f"Crawling {status.get('current_company') or '…'} — {done}/{total or '?'} companies")
    elif s == "running":  # process died without writing a final state
        st.warning("The crawl process is no longer running. Check logs/crawl_subprocess.log for details.")
    else:
        icon = {"completed": "✅", "stopped": "⏹️", "failed": "❌"}.get(s, "ℹ️")
        st.markdown(f"{icon} Last crawl **{s}** ({status.get('mode')}) — finished {fmt_datetime(status.get('finished_at', ''))}"
                    f" in {status.get('seconds', '?')} s")
        if st.session_state.get("crawl_was_running"):
            # The crawl just finished: reload data everywhere and re-enable the start buttons.
            st.session_state.crawl_was_running = False
            state.refresh_data()
            st.rerun(scope="app")
    c = st.columns(5)
    c[0].metric("Companies OK", f"{status.get('companies_succeeded', 0)}/{status.get('companies_attempted', 0)}")
    c[1].metric("Listings seen", status.get("listings_seen", 0))
    c[2].metric("Jobs saved", status.get("jobs_saved", 0))
    c[3].metric("New jobs", status.get("new_jobs", 0))
    c[4].metric("Duplicates removed", status.get("duplicates_removed", 0))
    if status.get("errors"):
        with st.expander(f"{len(status['errors'])} company error(s) — skipped, not retried aggressively"):
            for e in status["errors"]:
                st.markdown(f"- **{e['company']}**: {e['error']}")
    if status.get("per_company") and not running:
        st.dataframe(status["per_company"], width="stretch", hide_index=True)
    if running:
        st.session_state.crawl_was_running = True
        if st.button("Stop crawl", icon=":material/stop_circle:", type="secondary"):
            crawl_runner.stop_crawl()
            st.toast("Stop requested — the crawler will finish the current page, save and close the browser.")


def render() -> None:
    page_header("Collect Jobs with Playwright",
                "Browser automation runs in a separate process, so the dashboard stays responsive while it works.")
    running = crawl_runner.is_running()
    tab_demo, tab_live = st.tabs(["Offline demo crawl", "Live crawl (public job boards)"])
    with tab_demo:
        st.markdown("Crawls five **local demo career pages** (fictional companies) with real Chromium automation: card, table, "
                    "JavaScript-rendered, Greenhouse-style and Lever-style layouts. Works without internet — ideal for the "
                    "project demonstration.")
        targets = fixture_targets()
        st.dataframe([{"company": t.company_name, "adapter": t.platform, "page": t.url.rsplit("/", 1)[-1]} for t in targets],
                     hide_index=True, width="stretch")
        headed = st.checkbox("Show the browser window while crawling (headed mode)", key="demo_headed")
        if st.button("Start demo crawl", type="primary", disabled=running, icon=":material/play_arrow:"):
            try:
                crawl_runner.start_crawl("fixtures", headed=headed)
                st.toast("Demo crawl started")
            except Exception as exc:
                st.error(str(exc))
            st.rerun()
    with tab_live:
        notice("Live mode visits only <b>public</b> pages that robots.txt allows, one page at a time with a "
               f"{settings.REQUEST_DELAY_SECONDS:g}s delay. Logins, CAPTCHAs and bot protection are never bypassed — such "
               "pages are skipped and reported. Results depend on the websites at the moment you run it.")
        cat = crawlable(state.get_catalogue())
        boards = cat[cat["ats_board_token"] != ""]
        others = cat[cat["ats_board_token"] == ""]
        options = boards["company_name"].tolist() + others["company_name"].tolist()
        incoming = [c for c in st.session_state.pop("crawl_preselect", []) if c in options]
        if incoming:  # companies sent from the Company Explorer replace the current selection
            st.session_state.live_companies = incoming
        elif "live_companies" not in st.session_state:
            st.session_state.live_companies = boards["company_name"].head(2).tolist()
        picked = st.multiselect("Companies to crawl", options, key="live_companies", max_selections=settings.BATCH_SIZE,
                                help="Companies with public Greenhouse/Lever boards are listed first; others use the generic "
                                     "career-page adapter, which is less reliable.")
        max_details = st.slider("Detail pages to open per company", 1, 15, 5,
                                help="Only listings with fresher or entry-level titles are opened first.")
        headed_live = st.checkbox("Show the browser window", key="live_headed")
        if st.button("Start live crawl", type="primary", disabled=running or not picked, icon=":material/public:"):
            try:
                crawl_runner.start_crawl("live", companies=picked, max_details=max_details, headed=headed_live)
                st.toast("Live crawl started")
            except Exception as exc:
                st.error(str(exc))
            st.rerun()

    st.subheader("Crawl status")
    _status_panel()
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("View collected jobs", icon=":material/search:"):
        st.session_state.dataset_choice = "collected"
        state.refresh_data()
        nav.go("search")
    with c2.expander("Command-line equivalent"):
        st.code("python -m src.cli crawl --mode fixtures\n"
                "python -m src.cli crawl --mode live --companies \"Groww,Paytm\" --max-details 5", language="bash")
    runs = state.get_store().load_runs(10)
    if not runs.empty:
        st.markdown("**Recent crawl runs**")
        runs["errors"] = runs["errors"].map(lambda e: len(json.loads(e)) if e else 0)
        st.dataframe(runs, hide_index=True, width="stretch")
