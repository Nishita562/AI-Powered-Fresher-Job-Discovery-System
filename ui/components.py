"""Reusable UI pieces: badges, metric tiles, job cards and the job-details dialog.

All scraped text is HTML-escaped before it is placed inside custom markup,
so content from a website can never inject HTML or scripts into the app.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import settings
from src.text_utils import truncate
from ui import state

MODE_BADGE = {
    "live": ("LIVE", "b-live", "Collected from a public job board"),
    "sample": ("SAMPLE", "b-sample", "Fictional sample record for offline demo"),
    "demo_fixture": ("DEMO CRAWL", "b-demo", "Collected by Playwright from a local demo page"),
}
ELIGIBILITY_BADGE = {
    "eligible": ("Experience fits", "b-good"),
    "unknown": ("Experience not stated", "b-warn"),
    "not_eligible": ("Needs more experience", "b-bad"),
}


def esc(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return html.escape(str(value))


def badge(text: str, css: str = "b-neutral", title: str = "") -> str:
    return f'<span class="badge {css}" title="{esc(title)}">{esc(text)}</span>'


def mode_badge(mode: str) -> str:
    label, css, tip = MODE_BADGE.get(mode, (mode.upper(), "b-neutral", ""))
    return badge(label, css, tip)


def chips(items, css: str = "chip", limit: int = 12) -> str:
    items = list(items or [])
    extra = f'<span class="chip">+{len(items) - limit}</span>' if len(items) > limit else ""
    return "".join(f'<span class="{css}">{esc(i)}</span>' for i in items[:limit]) + extra


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="page-title">{esc(title)}</div><div class="page-sub">{esc(subtitle)}</div>', unsafe_allow_html=True)


def metric_tile(label: str, value, hint: str = "") -> None:
    st.markdown(f'<div class="metric-tile"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div>'
                f'<div class="hint">{esc(hint)}</div></div>', unsafe_allow_html=True)


def notice(text: str, kind: str = "warn") -> None:
    st.markdown(f'<div class="notice {"info" if kind == "info" else ""}">{text}</div>', unsafe_allow_html=True)


def empty_state(title: str, hint: str = "") -> None:
    st.markdown(f'<div class="empty-state"><div class="big">{esc(title)}</div><div>{esc(hint)}</div></div>', unsafe_allow_html=True)


def _local(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return dt.astimezone() if dt.tzinfo else dt  # stored in UTC, shown in the computer's time zone


def fmt_date(value: str) -> str:
    if not value:
        return ""
    dt = _local(value)
    return dt.strftime("%d %b %Y") if dt else str(value)[:10]


def fmt_datetime(value: str) -> str:
    dt = _local(value) if value else None
    return dt.strftime("%d %b %Y, %H:%M") if dt else (value or "")


def experience_label(job) -> str:
    lo, hi = job.get("min_experience_years"), job.get("max_experience_years")
    if lo is None or pd.isna(lo):
        return "Experience not specified"
    if hi is not None and not pd.isna(hi) and hi != lo:
        return f"{lo:g}–{hi:g} yrs"
    return "Fresher (0 yrs)" if lo == 0 else f"{lo:g}+ yrs"


def data_mode_summary(df: pd.DataFrame) -> str:
    if df.empty:
        return badge("No data loaded", "b-neutral")
    counts = df["data_mode"].value_counts()
    return " ".join(f'{mode_badge(m)}<span class="small-muted">{counts[m]} jobs</span>&nbsp;&nbsp;' for m in counts.index)


# ------------------------------------------------------------------ links
def fixture_path(url: str) -> Path | None:
    """Return the local fixture file for a file:// URL, only if it lives inside the fixture folder."""
    if not url.startswith("file://"):
        return None
    path = Path(unquote(urlsplit(url).path)).resolve()
    root = settings.FIXTURE_DIR.resolve()
    return path if root in path.parents and path.is_file() else None


def render_link_button(job: dict, key: str) -> None:
    url = job.get("apply_url") or ""
    mode = job.get("data_mode")
    if mode == "demo_fixture":
        if fixture_path(url) and st.button("Demo page", key=f"pv_{key}", icon=":material/web:", width="stretch",
                                           help="Show the local demo career page this record was crawled from"):
            preview_fixture(url)
        return
    if not url.startswith(("http://", "https://")):
        st.caption("No application link published")
        return
    label = "Sample link" if mode == "sample" else "Apply ↗"
    st.link_button(label, url, width="stretch", type="primary" if mode == "live" else "secondary",
                   help="Sample records link to the reserved example.com domain" if mode == "sample" else url)


