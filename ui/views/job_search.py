"""Job Search page: search, filters, sorting, pagination and export."""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from src.export import to_csv_bytes, to_json_bytes
from src.job_filter import QUICK_FILTERS, SORT_OPTIONS, JobFilters, apply_filters, sort_jobs
from ui import state
from ui.components import empty_state, job_card, page_header, paginator


def _city(loc: str) -> str:
    return loc.split(",")[0].split("(")[0].replace("Hybrid —", "").replace("Hybrid -", "").strip()


def _reset() -> None:
    st.session_state.filters = JobFilters()
    st.session_state.search_page = 1
    for k in [k for k in st.session_state if str(k).startswith("f_")]:
        del st.session_state[k]


def render() -> None:
    state.show_flash()
    page_header("Job Search", "Search, filter and sort the loaded job records. Filters never trigger a new crawl.")
    jobs = state.get_jobs()
    if jobs.empty:
        empty_state("No job records available", "Switch the dataset in the sidebar or run a crawl on the Collect Jobs page.")
        return
    f: JobFilters = st.session_state.filters
    scores = state.match_scores()

    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1.6, 0.9], vertical_alignment="bottom")
        keyword = c1.text_input("Keywords", value=f.keyword, key="f_keyword",
                                placeholder="All words must match: e.g. python intern bengaluru")
        sort_names = list(SORT_OPTIONS)
        if not scores:
            sort_names.remove("Relevance (match score)")
        default_sort = st.session_state.sort_option if st.session_state.sort_option in sort_names else "Newest first"
        sort_option = c2.selectbox("Sort by", sort_names, index=sort_names.index(default_sort), key="f_sort")
        page_size = c3.selectbox("Per page", [10, 20, 50], index=[10, 20, 50].index(st.session_state.page_size), key="f_pagesize")
        quick = st.pills("Quick filters", list(QUICK_FILTERS), selection_mode="multi", default=f.quick, key="f_quick")

        with st.expander("More filters", expanded=bool(f.locations or f.skills or f.companies or f.employment_types)):
            a, b, c = st.columns(3)
            all_locs = sorted({_city(l) for l in jobs["location"] if l} | {"Remote"})
            locations = a.multiselect("Location", all_locs, default=[l for l in f.locations if l in all_locs], key="f_locations")
            remote_only = a.toggle("Remote / hybrid only", value=f.remote_only, key="f_remote")
            all_skills = sorted({s for lst in jobs["skills"] for s in lst})
            skills = b.multiselect("Skills", all_skills, default=[s for s in f.skills if s in all_skills], key="f_skills")
            skill_mode = b.radio("Skill matching", ["any", "all"], index=0 if f.skill_mode == "any" else 1, horizontal=True,
                                 format_func={"any": "Any selected skill", "all": "All selected skills"}.get, key="f_skillmode")
            companies = c.multiselect("Company", sorted(jobs["company"].unique()), default=f.companies, key="f_companies")
            max_exp = c.select_slider("Maximum experience required (years)", options=[0, 1, 2, 3, 5, 10],
                                      value=f.max_experience if f.max_experience is not None else 10, key="f_maxexp")
            d, e, g = st.columns(3)
            emp = d.multiselect("Employment type", sorted(jobs["employment_type"].unique()), default=f.employment_types, key="f_emp")
            cats = e.multiselect("Category", sorted(jobs["category"].unique()), default=f.categories, key="f_cats")
            sources = g.multiselect("Source", sorted(jobs["source"].unique()), default=f.sources, key="f_sources")
            h1, h2, h3 = st.columns(3)
            fresher_only = h1.toggle("Fresher-friendly only", value=f.fresher_only, key="f_fresher")
            hide_expired = h2.toggle("Hide jobs past their deadline", value=f.hide_expired, key="f_expired")
            h3.button("Reset all filters", on_click=_reset, icon=":material/restart_alt:", width="stretch")

    new_f = replace(f, keyword=keyword, quick=list(quick or []), locations=locations, remote_only=remote_only, skills=skills,
                    skill_mode=skill_mode, companies=companies, max_experience=None if max_exp == 10 else float(max_exp),
                    employment_types=emp, categories=cats, sources=sources, fresher_only=fresher_only, hide_expired=hide_expired)
    if new_f != f or sort_option != st.session_state.sort_option or page_size != st.session_state.page_size:
        st.session_state.search_page = 1
    st.session_state.filters, st.session_state.sort_option, st.session_state.page_size = new_f, sort_option, page_size

    results = apply_filters(jobs, new_f)
    if scores:
        results = results.assign(match_score=results["job_id"].map(scores))
    results = sort_jobs(results, sort_option)

    top = st.columns([3, 1, 1], vertical_alignment="center")
    top[0].markdown(f"**{len(results)}** of {len(jobs)} jobs match" + (" · match scores use your current profile" if scores else ""))
    top[1].download_button("Export CSV", to_csv_bytes(results), "filtered_jobs.csv", "text/csv",
                           icon=":material/download:", width="stretch", disabled=results.empty)
    top[2].download_button("Export JSON", to_json_bytes(results), "filtered_jobs.json", "application/json",
                           icon=":material/data_object:", width="stretch", disabled=results.empty)

    if results.empty:
        empty_state("No jobs match these filters", "Try removing a filter, widening the experience range or clearing the keywords.")
        st.button("Reset filters", on_click=_reset, key="reset_empty")
        return
    page = paginator(len(results), page_size, "search_page", "top")
    tracked = state.get_store().tracked_ids()
    start = (page - 1) * page_size
    for _, job in results.iloc[start:start + page_size].iterrows():
        job_card(job.to_dict(), key=f"search_{job['job_id']}", score=job.get("match_score") if scores else None,
                 tracked=job["job_id"] in tracked)
    paginator(len(results), page_size, "search_page", "bottom")
