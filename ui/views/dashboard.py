"""Home / Dashboard page."""

from __future__ import annotations

import streamlit as st

from src.job_filter import QUICK_FILTERS, JobFilters
from ui import nav, state
from ui.components import data_mode_summary, empty_state, job_card, metric_tile, notice


def _start_search(keyword: str, location: str, quick: list[str]) -> None:
    st.session_state.filters = JobFilters(keyword=keyword.strip(), locations=[location] if location else [], quick=quick)
    st.session_state.search_page = 1
    nav.go("search")


def render() -> None:
    state.show_flash()
    jobs = state.get_jobs()
    catalogue = state.get_catalogue()
    st.markdown(
        '<div class="hero"><h1>AI-Powered Fresher Job Discovery System</h1>'
        '<p>Discover fresher, internship and graduate-trainee roles collected with Playwright, then rank them against '
        'your skills with an explainable TF-IDF recommender.</p></div>', unsafe_allow_html=True)

    with st.form("hero_search", border=True):
        c1, c2, c3 = st.columns([3, 1.6, 1], vertical_alignment="bottom")
        keyword = c1.text_input("Search jobs", placeholder="Job title, company or skill — e.g. data analyst, python, Nimbus")
        locations = sorted({loc.split(",")[0].split("(")[0].replace("Hybrid —", "").strip()
                            for loc in jobs["location"] if loc}) if not jobs.empty else []
        location = c2.selectbox("Location", [""] + locations, format_func=lambda x: x or "Any location")
        submitted = c3.form_submit_button("Search", type="primary", icon=":material/search:", width="stretch")
    if submitted:
        _start_search(keyword, location, [])

    st.caption("Quick filters")
    qcols = st.columns(len(QUICK_FILTERS))
    for col, name in zip(qcols, QUICK_FILTERS):
        count = int(QUICK_FILTERS[name](jobs).sum()) if not jobs.empty else 0
        if col.button(f"{name} ({count})", key=f"quick_{name}", width="stretch"):
            _start_search("", "", [name])

    st.markdown("&nbsp;", unsafe_allow_html=True)
    scores = state.match_scores()
    strong = sum(1 for s in scores.values() if s >= 50)
    tracked = len(state.get_store().tracked_ids())
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_tile("Jobs in loaded dataset", f"{len(jobs):,}", f"{int(jobs['is_fresher_friendly'].sum()) if not jobs.empty else 0} fresher-friendly")
    with m2:
        verified = int((catalogue["verification_status"] == "verified").sum())
        metric_tile("Companies in catalogue", f"{len(catalogue):,}", f"{verified} with a verified URL")
    with m3:
        if scores:
            metric_tile("Strong matches", strong, "relevance score ≥ 50 for your profile")
        else:
            metric_tile("Strong matches", "—", "set a profile to calculate")
    with m4:
        metric_tile("Tracked applications", tracked, "saved in local SQLite")

    st.markdown("Data in use: " + data_mode_summary(jobs), unsafe_allow_html=True)
    if not jobs.empty and (jobs["data_mode"] == "sample").all():
        notice("You are viewing the <b>sample dataset</b>: fictional companies and jobs for an offline demonstration. "
               "Use <b>Collect Jobs (Playwright)</b> to gather demo-crawl or live records.")

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Recent discoveries")
        if jobs.empty:
            empty_state("No jobs loaded", "Run a crawl or switch the dataset in the sidebar.")
        tracked_ids = state.get_store().tracked_ids()
        for _, job in jobs.head(4).iterrows():
            job_card(job.to_dict(), key=f"recent_{job['job_id']}", score=scores.get(job["job_id"]),
                     tracked=job["job_id"] in tracked_ids, snippet_len=140, compact=True)
    with right:
        st.subheader("Recommended for you")
        if not scores:
            empty_state("No profile yet", "Enter your skills to get explainable recommendations.")
            b1, b2 = st.columns(2)
            if b1.button("Create my profile", type="primary", width="stretch"):
                nav.go("recommend")
            if b2.button("Try a demo profile", width="stretch",
                         help="Fills in an example AIML-student profile (Python, ML, SQL…) so you can see scores."):
                st.session_state.profile = state.DEMO_PROFILE
                st.session_state.profile_is_demo = True
                st.rerun()
        else:
            if st.session_state.profile_is_demo:
                st.caption("Using the demo profile (Python, ML, SQL, pandas…). Edit it on AI Recommendations.")
            top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:4]
            by_id = jobs.set_index("job_id")
            for jid, score in top:
                job = by_id.loc[jid].to_dict() | {"job_id": jid}
                job_card(job, key=f"rec_{jid}", score=score, tracked=jid in tracked_ids, snippet_len=140, compact=True)
