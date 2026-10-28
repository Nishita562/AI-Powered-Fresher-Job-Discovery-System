"""Job record schema shared by the scraper, storage, filters and recommender."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

# Column order used for CSV/JSON export and the SQLite table.
JOB_FIELDS = [
    "job_id",
    "title",
    "company",
    "location",
    "work_mode",
    "experience_text",
    "min_experience_years",
    "max_experience_years",
    "employment_type",
    "description",
    "skills",
    "eligibility",
    "salary",
    "deadline",
    "apply_url",
    "source",
    "source_type",
    "data_mode",
    "category",
    "is_fresher_friendly",
    "discovered_at",
]

VALID_DATA_MODES = {"sample", "demo_fixture", "live"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class JobRecord:
    """One normalised job posting. Unknown values stay empty/None — never guessed."""

    title: str
    company: str
    apply_url: str = ""
    location: str = ""
    work_mode: str = "Unknown"  # Remote / Hybrid / On-site / Unknown
    experience_text: str = ""
    min_experience_years: float | None = None
    max_experience_years: float | None = None
    employment_type: str = "Not specified"
    description: str = ""
    skills: list[str] = field(default_factory=list)
    eligibility: str = ""
    salary: str = ""
    deadline: str = ""  # ISO date (YYYY-MM-DD) when published, else ""
    source: str = ""
    source_type: str = ""  # greenhouse / lever / generic / fixture / sample
    data_mode: str = "live"
    category: str = "Other"
    is_fresher_friendly: bool = False
    discovered_at: str = field(default_factory=utc_now_iso)
    job_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: d[k] for k in JOB_FIELDS}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "JobRecord":
        known = {k: d[k] for k in JOB_FIELDS if k in d}
        skills = known.get("skills", [])
        if isinstance(skills, str):
            known["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
        for key in ("min_experience_years", "max_experience_years"):
            val = known.get(key)
            if val in ("", "nan") or (isinstance(val, float) and val != val):
                known[key] = None
        if "is_fresher_friendly" in known:
            known["is_fresher_friendly"] = str(known["is_fresher_friendly"]).lower() in {"1", "true", "yes"}
        for key in ("title", "company", "location", "description", "apply_url", "eligibility", "salary", "deadline", "experience_text"):
            if key in known and (known[key] is None or (isinstance(known[key], float) and known[key] != known[key])):
                known[key] = ""
        return cls(**known)
