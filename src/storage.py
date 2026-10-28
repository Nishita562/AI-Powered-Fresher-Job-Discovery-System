"""SQLite persistence: collected jobs, the application tracker and crawl-run history."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from config import settings
from src.models import JOB_FIELDS, JobRecord, utc_now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    work_mode TEXT,
    experience_text TEXT,
    min_experience_years REAL,
    max_experience_years REAL,
    employment_type TEXT,
    description TEXT,
    skills TEXT,               -- JSON array of canonical skill names
    eligibility TEXT,
    salary TEXT,
    deadline TEXT,             -- ISO date or empty
    apply_url TEXT,
    source TEXT,
    source_type TEXT,
    data_mode TEXT NOT NULL CHECK (data_mode IN ('sample','demo_fixture','live')),
    category TEXT,
    is_fresher_friendly INTEGER,
    discovered_at TEXT NOT NULL,   -- first time this job was seen
    last_seen_at TEXT NOT NULL     -- most recent crawl that saw it
);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_mode ON jobs(data_mode);

CREATE TABLE IF NOT EXISTS applications (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    notes TEXT DEFAULT '',
    job_snapshot TEXT NOT NULL,    -- JSON copy so sample jobs can be tracked too
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    companies_attempted INTEGER DEFAULT 0,
    companies_succeeded INTEGER DEFAULT 0,
    companies_failed INTEGER DEFAULT 0,
    listings_seen INTEGER DEFAULT 0,
    jobs_saved INTEGER DEFAULT 0,
    new_jobs INTEGER DEFAULT 0,
    duplicates_removed INTEGER DEFAULT 0,
    status TEXT,
    errors TEXT                    -- JSON array of {company, error}
);
"""


class JobStore:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.DATABASE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------ jobs
    def upsert_jobs(self, records: Iterable[JobRecord]) -> tuple[int, int]:
        """Insert or update jobs. Returns ``(saved, newly_inserted)``.

        ``discovered_at`` of an existing row is never overwritten, so the
        original collection timestamp is preserved across crawls.
        """
        saved = new = 0
        now = utc_now_iso()
        with self._connect() as conn:
            for rec in records:
                d = rec.to_dict()
                d["skills"] = json.dumps(d["skills"])
                d["is_fresher_friendly"] = int(bool(d["is_fresher_friendly"]))
                exists = conn.execute("SELECT 1 FROM jobs WHERE job_id = ?", (d["job_id"],)).fetchone()
                if exists:
                    cols = [c for c in JOB_FIELDS if c not in ("job_id", "discovered_at")]
                    conn.execute(
                        f"UPDATE jobs SET {', '.join(f'{c} = ?' for c in cols)}, last_seen_at = ? WHERE job_id = ?",
                        [d[c] for c in cols] + [now, d["job_id"]],
                    )
                else:
                    conn.execute(
                        f"INSERT INTO jobs ({', '.join(JOB_FIELDS)}, last_seen_at) VALUES ({', '.join('?' * len(JOB_FIELDS))}, ?)",
                        [d[c] for c in JOB_FIELDS] + [now],
                    )
                    new += 1
                saved += 1
        return saved, new

    def load_jobs(self, data_mode: str | None = None) -> pd.DataFrame:
        query, params = "SELECT * FROM jobs", ()
        if data_mode:
            query, params = query + " WHERE data_mode = ?", (data_mode,)
        with self._connect() as conn:
            df = pd.read_sql_query(query + " ORDER BY discovered_at DESC", conn, params=params)
        if not df.empty:
            df["skills"] = df["skills"].apply(lambda s: json.loads(s) if s else [])
            df["is_fresher_friendly"] = df["is_fresher_friendly"].astype(bool)
        return df

    def count_jobs(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute("SELECT data_mode, COUNT(*) AS n FROM jobs GROUP BY data_mode").fetchall()
        return {r["data_mode"]: r["n"] for r in rows}

    def delete_jobs(self, data_mode: str) -> int:
        with self._connect() as conn:
            return conn.execute("DELETE FROM jobs WHERE data_mode = ?", (data_mode,)).rowcount

    # ------------------------------------------------------------ application tracker
    def save_application(self, job: dict, status: str = "Saved", notes: str = "") -> None:
        if status not in settings.APPLICATION_STATUSES:
            raise ValueError(f"Unknown status {status!r}")
        snapshot = {k: job.get(k) for k in JOB_FIELDS}
        if not isinstance(snapshot.get("skills"), list):
            snapshot["skills"] = list(snapshot.get("skills") or [])
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO applications (job_id, status, notes, job_snapshot, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(job_id) DO UPDATE SET status = excluded.status,
                       notes = CASE WHEN excluded.notes = '' THEN applications.notes ELSE excluded.notes END,
                       updated_at = excluded.updated_at""",
                (job["job_id"], status, notes, json.dumps(snapshot, default=str), now, now),
            )

    def update_application(self, job_id: str, status: str | None = None, notes: str | None = None) -> None:
        if status is not None and status not in settings.APPLICATION_STATUSES:
            raise ValueError(f"Unknown status {status!r}")
        with self._connect() as conn:
            if status is not None:
                conn.execute("UPDATE applications SET status = ?, updated_at = ? WHERE job_id = ?", (status, utc_now_iso(), job_id))
            if notes is not None:
                conn.execute("UPDATE applications SET notes = ?, updated_at = ? WHERE job_id = ?", (notes, utc_now_iso(), job_id))

    def remove_application(self, job_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))

    def load_applications(self) -> pd.DataFrame:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
        records = []
        for r in rows:
            snap = json.loads(r["job_snapshot"])
            records.append({**snap, "job_id": r["job_id"], "status": r["status"], "notes": r["notes"],
                            "saved_at": r["created_at"], "updated_at": r["updated_at"]})
        return pd.DataFrame(records)

    def tracked_ids(self) -> set[str]:
        with self._connect() as conn:
            return {r["job_id"] for r in conn.execute("SELECT job_id FROM applications")}

    # ------------------------------------------------------------ crawl history
    def start_run(self, mode: str) -> int:
        with self._connect() as conn:
            cur = conn.execute("INSERT INTO crawl_runs (mode, started_at, status) VALUES (?, ?, 'running')", (mode, utc_now_iso()))
            return int(cur.lastrowid)

    def finish_run(self, run_id: int, **stats) -> None:
        stats = {**stats, "finished_at": utc_now_iso()}
        if "errors" in stats:
            stats["errors"] = json.dumps(stats["errors"])
        cols = ", ".join(f"{k} = ?" for k in stats)
        with self._connect() as conn:
            conn.execute(f"UPDATE crawl_runs SET {cols} WHERE run_id = ?", [*stats.values(), run_id])

    def load_runs(self, limit: int = 20) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query("SELECT * FROM crawl_runs ORDER BY run_id DESC LIMIT ?", conn, params=(limit,))
