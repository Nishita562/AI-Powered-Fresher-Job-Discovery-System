"""Settings & About: dataset mode, refresh, data sources, architecture, usage, limitations and troubleshooting."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from src.data_loader import DATASET_CHOICES, load_sample_jobs
from src.recommendation import CandidateProfile, JobRecommender
from ui import state
from ui.components import page_header

ARCHITECTURE_DOT = """
digraph G {
  rankdir=TB; node [shape=box, style="rounded,filled", fillcolor="#EEF2FF", color="#4F46E5", fontname="Helvetica", fontsize=11];
  edge [color="#64748B", fontname="Helvetica", fontsize=9];
  subgraph cluster_collect { label="Collection (Playwright, background process)"; color="#CBD5E1";
    cat [label="Company catalogue\\ncompanies.csv (518)"]; adapters [label="Adapters\\nGreenhouse · Lever · Generic"];
    browser [label="BrowserManager\\nrobots.txt · delay · retries"]; }
  subgraph cluster_proc { label="Processing"; color="#CBD5E1";
    extract [label="Extraction & normalisation\\nexperience · salary · deadline · skills"]; dedup [label="De-duplication\\nURL hash + composite key"]; }
  db [label="SQLite\\njobs · applications · crawl_runs", fillcolor="#ECFDF5", color="#0D9488"];
  sample [label="Sample dataset\\n(fictional, offline)", fillcolor="#FFFBEB", color="#B45309"];
  subgraph cluster_ai { label="AI / ML"; color="#CBD5E1";
    tfidf [label="TF-IDF vectoriser\\n+ cosine similarity"]; score [label="Explainable score\\nskills · preference · eligibility"];
    kmeans [label="K-Means clusters"]; resume [label="Resume parser\\n(PDF/DOCX, in memory)"]; }
  ui [label="Streamlit UI\\n8 pages", fillcolor="#E0E7FF"];
  cat -> adapters -> browser -> extract -> dedup -> db; db -> ui; sample -> ui;
  db -> tfidf; sample -> tfidf; resume -> score; tfidf -> score -> ui; tfidf -> kmeans -> ui;
}
"""


def _worked_example() -> None:
    sample = load_sample_jobs()
    picks = []
    for title in ["Machine Learning Engineer Intern", "Junior Data Analyst", "Senior Data Scientist"]:
        row = sample[sample["title"] == title].head(1)
        if not row.empty:
            picks.append(row)
    if not picks:
        st.caption("Sample jobs needed for the worked example are not available.")
        return
    jobs = pd.concat(picks, ignore_index=True)
    profile = CandidateProfile(skills=["python", "machine learning", "pandas", "sql"], preferred_roles=["Machine Learning Engineer"],
                               preferred_locations=["Bengaluru"], experience_years=0)
    recs = JobRecommender(jobs).score_all(profile)
    st.markdown("Profile: skills **python, machine learning, pandas, sql** · preferred role **Machine Learning Engineer** · "
                "location **Bengaluru** · experience **0 years**. The model is fitted on just these three sample jobs, "
                "so the numbers below are computed live by the same code the app uses.")
    by_id = jobs.set_index("job_id")
    st.dataframe(pd.DataFrame([{
        "job (sample)": by_id.loc[r.job_id, "title"], "location": by_id.loc[r.job_id, "location"],
        "cosine": r.text_similarity, "S_text (relative)": r.text_relative, "S_skill": r.skill_score, "S_pref": r.preference_score, "eligibility": r.eligibility,
        "score": r.score, "matched": ", ".join(r.matched_skills)} for r in recs]), hide_index=True, width="stretch")


def render() -> None:
    page_header("Settings & About", "Configuration, data sources, architecture and help.")
    tab_set, tab_about, tab_help = st.tabs(["Settings", "About the project", "Help & troubleshooting"])

    with tab_set:
        st.markdown("**Dataset mode**")
        choice = st.radio("Records used by every page", list(DATASET_CHOICES), format_func=DATASET_CHOICES.get,
                          index=list(DATASET_CHOICES).index(st.session_state.dataset_choice), horizontal=True)
        if choice != st.session_state.dataset_choice:
            st.session_state.dataset_choice = choice
            st.session_state.search_page = 1
            st.session_state.pop("score_cache", None)
            st.rerun()
        if st.button("Refresh data from disk", icon=":material/refresh:"):
            state.refresh_data()
            st.success("Caches cleared — data and the TF-IDF model will be reloaded.")
        st.markdown("**Search defaults**")
        c1, c2 = st.columns(2)
        st.session_state.page_size = c1.selectbox("Results per page", settings.PAGE_SIZE_OPTIONS,
                                                  index=settings.PAGE_SIZE_OPTIONS.index(st.session_state.page_size))
        f = st.session_state.filters
        f.hide_expired = c2.toggle("Hide jobs past their deadline by default", value=f.hide_expired)
        st.markdown("**Data sources in the database**")
        counts = state.get_store().count_jobs()
        st.dataframe(pd.DataFrame([{"data mode": m, "meaning": settings.DATA_MODE_LABELS[m],
                                    "records": f"{counts.get(m, 0)} in SQLite"} for m in settings.DATA_MODE_LABELS]
                                  + [{"data mode": "sample (file)", "meaning": "data/sample_jobs.json — fictional",
                                      "records": f"{len(load_sample_jobs())} in file"}]),
                     hide_index=True, width="stretch")
        with st.expander("Delete collected records"):
            mode = st.selectbox("Data to delete", ["demo_fixture", "live"])
            confirm = st.checkbox(f"Yes, permanently delete all '{mode}' jobs from database/jobs.db")
            if st.button("Delete", disabled=not confirm, type="secondary"):
                n = state.get_store().delete_jobs(mode)
                state.refresh_data()
                st.success(f"Deleted {n} records.")
        st.markdown("**Current crawler settings** (edit `config/settings.py` or `.env`)")
        st.json({"HEADLESS": settings.HEADLESS, "NAV_TIMEOUT_MS": settings.NAV_TIMEOUT_MS, "MAX_RETRIES": settings.MAX_RETRIES,
                 "REQUEST_DELAY_SECONDS": settings.REQUEST_DELAY_SECONDS, "BATCH_SIZE": settings.BATCH_SIZE,
                 "MAX_DETAIL_PAGES_PER_COMPANY": settings.MAX_DETAIL_PAGES_PER_COMPANY,
                 "RESPECT_ROBOTS_TXT": settings.RESPECT_ROBOTS_TXT, "USER_AGENT": settings.USER_AGENT,
                 "weights (text, skill, preference)": [settings.WEIGHT_TEXT_SIMILARITY, settings.WEIGHT_SKILL_MATCH,
                                                       settings.WEIGHT_PREFERENCE],
                 "eligibility factors": settings.ELIGIBILITY_FACTORS}, expanded=False)

    with tab_about:
        st.markdown("""
