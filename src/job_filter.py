"""Filtering and sorting of job DataFrames (independent of the scraper and UI)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from src.skills import normalize_skill_list

QUICK_FILTERS = {
    "Fresher": lambda df: df["is_fresher_friendly"],
    "Internship": lambda df: df["employment_type"].eq("Internship"),
    "Graduate Trainee": lambda df: df["employment_type"].eq("Graduate Trainee")
    | df["title"].str.contains(r"graduate|trainee", case=False, regex=True),
    "Entry-level": lambda df: df["min_experience_years"].fillna(99).le(1)
    | df["title"].str.contains(r"entry|junior|associate", case=False, regex=True),
}

SORT_OPTIONS = {
    "Relevance (match score)": ("match_score", False),
    "Newest first": ("discovered_at", False),
    "Oldest first": ("discovered_at", True),
    "Company (A–Z)": ("company", True),
    "Title (A–Z)": ("title", True),
    "Deadline (soonest)": ("deadline", True),
    "Experience (lowest first)": ("min_experience_years", True),
}


@dataclass
class JobFilters:
    keyword: str = ""
    locations: list[str] = field(default_factory=list)
    remote_only: bool = False
    skills: list[str] = field(default_factory=list)
    skill_mode: str = "any"  # "any" or "all"
    companies: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    data_modes: list[str] = field(default_factory=list)
    employment_types: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    max_experience: float | None = None
    fresher_only: bool = False
    quick: list[str] = field(default_factory=list)
    deadline_after: date | None = None
    hide_expired: bool = False


def apply_filters(df: pd.DataFrame, f: JobFilters, today: date | None = None) -> pd.DataFrame:
    if df.empty:
        return df
    out = df
    if f.keyword.strip():
        terms = [t for t in f.keyword.lower().split() if t]
        haystack = (
            out["title"].fillna("") + " " + out["company"].fillna("") + " " + out["location"].fillna("") + " "
            + out["skills"].apply(lambda s: " ".join(s) if isinstance(s, list) else str(s)) + " "
            + out["description"].fillna("")
        ).str.lower()
        for t in terms:  # every term must appear somewhere (AND search)
            out = out[haystack.loc[out.index].str.contains(t, regex=False)]
    if f.locations:
        pattern = "|".join(loc.lower() for loc in f.locations)
        loc_mask = out["location"].fillna("").str.lower().str.contains(pattern, regex=True)
        if "remote" in pattern:
            loc_mask |= out["work_mode"].eq("Remote")
        out = out[loc_mask]
    if f.remote_only:
        out = out[out["work_mode"].isin(["Remote", "Hybrid"])]
    if f.skills:
        wanted = set(normalize_skill_list(f.skills))
        if f.skill_mode == "all":
            out = out[out["skills"].apply(lambda s: wanted.issubset(set(s)))]
        else:
            out = out[out["skills"].apply(lambda s: bool(wanted & set(s)))]
    if f.companies:
        out = out[out["company"].isin(f.companies)]
    if f.sources:
        out = out[out["source"].isin(f.sources)]
    if f.data_modes:
        out = out[out["data_mode"].isin(f.data_modes)]
    if f.employment_types:
        out = out[out["employment_type"].isin(f.employment_types)]
    if f.categories:
        out = out[out["category"].isin(f.categories)]
    if f.max_experience is not None:
        # Unknown experience is kept (not silently dropped) — it is shown as "Not specified".
        out = out[out["min_experience_years"].isna() | (out["min_experience_years"] <= f.max_experience)]
    if f.fresher_only:
        out = out[out["is_fresher_friendly"]]
    for name in f.quick:
        if name in QUICK_FILTERS:
            out = out[QUICK_FILTERS[name](out)]
    today = today or date.today()
    if f.hide_expired:
        out = out[(out["deadline"].fillna("") == "") | (out["deadline"] >= today.isoformat())]
    if f.deadline_after:
        out = out[(out["deadline"].fillna("") != "") & (out["deadline"] >= f.deadline_after.isoformat())]
    return out


def sort_jobs(df: pd.DataFrame, option: str) -> pd.DataFrame:
    column, ascending = SORT_OPTIONS.get(option, ("discovered_at", False))
    if column not in df.columns or df.empty:
        return df
    if column == "deadline":
        # Jobs without a published deadline go last.
        key = df["deadline"].replace("", "9999-12-31").fillna("9999-12-31")
        return df.assign(_k=key).sort_values("_k", ascending=True, kind="stable").drop(columns="_k")
    return df.sort_values(column, ascending=ascending, na_position="last", kind="stable")
