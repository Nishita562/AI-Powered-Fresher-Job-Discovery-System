"""Data-driven company catalogue (``data/companies.csv``).

The catalogue is a *directory* of employers and their career-page URLs.
It does not claim that any company currently has a vacancy — vacancies
only come from listings actually collected by the scraper.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterator

import pandas as pd

from config import settings

CATALOGUE_COLUMNS = [
    "company_id", "company_name", "industry", "headquarters", "career_url", "url_type",
    "ats_platform", "ats_board_token", "verification_status", "verification_detail",
    "last_checked", "notes",
]
URL_TYPES = {"careers_page", "homepage", "ats_board", "missing"}
VERIFICATION_STATUSES = {"verified", "unverified", "missing"}


def _norm_name(name: str) -> str:
    name = re.sub(r"\b(pvt|private|ltd|limited|inc|llp|india)\b\.?", " ", str(name).lower())
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


def load_catalogue(path: Path | str | None = None) -> pd.DataFrame:
    """Load, validate and de-duplicate the catalogue. Missing optional columns are added."""
    df = pd.read_csv(path or settings.COMPANIES_CSV, dtype=str, keep_default_na=False)
    missing_required = {"company_name"} - set(df.columns)
    if missing_required:
        raise ValueError(f"companies.csv is missing required columns: {missing_required}")
    for col in CATALOGUE_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[CATALOGUE_COLUMNS].copy()
    for col in CATALOGUE_COLUMNS:
        df[col] = df[col].astype(str).str.strip()
    df = df[df["company_name"] != ""]
    df["_key"] = df["company_name"].map(_norm_name)
    df = df.drop_duplicates(subset="_key", keep="first").drop(columns="_key")
    # Derive statuses when the verifier has not run yet.
    df.loc[df["career_url"] == "", ["url_type", "verification_status"]] = ["missing", "missing"]
    df.loc[(df["verification_status"] == "") & (df["career_url"] != ""), "verification_status"] = "unverified"
    df.loc[df["url_type"] == "", "url_type"] = "careers_page"
    if (df["company_id"] == "").any():
        df["company_id"] = [f"C{i:04d}" for i in range(1, len(df) + 1)]
    return df.reset_index(drop=True)


def search_catalogue(
    df: pd.DataFrame,
    query: str = "",
    industries: list[str] | None = None,
    statuses: list[str] | None = None,
    url_types: list[str] | None = None,
    platforms: list[str] | None = None,
) -> pd.DataFrame:
    out = df
    if query:
        q = query.strip().lower()
        mask = out["company_name"].str.lower().str.contains(q, regex=False) | out["industry"].str.lower().str.contains(q, regex=False)
        out = out[mask]
    if industries:
        out = out[out["industry"].isin(industries)]
    if statuses:
        out = out[out["verification_status"].isin(statuses)]
    if url_types:
        out = out[out["url_type"].isin(url_types)]
    if platforms:
        out = out[out["ats_platform"].isin(platforms)]
    return out


def paginate(df: pd.DataFrame, page: int, page_size: int) -> tuple[pd.DataFrame, int]:
    """Return ``(page_rows, total_pages)``; ``page`` is 1-based and clamped to range."""
    total_pages = max(1, math.ceil(len(df) / page_size))
    page = min(max(1, page), total_pages)
    start = (page - 1) * page_size
    return df.iloc[start:start + page_size], total_pages


def iter_batches(df: pd.DataFrame, batch_size: int = settings.BATCH_SIZE) -> Iterator[pd.DataFrame]:
    """Yield the catalogue in fixed-size batches so the crawler never opens hundreds of pages at once."""
    for start in range(0, len(df), batch_size):
        yield df.iloc[start:start + batch_size]


def crawlable(df: pd.DataFrame) -> pd.DataFrame:
    """Companies the live crawler can attempt: a public ATS board or a known career URL."""
    has_board = df["ats_platform"].isin(["greenhouse", "lever"]) & (df["ats_board_token"] != "")
    has_url = (df["career_url"] != "") & (df["url_type"].isin(["careers_page", "ats_board"]))
    return df[has_board | has_url]


def catalogue_stats(df: pd.DataFrame) -> dict:
    return {
        "total": int(len(df)),
        "by_status": df["verification_status"].value_counts().to_dict(),
        "by_url_type": df["url_type"].value_counts().to_dict(),
        "by_industry": df["industry"].value_counts().to_dict(),
        "with_public_board": int((df["ats_board_token"] != "").sum()),
    }
