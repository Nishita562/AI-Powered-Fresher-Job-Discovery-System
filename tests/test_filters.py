from datetime import date

import pandas as pd

from src.job_filter import JobFilters, apply_filters, sort_jobs


def test_keyword_search_requires_every_term(jobs_df):
    out = apply_filters(jobs_df, JobFilters(keyword="python intern"))
    assert out["title"].tolist() == ["Machine Learning Intern"]
    assert apply_filters(jobs_df, JobFilters(keyword="nonexistentword")).empty


def test_location_filter_includes_remote_jobs_when_asked(jobs_df):
    out = apply_filters(jobs_df, JobFilters(locations=["Remote"]))
    assert out["title"].tolist() == ["Frontend Developer Intern"]
    assert set(apply_filters(jobs_df, JobFilters(locations=["Pune", "Noida"]))["title"]) == {"Junior Data Analyst", "HR Intern"}


def test_skill_filter_any_vs_all(jobs_df):
    any_ = apply_filters(jobs_df, JobFilters(skills=["python", "react"], skill_mode="any"))
    all_ = apply_filters(jobs_df, JobFilters(skills=["python", "scikit-learn"], skill_mode="all"))
    assert {"Machine Learning Intern", "Frontend Developer Intern", "Senior Data Scientist"} == set(any_["title"])
    assert all_["title"].tolist() == ["Machine Learning Intern"]


def test_experience_filter_keeps_unknown(jobs_df):
    out = apply_filters(jobs_df, JobFilters(max_experience=1))
    assert "Senior Data Scientist" not in set(out["title"])
    assert "HR Intern" in set(out["title"])  # internship -> 0 years


def test_fresher_and_quick_filters(jobs_df):
    fresher = apply_filters(jobs_df, JobFilters(fresher_only=True))
    assert "Senior Data Scientist" not in set(fresher["title"])
    interns = apply_filters(jobs_df, JobFilters(quick=["Internship"]))
    assert set(interns["employment_type"]) == {"Internship"}


def test_deadline_filters():
    df = pd.DataFrame({"title": ["a", "b", "c"], "deadline": ["2026-10-01", "", "2026-12-01"]})
    for col in ["company", "location", "description", "work_mode", "employment_type", "category", "source", "data_mode"]:
        df[col] = ""
    df["skills"] = [[], [], []]
    df["min_experience_years"] = None
    df["is_fresher_friendly"] = True
    out = apply_filters(df, JobFilters(hide_expired=True), today=date(2026, 10, 25))
    assert out["title"].tolist() == ["b", "c"]
    assert sort_jobs(df, "Deadline (soonest)")["title"].tolist() == ["a", "c", "b"]  # no deadline goes last


def test_sorting(jobs_df):
    scored = jobs_df.assign(match_score=[10, 50, 30, 20, 40])
    assert sort_jobs(scored, "Relevance (match score)")["match_score"].tolist() == [50, 40, 30, 20, 10]
    assert sort_jobs(jobs_df, "Company (A–Z)").shape == jobs_df.shape


def test_empty_dataframe_is_safe():
    empty = pd.DataFrame()
    assert apply_filters(empty, JobFilters(keyword="x")).empty
