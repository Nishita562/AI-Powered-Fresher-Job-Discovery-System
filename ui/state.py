"""Session state, cached data loading and shared helpers for all pages.

Expensive work (loading data, fitting TF-IDF) is cached and keyed on the
data files' modification times, so changing a filter or switching pages
never re-runs browser automation or re-fits the model.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import pandas as pd
import streamlit as st

from config import settings
from src.company_catalog import load_catalogue
from src.data_loader import load_jobs
from src.job_filter import JobFilters
from src.recommendation import CandidateProfile, JobRecommender
from src.storage import JobStore


def _mtime(path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def data_signature() -> tuple[float, float]:
    return (_mtime(settings.DATABASE_PATH), _mtime(settings.SAMPLE_JOBS_JSON))


@st.cache_resource
def get_store() -> JobStore:
    return JobStore()


@st.cache_data(show_spinner="Loading job records…")
def _jobs(choice: str, signature: tuple) -> pd.DataFrame:
    return load_jobs(choice, get_store())


def get_jobs() -> pd.DataFrame:
    return _jobs(st.session_state.dataset_choice, data_signature())


@st.cache_data(show_spinner=False)
def _catalogue(mtime: float) -> pd.DataFrame:
    return load_catalogue()


def get_catalogue() -> pd.DataFrame:
    return _catalogue(_mtime(settings.COMPANIES_CSV))


@st.cache_resource(show_spinner="Fitting TF-IDF model on the job corpus…")
def _recommender(choice: str, signature: tuple) -> JobRecommender:
    return JobRecommender(_jobs(choice, signature))


def get_recommender() -> JobRecommender:
    return _recommender(st.session_state.dataset_choice, data_signature())


def refresh_data() -> None:
    _jobs.clear()
    _catalogue.clear()
    _recommender.clear()
    st.session_state.pop("score_cache", None)


DEFAULTS = {
    "dataset_choice": "all",
    "filters": JobFilters(),
    "search_page": 1,
    "page_size": 10,
    "sort_option": "Newest first",
    "profile": None,           # CandidateProfile once the user has entered one
    "profile_is_demo": False,
    "resume_text": "",
    "resume_skills": [],
    "resume_name": "",
    "rec_results": None,
    "company_page": 1,
    "flash": None,
}


def init_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value if not isinstance(value, JobFilters) else JobFilters()


def profile_key(profile: CandidateProfile | None) -> str:
    if profile is None:
        return ""
    return hashlib.md5(json.dumps(asdict(profile), sort_keys=True).encode()).hexdigest()


def match_scores() -> dict[str, float]:
    """Relevance scores for every loaded job under the current profile (cached per profile)."""
    profile = st.session_state.profile
    if profile is None or profile.is_empty():
        return {}
    key = (profile_key(profile), st.session_state.dataset_choice, data_signature())
    cache = st.session_state.get("score_cache")
    if not cache or cache[0] != key:
        recs = get_recommender().score_all(profile)
        cache = (key, {r.job_id: r for r in recs})
        st.session_state.score_cache = cache
    return {jid: r.score for jid, r in cache[1].items()}


def recommendation_for(job_id: str):
    match_scores()
    cache = st.session_state.get("score_cache")
    return cache[1].get(job_id) if cache else None


DEMO_PROFILE = CandidateProfile(
    skills=["python", "machine learning", "sql", "pandas", "scikit-learn", "data visualization", "git"],
    preferred_roles=["Machine Learning Engineer", "Data Analyst"],
    preferred_locations=["Bengaluru", "Remote"],
    experience_years=0,
    accept_remote=True,
)


def flash(message: str, kind: str = "success") -> None:
    """Show a message after the next rerun (e.g. after a button changes state)."""
    st.session_state.flash = (message, kind)


def show_flash() -> None:
    msg = st.session_state.get("flash")
    if msg:
        text, kind = msg
        {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}[kind](text)
        st.session_state.flash = None
