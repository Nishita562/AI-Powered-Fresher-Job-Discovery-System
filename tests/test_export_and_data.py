import io
import json

import pandas as pd

from src.data_loader import load_sample_jobs
from src.export import export_to_files, to_csv_bytes, to_json_bytes


def test_csv_export_joins_skills(jobs_df):
    df = pd.read_csv(io.BytesIO(to_csv_bytes(jobs_df)))
    assert len(df) == len(jobs_df)
    assert "python" in df.iloc[0]["skills"] and "," in df.iloc[0]["skills"]


def test_json_export_labels_data(jobs_df):
    payload = json.loads(to_json_bytes(jobs_df))
    assert payload["record_count"] == len(jobs_df)
    assert "fictional" in payload["note"]
    assert isinstance(payload["jobs"][0]["skills"], list)


def test_export_to_files(tmp_path, jobs_df):
    csv_path, json_path = export_to_files(jobs_df, "t", tmp_path)
    assert csv_path.exists() and json_path.exists()


def test_sample_dataset_is_labelled_and_clean():
    df = load_sample_jobs()
    assert len(df) >= 100
    assert set(df["data_mode"]) == {"sample"}
    assert df["job_id"].is_unique
    assert df["apply_url"].str.startswith("https://example.com/").all()  # reserved domain, never a real employer
