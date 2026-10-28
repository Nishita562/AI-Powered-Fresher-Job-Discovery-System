"""Analytics: interactive Plotly charts computed from the records actually loaded."""

from __future__ import annotations

from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from src.clustering import cluster_jobs
from ui import state
from ui.components import data_mode_summary, empty_state, page_header
from ui.theme import CHART_COLORS

LAYOUT = dict(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10), height=360)


def _bar(df: pd.DataFrame, x: str, y: str, title: str, horizontal: bool = False, color: str | None = None):
    fig = px.bar(df, x=y if horizontal else x, y=x if horizontal else y, orientation="h" if horizontal else "v",
                 title=title, color=color, color_discrete_sequence=CHART_COLORS)
    fig.update_layout(**LAYOUT, showlegend=bool(color), xaxis_title="", yaxis_title="")
    if horizontal:
        fig.update_yaxes(autorange="reversed")
    return fig


def _city(loc: str) -> str:
    if not loc:
        return "Not stated"
    if "remote" in loc.lower():
        return "Remote"
    return loc.split(",")[0].split("(")[0].replace("Hybrid —", "").replace("Hybrid -", "").strip()


@st.cache_data(show_spinner="Clustering job descriptions with K-Means…")
def _clusters(signature: tuple, choice: str):
    jobs = state._jobs(choice, signature)
    res = cluster_jobs(jobs)
    if res is None:
        return None
    return {"labels": res.labels.tolist(), "k": res.k, "silhouette": res.silhouette, "top_terms": res.top_terms,
            "silhouette_by_k": res.silhouette_by_k}


