"""Central configuration for the Fresher Job Discovery System.

Every tunable value lives here so that behaviour can be changed without
editing application code. Values can be overridden with environment
variables (or a local ``.env`` file, see ``.env.example``).
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal ``.env`` loader (KEY=VALUE lines) so python-dotenv is not needed."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


# ---------------------------------------------------------------- paths
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
FIXTURE_DIR = DATA_DIR / "fixtures" / "career_pages"
COMPANIES_CSV = DATA_DIR / "companies.csv"
SAMPLE_JOBS_CSV = DATA_DIR / "sample_jobs.csv"
SAMPLE_JOBS_JSON = DATA_DIR / "sample_jobs.json"
SKILLS_JSON = CONFIG_DIR / "skills.json"
SOURCES_JSON = CONFIG_DIR / "sources.json"
DATABASE_PATH = Path(os.environ.get("JOBS_DB_PATH", BASE_DIR / "database" / "jobs.db"))
EXPORT_DIR = BASE_DIR / "exports"
LOG_DIR = BASE_DIR / "logs"
CRAWL_STATUS_FILE = BASE_DIR / "database" / "crawl_status.json"

# ---------------------------------------------------------------- browser automation
HEADLESS = _env_bool("HEADLESS", True)
NAV_TIMEOUT_MS = _env_int("NAV_TIMEOUT_MS", 25_000)
MAX_RETRIES = _env_int("MAX_RETRIES", 2)
# Polite delay between page loads on the same host (seconds). Lever's
# robots.txt asks for Crawl-delay: 1, so the default is deliberately higher.
REQUEST_DELAY_SECONDS = _env_float("REQUEST_DELAY_SECONDS", 1.5)
BATCH_SIZE = _env_int("BATCH_SIZE", 5)
MAX_DETAIL_PAGES_PER_COMPANY = _env_int("MAX_DETAIL_PAGES_PER_COMPANY", 8)
MAX_LISTINGS_PER_COMPANY = _env_int("MAX_LISTINGS_PER_COMPANY", 200)
RESPECT_ROBOTS_TXT = _env_bool("RESPECT_ROBOTS_TXT", True)
USER_AGENT = os.environ.get(
    "USER_AGENT",
    "FresherJobDiscovery/1.0 (B.Tech AIML academic project; low request rate)",
)

# ---------------------------------------------------------------- recommendation
# Illustrative starting weights (not experimentally optimised). They must sum to 1.
WEIGHT_TEXT_SIMILARITY = 0.50
WEIGHT_SKILL_MATCH = 0.30
WEIGHT_PREFERENCE = 0.20
# Multipliers applied after the weighted sum, based on experience eligibility.
ELIGIBILITY_FACTORS = {"eligible": 1.0, "unknown": 0.9, "not_eligible": 0.5}
TFIDF_MAX_FEATURES = 5000
TFIDF_NGRAM_RANGE = (1, 2)
# How many times the title is repeated in the job document (simple field weighting).
TITLE_WEIGHT_REPEAT = 2

# ---------------------------------------------------------------- UI
PAGE_SIZE_OPTIONS = [10, 20, 50]
APPLICATION_STATUSES = ["Saved", "Applied", "Interview", "Rejected", "Offer"]
MAX_RESUME_MB = 5

# Data-mode labels shown in the interface. Every job record carries one of these.
DATA_MODE_LABELS = {
    "sample": "Sample data (fictional, offline demo)",
    "demo_fixture": "Demo crawl of local fixture pages",
    "live": "Live — collected from public job boards",
}