**AI-Powered Fresher Job Discovery System Using Playwright** — a B.Tech AIML minor project (AIML-451).

The system collects fresher and entry-level job listings with browser automation, extracts structured fields, removes
duplicates, stores them in SQLite and recommends jobs with an explainable text-similarity model.

| Part | What it really does | Technique |
|---|---|---|
| Browser automation | Opens career pages / public job boards, waits for JavaScript, reads listings | Playwright (Chromium) |
| Information extraction | Experience, salary, deadline, employment type, eligibility, work mode | Regular-expression rules |
| Skill extraction | Finds skills in job text and resumes | Dictionary of 123 skills with aliases |
| Recommendation | Ranks jobs for a candidate profile | TF-IDF + cosine similarity + weighted rules |
| Grouping | Groups similar job descriptions | K-Means (unsupervised) + silhouette |
| Storage | Jobs, tracker, crawl history | SQLite, CSV, JSON |

The recommender is **not trained on hiring outcomes** — TF-IDF is a text-vectorisation method, so no accuracy figure is claimed.
""")
        st.graphviz_chart(ARCHITECTURE_DOT, width="stretch")
        st.markdown("##### Worked example of the relevance score")
        _worked_example()
        st.markdown("""
##### Limitations
* Website layouts change; adapters may need selector updates in `config/sources.json`.
* Many company sites block automated browsers (HTTP 403/429, CAPTCHAs). These are skipped, never bypassed.
* Rule-based extraction can miss unusual phrasing; missing fields are left empty rather than guessed.
* Keyword/TF-IDF matching does not understand synonyms deeply (e.g. "ML" vs "statistical learning" may not match).
* The sample dataset is fictional; only `live` records come from real public job boards.

##### Privacy
Resumes are processed in memory and never stored. Tracker data stays in `database/jobs.db` on this computer.
No analytics or telemetry are sent (Streamlit usage statistics are disabled in `.streamlit/config.toml`).
""")

    with tab_help:
        st.markdown("""
##### How to use
1. **Dashboard** — search or click a quick filter.
2. **Job Search** — refine with filters, sort, open *Details*, *Save* or open the original link.
3. **AI Recommendations** — enter skills (or extract them from a resume) and press *Get recommendations*.
4. **Company Explorer** — browse the 518-company catalogue and send companies to the crawler.
5. **Collect Jobs** — run the offline demo crawl or a small live crawl; progress updates every 2 seconds.
6. **Application Tracker** — change statuses and notes, then *Save changes*.

##### Troubleshooting
| Problem | Fix |
|---|---|
| `Executable doesn't exist … chromium` | `python -m playwright install chromium` |
| Port 8501 already in use | `streamlit run app.py --server.port 8502` or close the other app |
| Live crawl finds 0 jobs | The site may have changed or blocked access — see the error list; use the demo crawl |
| `ModuleNotFoundError` | Activate the environment: `conda activate fresherjobs` (or `source .venv/bin/activate`) |
| Old data showing | Settings → *Refresh data from disk* |
| Resume gives "very little text" | It is probably a scanned image; type your skills instead |
""")