def render() -> None:
    page_header("Analytics", "Every chart is calculated live from the loaded records — nothing is hard-coded.")
    jobs = state.get_jobs()
    if jobs.empty:
        empty_state("No data to analyse", "Load a dataset first.")
        return
    st.markdown(f"Analysing **{len(jobs)} jobs** · " + data_mode_summary(jobs), unsafe_allow_html=True)

    tab_jobs, tab_skills, tab_ml, tab_cat = st.tabs(["Jobs", "Skills & matching", "Job clusters (K-Means)", "Catalogue & tracker"])
    with tab_jobs:
        c1, c2 = st.columns(2)
        cat = jobs["category"].value_counts().reset_index()
        cat.columns = ["category", "jobs"]
        c1.plotly_chart(_bar(cat, "category", "jobs", "Jobs by category", horizontal=True), width="stretch")
        loc = jobs["location"].map(_city).value_counts().head(12).reset_index()
        loc.columns = ["location", "jobs"]
        c2.plotly_chart(_bar(loc, "location", "jobs", "Jobs by location (top 12)", horizontal=True), width="stretch")
        c3, c4 = st.columns(2)
        comp = jobs["company"].value_counts().head(15).reset_index()
        comp.columns = ["company", "jobs"]
        c3.plotly_chart(_bar(comp, "company", "jobs", "Jobs by company (top 15)", horizontal=True), width="stretch")
        src = jobs.groupby(["source", "data_mode"]).size().reset_index(name="jobs")
        fig = px.pie(src, names="source", values="jobs", hole=0.5, title="Jobs by source", color_discrete_sequence=CHART_COLORS)
        fig.update_layout(**LAYOUT)
        c4.plotly_chart(fig, width="stretch")
        c5, c6 = st.columns(2)
        emp = jobs["employment_type"].value_counts().reset_index()
        emp.columns = ["employment type", "jobs"]
        c5.plotly_chart(_bar(emp, "employment type", "jobs", "Employment type"), width="stretch")
        fresh = jobs["is_fresher_friendly"].map({True: "Fresher-friendly", False: "Experience required / unclear"}).value_counts().reset_index()
        fresh.columns = ["group", "jobs"]
        fig = px.pie(fresh, names="group", values="jobs", hole=0.5, title="Fresher-friendly share", color_discrete_sequence=CHART_COLORS)
        fig.update_layout(**LAYOUT)
        c6.plotly_chart(fig, width="stretch")

    with tab_skills:
        counts = Counter(s for lst in jobs["skills"] for s in lst)
        top = pd.DataFrame(counts.most_common(20), columns=["skill", "jobs"])
        st.plotly_chart(_bar(top, "skill", "jobs", "Most frequently requested skills (top 20)", horizontal=True), width="stretch")
        st.caption("Skills are detected with the transparent dictionary in config/skills.json. Company 'About us' text can add "
                   "words such as 'cybersecurity' that are not strictly requirements — a known limitation of keyword extraction.")
        scores = state.match_scores()
        if scores:
            s = pd.Series(scores, name="score")
            bins = pd.cut(s, bins=[0, 20, 40, 60, 80, 100], include_lowest=True,
                          labels=["0–20", "20–40", "40–60", "60–80", "80–100"]).value_counts().sort_index().reset_index()
            bins.columns = ["score range", "jobs"]
            st.plotly_chart(_bar(bins, "score range", "jobs", "Distribution of relevance scores for your current profile"),
                            width="stretch")
            st.caption("Relevance scores rank jobs for this profile; they are not probabilities of being hired.")
        else:
            st.info("Set a candidate profile on the AI Recommendations page to see the match-score distribution.")

    with tab_ml:
        st.markdown("Unsupervised **K-Means** clustering of TF-IDF job vectors. No labels are used; *k* is chosen by the "
                    "silhouette coefficient (cosine distance) over k = 3…10, reported below as measured. Low values mean "
                    "the groups overlap — job descriptions share much of their vocabulary.")
        res = _clusters(state.data_signature(), st.session_state.dataset_choice)
        if res is None:
            st.info("Not enough jobs to cluster (at least 5 are needed).")
        else:
            labelled = jobs.assign(cluster=[f"Cluster {c + 1}" for c in res["labels"]])
            c1, c2 = st.columns([1, 1.4])
            c1.metric("Chosen k", res["k"])
            c1.metric("Silhouette (cosine)", f"{res['silhouette']:.3f}", help="−1 to 1; higher means better-separated clusters")
            sil = pd.DataFrame({"k": list(res["silhouette_by_k"]), "silhouette": list(res["silhouette_by_k"].values())})
            fig = px.line(sil, x="k", y="silhouette", markers=True, title="Silhouette score for each k")
            fig.update_layout(**{**LAYOUT, "height": 260})
            c2.plotly_chart(fig, width="stretch")
            summary = labelled.groupby("cluster").agg(jobs=("job_id", "count"),
                                                      example_titles=("title", lambda t: " · ".join(t.value_counts().index[:3])))
            summary["top_terms"] = [", ".join(res["top_terms"][int(c.split()[1]) - 1]) for c in summary.index]
            st.dataframe(summary.reset_index(), hide_index=True, width="stretch")
            mix = labelled.groupby(["cluster", "category"]).size().reset_index(name="jobs")
            fig = px.bar(mix, x="cluster", y="jobs", color="category", title="Rule-based categories inside each cluster",
                         color_discrete_sequence=CHART_COLORS)
            fig.update_layout(**{**LAYOUT, "height": 420})
            st.plotly_chart(fig, width="stretch")

    with tab_cat:
        cat = state.get_catalogue()
        c1, c2 = st.columns(2)
        ind = cat["industry"].value_counts().reset_index()
        ind.columns = ["industry", "companies"]
        c1.plotly_chart(_bar(ind, "industry", "companies", "Catalogue companies by industry", horizontal=True), width="stretch")
        ver = cat.groupby(["verification_status", "url_type"]).size().reset_index(name="companies")
        fig = px.bar(ver, x="verification_status", y="companies", color="url_type", title="Catalogue URL verification status",
                     color_discrete_sequence=CHART_COLORS)
        fig.update_layout(**LAYOUT, xaxis_title="", yaxis_title="")
        c2.plotly_chart(fig, width="stretch")
        apps = state.get_store().load_applications()
        if apps.empty:
            st.info("No tracked applications yet — tracker statistics appear here once you save jobs.")
        else:
            a = apps["status"].value_counts().reset_index()
            a.columns = ["status", "applications"]
            st.plotly_chart(_bar(a, "status", "applications", "Application tracker statuses (user-entered)"), width="stretch")
        runs = state.get_store().load_runs()
        if not runs.empty:
            st.markdown("**Crawl history (from SQLite)**")
            st.dataframe(runs.drop(columns=["errors"]), hide_index=True, width="stretch")
