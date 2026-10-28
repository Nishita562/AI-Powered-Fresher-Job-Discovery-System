"""CSV / JSON export of job records (used by the UI download buttons and the CLI)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import settings
from src.models import JOB_FIELDS

EXTRA_EXPORT_COLUMNS = ["match_score", "status", "notes"]


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in JOB_FIELDS + EXTRA_EXPORT_COLUMNS if c in df.columns]
    return df[cols].copy()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    out = _prepare(df)
    if "skills" in out.columns:
        out["skills"] = out["skills"].apply(lambda s: ", ".join(s) if isinstance(s, list) else (s or ""))
    return out.to_csv(index=False).encode("utf-8")


def to_json_bytes(df: pd.DataFrame) -> bytes:
    out = _prepare(df)
    records = json.loads(out.to_json(orient="records", force_ascii=False))
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "record_count": len(records),
        "data_modes": sorted(out["data_mode"].dropna().unique().tolist()) if "data_mode" in out else [],
        "note": "data_mode 'sample' and 'demo_fixture' records are fictional demonstration data, not real vacancies.",
        "jobs": records,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def export_to_files(df: pd.DataFrame, stem: str = "jobs_export", directory: Path | None = None) -> tuple[Path, Path]:
    directory = Path(directory or settings.EXPORT_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = directory / f"{stem}_{stamp}.csv"
    json_path = directory / f"{stem}_{stamp}.json"
    csv_path.write_bytes(to_csv_bytes(df))
    json_path.write_bytes(to_json_bytes(df))
    return csv_path, json_path