@st.dialog("Demo career page (local fixture)", width="large")
def preview_fixture(url: str) -> None:
    path = fixture_path(url)
    if not path:
        st.error("Fixture page not found.")
        return
    st.caption(f"Local file: data/fixtures/career_pages/{path.name} — the page Playwright crawled in demo mode.")
    components.html(path.read_text(encoding="utf-8"), height=520, scrolling=True)


# ------------------------------------------------------------------ job cards
def save_job(job: dict) -> None:
    try:
        state.get_store().save_application(job, "Saved")
        state.flash(f"Saved “{job['title']}” to your application tracker.")
    except Exception as exc:  # surface DB problems clearly
        state.flash(f"Could not save the job: {exc}", "error")


def score_html(score: float | None, caption: str = "match score") -> str:
    if score is None or pd.isna(score):
        return ""
    return f'<div class="score-box"><div class="num">{score:.0f}</div><div class="cap">{esc(caption)}</div></div>'


def _card_body(job: dict, snippet_len: int) -> str:
    meta = " · ".join(x for x in [esc(job.get("company")), esc(job.get("location") or "Location not stated"),
                                  esc(job.get("work_mode")) if job.get("work_mode") not in ("", "Unknown") else ""] if x)
    badges = (mode_badge(job.get("data_mode", "")) + badge(job.get("employment_type") or "Not specified")
              + badge(experience_label(job)) + badge(job.get("category") or "Other"))
    if job.get("is_fresher_friendly"):
        badges += badge("Fresher-friendly", "b-good")
    if job.get("deadline"):
        badges += badge(f"Apply by {fmt_date(job['deadline'])}", "b-warn")
    collected = (f'<div class="small-muted">Collected {fmt_date(job.get("discovered_at"))} from {esc(job.get("source"))}</div>'
                 if job.get("data_mode") == "live" else "")
    return (f'<div class="job-title">{esc(job.get("title"))}</div><div class="job-meta">{meta}</div>{badges}'
            f'<div>{chips(job.get("skills"), limit=8)}</div>'
            f'<div class="job-snippet">{esc(truncate(job.get("description", ""), snippet_len))}</div>{collected}')


def _card_buttons(job: dict, key: str, tracked: bool) -> None:
    if st.button("Details", key=f"d_{key}", icon=":material/description:", width="stretch"):
        job_details(job)
    if tracked:
        st.button("Saved", key=f"s_{key}", icon=":material/bookmark_added:", disabled=True, width="stretch")
    else:
        st.button("Save", key=f"s_{key}", icon=":material/bookmark_add:", width="stretch", on_click=save_job, args=(job,))


def job_card(job: dict, key: str, score: float | None = None, tracked: bool = False, snippet_len: int = 220,
             compact: bool = False) -> None:
    """A job as a bordered card. ``compact`` puts the buttons in a row underneath (for narrow columns)."""
    has_score = score is not None and not pd.isna(score)
    with st.container(border=True):
        if compact:
            body, sc = st.columns([4, 1]) if has_score else (st.container(), None)
            body.markdown(_card_body(job, snippet_len), unsafe_allow_html=True)
            if sc is not None:
                sc.markdown(score_html(score), unsafe_allow_html=True)
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("Details", key=f"d_{key}", width="stretch"):
                    job_details(job)
            with b2:
                st.button("Saved" if tracked else "Save", key=f"s_{key}", disabled=tracked, width="stretch",
                          on_click=None if tracked else save_job, args=None if tracked else (job,))
            with b3:
                render_link_button(job, key)
            return
        left, right = st.columns([5, 1.45], vertical_alignment="top")
        with left:
            st.markdown(_card_body(job, snippet_len), unsafe_allow_html=True)
        with right:
            if has_score:
                st.markdown(score_html(score), unsafe_allow_html=True)
            _card_buttons(job, key, tracked)
            render_link_button(job, key)


def component_bar(label: str, value: float | None, weight: float, note: str = "") -> str:
    """One labelled progress bar of the score breakdown, e.g. 'Text · 50%   0.43'."""
    shown = "not scored" if value is None else f"{value:.2f}{note}"
    width = 0 if value is None else min(value, 1) * 100
    return (f'<div class="bar-label"><span>{esc(label)} · {weight:.0%}</span><span>{esc(shown)}</span></div>'
            f'<div class="bar"><span style="width:{width:.0f}%"></span></div>')


def recommendation_breakdown(rec, with_badge: bool = True) -> str:
    elig_label, elig_css = ELIGIBILITY_BADGE[rec.eligibility]
    return (component_bar("Text", rec.text_relative, settings.WEIGHT_TEXT_SIMILARITY, f" (cos {rec.text_similarity:.2f})")
            + component_bar("Skills", rec.skill_score, settings.WEIGHT_SKILL_MATCH)
            + component_bar("Preference", rec.preference_score, settings.WEIGHT_PREFERENCE)
            + (badge(elig_label, elig_css) if with_badge else ""))


