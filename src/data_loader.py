"""Loads job records from the sample dataset and/or the SQLite store into one DataFrame."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import settings
from src.deduplication import deduplicate
from src.models import JOB_FIELDS, JobRecord
from src.storage import JobStore

DATASET_CHOICES = {
    "all": "All available data (sample + collected)",
    "collected": "Collected only (live + demo crawl)",
    "live": "Live only",
    "sample": "Sample only",
}


def load_sample_jobs(path: Path | None = None) -> pd.DataFrame:
    path = Path(path or settings.SAMPLE_JOBS_JSON)
    if not path.exists():
        return pd.DataFrame(columns=JOB_FIELDS)
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["jobs"] if isinstance(payload, dict) else payload
    df = pd.DataFrame(rows)
    for col in JOB_FIELDS:
        if col not in df.columns:
            df[col] = None
    return df[JOB_FIELDS]


def _finalise(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=JOB_FIELDS)
    df = df.copy()
    df["skills"] = df["skills"].apply(lambda s: s if isinstance(s, list) else [x.strip() for x in str(s or "").split(",") if x.strip()])
    for col in ("title", "company", "location", "description", "apply_url", "salary", "deadline", "eligibility",
                "experience_text", "source", "source_type", "category", "employment_type", "work_mode"):
        df[col] = df[col].fillna("").astype(str)
    df["min_experience_years"] = pd.to_numeric(df["min_experience_years"], errors="coerce")
    df["max_experience_years"] = pd.to_numeric(df["max_experience_years"], errors="coerce")
    df["is_fresher_friendly"] = df["is_fresher_friendly"].astype(str).str.lower().isin(["true", "1", "yes"])
    # Final de-duplication across sources using the same keys as the scraper.
    records = [JobRecord.from_dict(r) for r in df.to_dict(orient="records")]
    unique, _ = deduplicate(records)
    keep = {r.job_id for r in unique}
    df = df[df["job_id"].isin(keep)].drop_duplicates(subset="job_id")
    return df.sort_values("discovered_at", ascending=False).reset_index(drop=True)


def load_jobs(choice: str = "all", store: JobStore | None = None) -> pd.DataFrame:
    store = store or JobStore()
    frames = []
    if choice in ("all", "sample"):
        frames.append(load_sample_jobs())
    if choice in ("all", "collected", "live"):
        collected = store.load_jobs()
        if not collected.empty:
            if choice == "live":
                collected = collected[collected["data_mode"] == "live"]
            frames.append(collected[JOB_FIELDS])
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=JOB_FIELDS)
    return _finalise(pd.concat(frames, ignore_index=True))
