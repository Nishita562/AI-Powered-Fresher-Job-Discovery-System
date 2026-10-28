"""Company Explorer: browse, search and filter the ~500-company catalogue."""

from __future__ import annotations

import streamlit as st

from config import settings
from src.company_catalog import catalogue_stats, crawlable, search_catalogue
from ui import nav, state
from ui.components import current_page, empty_state, metric_tile, notice, page_header, paginator

STATUS_LABELS = {"verified": "Verified (URL reachable)", "unverified": "Unverified", "missing": "Missing URL"}


def render() -> None:
    page_header("Company Explorer", "A data-driven directory of employers and their career pages (data/companies.csv).")
    cat = state.get_catalogue()
    jobs = state.get_jobs()
    stats = catalogue_stats(cat)
    m = st.columns(5)
    with m[0]:
        metric_tile("Companies", stats["total"], f"{len(stats['by_industry'])} industries")
    with m[1]:
        metric_tile("Verified URLs", stats["by_status"].get("verified", 0), "responded when last checked")
    with m[2]:
        metric_tile("Unverified", stats["by_status"].get("unverified", 0), "blocked, timed out or unchecked")
    with m[3]:
        metric_tile("Missing URL", stats["by_status"].get("missing", 0), "no official URL known")
    with m[4]:
        metric_tile("Public job boards", stats["with_public_board"], "Greenhouse / Lever, crawlable")
    last = sorted(d for d in cat["last_checked"].unique() if d)
    notice("This catalogue lists companies and official URLs; it does <b>not</b> mean a company currently has a vacancy. "
           "Openings appear only when a crawl actually collects a listing. “Verified” means the URL responded on "
           f"{last[-1] if last else 'the last check'}; homepage URLs are used where an exact careers path could not be confirmed.")

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.2, 2, 1.4, 1.4])
        query = c1.text_input("Search company or industry", key="co_query", placeholder="e.g. Infosys, fintech")
        industries = c2.multiselect("Industry", sorted(cat["industry"].unique()), key="co_ind")
        statuses = c3.multiselect("URL status", list(STATUS_LABELS), format_func=STATUS_LABELS.get, key="co_status")
        url_types = c4.multiselect("URL type", sorted(cat["url_type"].unique()), key="co_type")
        only_boards = st.toggle("Only companies with a public job board (Greenhouse / Lever)", key="co_boards")
    filtered = search_catalogue(cat, query, industries, statuses, url_types, ["greenhouse", "lever"] if only_boards else None)
    signature = (query, tuple(industries), tuple(statuses), tuple(url_types), only_boards)
    if st.session_state.get("co_sig") != signature:
        st.session_state.co_sig, st.session_state.company_page = signature, 1

    if filtered.empty:
        empty_state("No companies match", "Clear the search box or filters.")
        return
    page_size = 25
    page, _ = current_page(len(filtered), page_size, "company_page")
    view = filtered.iloc[(page - 1) * page_size: page * page_size].copy()
    counts = jobs["company"].value_counts() if not jobs.empty else {}
    view["collected_jobs"] = view["company_name"].map(lambda n: int(counts.get(n, 0)) if len(counts) else 0)
    view["board"] = view.apply(lambda r: f"{r['ats_platform']}:{r['ats_board_token']}" if r["ats_board_token"] else "", axis=1)
    st.dataframe(
        view[["company_id", "company_name", "industry", "headquarters", "career_url", "url_type", "verification_status",
              "verification_detail", "board", "collected_jobs"]],
        hide_index=True, width="stretch", height=min(38 * len(view) + 40, 720),
        column_config={
            "company_id": st.column_config.TextColumn("ID", width="small"),
            "company_name": st.column_config.TextColumn("Company"),
            "career_url": st.column_config.LinkColumn("Career / official URL", display_text=r"https?://(?:www\.)?([^/]+).*"),
            "url_type": st.column_config.TextColumn("URL type", width="small"),
            "verification_status": st.column_config.TextColumn("Status", width="small"),
            "verification_detail": st.column_config.TextColumn("Check result"),
            "board": st.column_config.TextColumn("Public board"),
            "collected_jobs": st.column_config.NumberColumn("Jobs collected", help="Listings in the loaded dataset", width="small"),
        },
    )
    paginator(len(filtered), page_size, "company_page", "companies")
    st.download_button("Download filtered catalogue (CSV)", filtered.to_csv(index=False).encode(), "companies_filtered.csv",
                       "text/csv", icon=":material/download:")

    st.divider()
    st.markdown("**Crawl a company from the catalogue**")
    able = crawlable(filtered)
    boards = able[able["ats_board_token"] != ""]
    if able.empty:
        st.caption("None of the filtered companies has a crawlable public board or careers-page URL.")
        return
    options = boards["company_name"].tolist() + [n for n in able["company_name"] if n not in set(boards["company_name"])]
    pick = st.multiselect("Select companies (public boards first)", options, max_selections=settings.BATCH_SIZE,
                          help=f"At most {settings.BATCH_SIZE} per run — the crawler works in small polite batches.")
    if st.button("Open in Collect Jobs", disabled=not pick, icon=":material/robot_2:"):
        st.session_state.crawl_preselect = pick
        nav.go("discover")