@st.dialog("Job details", width="large")
def job_details(job: dict) -> None:
    st.markdown(f'<div class="job-title" style="font-size:1.3rem">{esc(job.get("title"))}</div>'
                f'<div class="job-meta">{esc(job.get("company"))} · {esc(job.get("location") or "Location not stated")}</div>'
                f'{mode_badge(job.get("data_mode", ""))}{badge(job.get("category") or "Other")}', unsafe_allow_html=True)
    if job.get("data_mode") == "sample":
        st.caption("Sample record: the company and job are fictional and exist only for the offline demonstration.")
    fields = {
        "Work mode": job.get("work_mode") or "Unknown",
        "Employment type": job.get("employment_type") or "Not specified",
        "Experience": job.get("experience_text") or experience_label(job),
        "Salary / stipend": job.get("salary") or "Not published",
        "Application deadline": fmt_date(job.get("deadline")) or "Not published",
        "Eligibility": job.get("eligibility") or "Not stated",
        "Source": job.get("source") or "",
        "Discovered": fmt_date(job.get("discovered_at")),
    }
    c1, c2 = st.columns(2)
    for i, (k, v) in enumerate(fields.items()):
        (c1 if i % 2 == 0 else c2).markdown(f"**{k}:** {esc(v)}", unsafe_allow_html=True)
    st.markdown("**Skills found:** " + (chips(job.get("skills"), limit=30) or "none detected"), unsafe_allow_html=True)

    rec = state.recommendation_for(job["job_id"])
    if rec is not None:
        st.markdown("##### Why this job matches your profile")
        st.markdown(score_html(rec.score, "relevance score (0–100, not a hiring probability)") + "<br>"
                    + recommendation_breakdown(rec), unsafe_allow_html=True)
        if rec.matched_skills:
            st.markdown('<span class="small-muted">Matched skills:</span> ' + chips(rec.matched_skills, "chip chip-match", 20),
                        unsafe_allow_html=True)
        if rec.missing_skills:
            st.markdown('<span class="small-muted">Skills you have not listed:</span> ' + chips(rec.missing_skills, "chip chip-miss", 20),
                        unsafe_allow_html=True)
        st.caption(rec.explanation)

    st.markdown("##### Description")
    with st.container(height=260, border=True):
        st.markdown(f'<div style="white-space:pre-wrap;font-size:0.92rem">{esc(job.get("description") or "No description captured.")}</div>',
                    unsafe_allow_html=True)
    recommender = state.get_recommender()
    terms = recommender.top_terms(job["job_id"], 8)
    if terms:
        st.markdown("**Top TF-IDF keywords:** " + chips(terms), unsafe_allow_html=True)
    similar = recommender.similar_jobs(job["job_id"], 3)
    if similar:
        jobs = state.get_jobs().set_index("job_id")
        lines = [f"- {esc(jobs.loc[jid, 'title'])} — {esc(jobs.loc[jid, 'company'])} (cosine {sim:.2f})"
                 for jid, sim in similar if jid in jobs.index]
        st.markdown("**Similar jobs (content-based):**\n" + "\n".join(lines), unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        render_link_button(job, f"dlg_{job['job_id']}")
    with b2:
        if job["job_id"] in state.get_store().tracked_ids():
            st.button("Already in tracker", disabled=True, width="stretch", key=f"dlg_saved_{job['job_id']}")
        elif st.button("Save to tracker", width="stretch", icon=":material/bookmark_add:", key=f"dlg_save_{job['job_id']}"):
            save_job(job)
            st.rerun()


def _step_page(state_key: str, delta: int) -> None:
    st.session_state[state_key] = st.session_state.get(state_key, 1) + delta


def current_page(total_items: int, page_size: int, state_key: str) -> tuple[int, int]:
    pages = max(1, -(-total_items // page_size))
    page = min(max(1, st.session_state.get(state_key, 1)), pages)
    st.session_state[state_key] = page
    return page, pages


def paginator(total_items: int, page_size: int, state_key: str, key: str) -> int:
    """Previous/next pagination using callbacks (so several paginators on one page stay in sync)."""
    page, pages = current_page(total_items, page_size, state_key)
    c1, c2, c3 = st.columns([1, 2, 1], vertical_alignment="center")
    c1.button("← Previous", key=f"prev_{key}", disabled=page <= 1, width="stretch", on_click=_step_page, args=(state_key, -1))
    c3.button("Next →", key=f"next_{key}", disabled=page >= pages, width="stretch", on_click=_step_page, args=(state_key, 1))
    c2.markdown(f'<div style="text-align:center" class="small-muted">Page {page} of {pages} · {total_items} results</div>',
                unsafe_allow_html=True)
    return page
