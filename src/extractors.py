"""Rule-based information extraction from job titles and descriptions.

Each function returns an empty value when the information is not
published — the system never invents salaries, deadlines or requirements.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from src.deduplication import make_job_id, normalize_url
from src.keywords import has_fresher_signal, has_senior_signal, has_strong_senior_signal
from src.models import JobRecord, utc_now_iso
from src.skills import extract_skills, normalize_skill_list
from src.text_utils import clean_whitespace, strip_html

# ---------------------------------------------------------------- experience
_YEARS = r"(?:years?|yrs?)"
_NUM = r"(\d{1,2}(?:\.\d)?)"
_RANGE_RE = re.compile(rf"{_NUM}\s*(?:-|–|—|to)\s*{_NUM}\s*\+?\s*{_YEARS}", re.I)
_PLUS_RE = re.compile(rf"{_NUM}\s*\+\s*{_YEARS}", re.I)
_MIN_RE = re.compile(rf"(?:minimum|min\.?|at\s*least|atleast)\s*(?:of\s*)?{_NUM}\s*\+?\s*{_YEARS}", re.I)
_PLAIN_RE = re.compile(
    rf"{_NUM}\s*{_YEARS}\s*(?:of\s*)?(?:relevant\s*|professional\s*|work\s*|industry\s*|hands-on\s*|prior\s*)?(?:experience|exp\b)",
    re.I,
)
_FRESHER_EXP_RE = re.compile(
    r"\b(freshers?|no (?:prior |previous )?(?:work )?experience|0 years?|zero experience|entry[- ]level)\b", re.I
)


def parse_experience(text: str | None, require_context: bool = True) -> tuple[float | None, float | None, str]:
    """Return ``(min_years, max_years, matched_text)`` for the first experience requirement.

    ``require_context=False`` is used for dedicated experience fields (e.g. a
    "0-1 years" badge), where the word "experience" is not repeated.

    >>> parse_experience("Experience: 0-2 years in Python")
    (0.0, 2.0, '0-2 years')
    """
    if not text:
        return None, None, ""
    candidates: list[tuple[int, float, float | None, str]] = []
    for pattern, kind in ((_RANGE_RE, "range"), (_MIN_RE, "min"), (_PLUS_RE, "plus"), (_PLAIN_RE, "plain")):
        for m in pattern.finditer(text):
            window = text[max(0, m.start() - 60): m.end() + 60].lower()
            # Ranges and "N+ years" must sit near the word "experience" to avoid
            # matching things like "a 4-year degree".
            if require_context and kind in {"range", "plus"} and "exp" not in window:
                continue
            lo = float(m.group(1))
            hi = float(m.group(2)) if kind == "range" else None
            if lo > 30 or (hi is not None and (hi > 40 or hi < lo)):
                continue
            candidates.append((m.start(), lo, hi, clean_whitespace(m.group(0))))
    if candidates:
        _, lo, hi, matched = min(candidates, key=lambda c: c[0])
        return lo, hi, matched
    m = _FRESHER_EXP_RE.search(text)
    if m:
        return 0.0, 1.0, clean_whitespace(m.group(0))
    return None, None, ""


# ---------------------------------------------------------------- salary
_CUR = r"(?:₹|rs\.?|inr|\$|usd)"
_AMT = r"\d[\d,]*(?:\.\d+)?\s*(?:lpa|lakhs?|lacs?|l|k|cr|crore)?"
_PERIOD = r"(?:\s*(?:per\s+(?:annum|month|year|hour)|/\s*(?:month|year|annum|hr)|p\.?\s?a\.?|ctc|stipend))?"
_SALARY_RES = [
    re.compile(rf"{_CUR}\s?{_AMT}(?:\s*(?:-|–|to)\s*{_CUR}?\s?{_AMT})?{_PERIOD}", re.I),
    re.compile(rf"\b\d{{1,2}}(?:\.\d)?\s*(?:-|–|to)\s*\d{{1,2}}(?:\.\d)?\s*(?:lpa|lakhs?\s+per\s+annum)\b", re.I),
    re.compile(r"\b\d{1,2}(?:\.\d)?\s*lpa\b", re.I),
]
_SALARY_CONTEXT = re.compile(r"salary|ctc|stipend|compensation|package|pay|lpa|per (?:annum|month)|₹|inr|\$", re.I)


def extract_salary(text: str | None) -> str:
    """Return the published salary/stipend text, or "" if none is stated."""
    if not text:
        return ""
    for pattern in _SALARY_RES:
        for m in pattern.finditer(text):
            snippet = clean_whitespace(m.group(0)).rstrip(".,;")
            window = text[max(0, m.start() - 40): m.end() + 20]
            if not re.search(r"\d", snippet) or not _SALARY_CONTEXT.search(window):
                continue
            # Ignore bare currency signs followed by tiny numbers (e.g. "$1").
            digits = re.sub(r"\D", "", snippet)
            if len(digits) < 1 or (snippet.startswith(("$", "₹")) and len(digits) < 2):
                continue
            return snippet
    return ""


# ---------------------------------------------------------------- deadline
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_DEADLINE_KEY = re.compile(
    r"(apply\s+by|last\s+date(?:\s+to\s+apply)?|application\s+deadline|deadline|applications?\s+close[sd]?(?:\s+on)?|closing\s+date)\s*[:\-–]?\s*",
    re.I,
)
_DATE_PATTERNS = [
    (re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"), "ymd"),
    (re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})"), "dmy"),
    (re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})"), "d_mon_y"),
    (re.compile(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"), "mon_d_y"),
]


def _to_date(groups: tuple[str, ...], kind: str) -> date | None:
    try:
        if kind == "ymd":
            return date(int(groups[0]), int(groups[1]), int(groups[2]))
        if kind == "dmy":  # Indian convention: day first
            return date(int(groups[2]), int(groups[1]), int(groups[0]))
        if kind == "d_mon_y":
            return date(int(groups[2]), _MONTHS[groups[1][:3].lower()], int(groups[0]))
        if kind == "mon_d_y":
            return date(int(groups[2]), _MONTHS[groups[0][:3].lower()], int(groups[1]))
    except (KeyError, ValueError):
        return None
    return None


def extract_deadline(text: str | None) -> str:
    """Return the application deadline as ISO ``YYYY-MM-DD`` if explicitly published."""
    if not text:
        return ""
    for key in _DEADLINE_KEY.finditer(text):
        tail = text[key.end(): key.end() + 40]
        for pattern, kind in _DATE_PATTERNS:
            m = pattern.match(tail.strip())
            if m:
                parsed = _to_date(m.groups(), kind)
                if parsed:
                    return parsed.isoformat()
    return ""


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


# ---------------------------------------------------------------- employment type / work mode
_EMPLOYMENT_RULES = [
    ("Internship", re.compile(r"\b(intern|interns|internship|summer intern)\b", re.I)),
    ("Apprenticeship", re.compile(r"\b(apprentice|apprenticeship)\b", re.I)),
    ("Graduate Trainee", re.compile(r"\b(graduate (?:engineer )?trainee|management trainee|trainee|graduate program(?:me)?)\b", re.I)),
    ("Contract", re.compile(r"\b(contract|contractual|temporary|fixed[- ]term)\b", re.I)),
    ("Part-time", re.compile(r"\bpart[- ]time\b", re.I)),
    ("Full-time", re.compile(r"\b(full[- ]time|permanent|regular employee|full time employee)\b", re.I)),
]


def detect_employment_type(title: str, description: str = "", hint: str = "") -> str:
    # Title first ("Graduate Engineer Trainee" beats a generic "Full Time" badge), then the
    # source's own employment field, then the description.
    for text in (title, hint, description):
        if not text:
            continue
        for label, pattern in _EMPLOYMENT_RULES:
            if pattern.search(text):
                return label
    return "Not specified"


_REMOTE_STRONG = re.compile(r"\b(remote|work from home|wfh|anywhere in india)\b", re.I)
_REMOTE_DESC = re.compile(r"\b(fully remote|remote[- ]first|remote role|remote position|this is a remote|100% remote|work from home|wfh)\b", re.I)
_HYBRID = re.compile(r"\bhybrid\b", re.I)
_ONSITE = re.compile(r"\b(on[- ]?site|in[- ]office|work from office|wfo)\b", re.I)


def detect_work_mode(location: str = "", description: str = "", hint: str = "") -> str:
    for text in (hint, location):
        if not text:
            continue
        if _HYBRID.search(text):
            return "Hybrid"
        if _REMOTE_STRONG.search(text):
            return "Remote"
        if _ONSITE.search(text):
            return "On-site"
    if description:
        if _REMOTE_DESC.search(description):
            return "Remote"
        if re.search(r"\bhybrid (?:work|role|model|mode|setup)\b", description, re.I):
            return "Hybrid"
        if _ONSITE.search(description):
            return "On-site"
    return "Unknown"


# ---------------------------------------------------------------- eligibility
_ELIGIBILITY_RE = re.compile(
    r"(b\.?\s?tech|b\.\s?e\b|\bbe\s*/\s*b\.?tech|\bbca\b|\bmca\b|m\.?\s?tech|b\.?\s?sc|m\.?\s?sc|bachelor|master'?s|"
    r"\bdegree\b|graduat(?:e|es|ion)\b|\bbatch\b|\bcgpa\b|percentage|eligib)",
    re.I,
)


def extract_eligibility(text: str | None, max_chars: int = 300) -> str:
    """Return the sentence(s) that state educational eligibility, if any."""
    if not text:
        return ""
    sentences = re.split(r"(?<=[.;!?])\s+|\n+|\s•\s|\s\|\s", text)
    picked: list[str] = []
    for s in sentences:
        s = clean_whitespace(s)
        if 10 <= len(s) <= 400 and _ELIGIBILITY_RE.search(s):
            picked.append(s)
        if len(" ".join(picked)) >= max_chars or len(picked) == 2:
            break
    result = " ".join(picked)
    return result if len(result) <= max_chars else result[: max_chars - 1].rsplit(" ", 1)[0] + "…"


# ---------------------------------------------------------------- category
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Data Science & AI", ["machine learning", "ml engineer", "ai engineer", "artificial intelligence", "data scientist",
                           "data science", "deep learning", "nlp", "computer vision", "genai", "generative ai", "llm"]),
    ("Data Analytics & BI", ["data analyst", "business intelligence", "analytics", "bi developer", "bi analyst", "power bi",
                             "tableau", "reporting analyst", "mis"]),
    ("Data Engineering", ["data engineer", "etl", "big data", "spark", "data platform", "data pipeline"]),
    ("Software Development", ["software engineer", "software developer", "developer", "sde", "backend", "back-end",
                              "frontend", "front-end", "full stack", "full-stack", "programmer", "android", "ios",
                              "mobile", "web", "java", "python developer"]),
    ("QA & Testing", ["qa", "quality assurance", "test engineer", "testing", "sdet", "automation tester"]),
    ("Cloud, DevOps & IT Infrastructure", ["devops", "cloud engineer", "cloud", "sre", "site reliability", "infrastructure",
                                           "platform engineer", "systems engineer", "network engineer", "it support",
                                           "technical support", "support engineer", "cloud support"]),
    ("Cybersecurity", ["security", "cybersecurity", "soc analyst", "soc", "cyber", "penetration", "vapt", "information security"]),
    ("UI/UX & Design", ["ui/ux", "ux", "ui designer", "product designer", "product design", "design intern", "designer",
                        "illustrator", "graphic"]),
    ("Embedded, Robotics & Hardware", ["embedded", "vlsi", "hardware", "firmware", "electronics", "iot", "asic", "robotics",
                                       "rtl", "verification engineer"]),
    ("Business, Product & Operations", ["business analyst", "consultant", "consulting", "product manager", "product management",
                                        "operations", "sales", "marketing", "finance", "financial analyst", "analyst",
                                        "compliance", "procurement", "hr"]),
]


def categorize_job(title: str, description: str = "") -> str:
    """Transparent keyword-rule categorisation (title hits weigh 3x description hits)."""
    title_l, desc_l = (title or "").lower(), (description or "").lower()
    best, best_score = "Other", 0
    for category, words in CATEGORY_RULES:
        score = 0
        for w in words:
            pattern = rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])"
            score += 3 * len(re.findall(pattern, title_l)) + min(len(re.findall(pattern, desc_l)), 3)
        if score > best_score:
            best, best_score = category, score
    return best


# ---------------------------------------------------------------- fresher classification
def is_fresher_friendly(title: str, description: str, min_exp: float | None, employment_type: str = "") -> bool:
    """Decide whether a job is open to freshers.

    Order of evidence: senior words in the *title* exclude the job; a parsed
    minimum experience of <= 1 year includes it; otherwise explicit fresher
    keywords (or an internship/trainee employment type) include it.
    """
    if has_senior_signal(title) and not (has_fresher_signal(title) and not has_strong_senior_signal(title)):
        # "Associate Product Manager – Fresher" stays; "Senior Analyst" or "Team Lead" does not.
        return False
    if min_exp is not None:
        return min_exp <= 1
    if employment_type in {"Internship", "Graduate Trainee", "Apprenticeship"}:
        return True
    return has_fresher_signal(title) or has_fresher_signal(description)


# ---------------------------------------------------------------- record builder
def build_job_record(raw: dict[str, Any], *, source: str, source_type: str, data_mode: str) -> JobRecord | None:
    """Normalise a raw scraped dict into a ``JobRecord``. Returns None if no title/company."""
    title = clean_whitespace(raw.get("title"))
    company = clean_whitespace(raw.get("company"))
    if not title or not company:
        return None
    # Drop a trailing " — Company" suffix that some career pages append to titles.
    title = re.sub(rf"\s*[—–|-]\s*{re.escape(company)}\s*$", "", title, flags=re.I) or title
    description = strip_html(raw.get("description", ""))
    location = clean_whitespace(raw.get("location"))
    full_text = f"{title}. {description}"

    lo, hi, exp_text = parse_experience(raw.get("experience_text"), require_context=False)
    if lo is None:
        lo, hi, exp_text = parse_experience(full_text)
    employment = clean_whitespace(raw.get("employment_type")) or detect_employment_type(
        title, description, raw.get("employment_hint", "")
    )
    if employment == "Internship" and lo is None:
        lo, hi, exp_text = 0.0, 0.0, exp_text or "Internship (no experience required)"

    skills = normalize_skill_list(raw.get("skills")) if raw.get("skills") else extract_skills(full_text)
    record = JobRecord(
        title=title,
        company=company,
        apply_url=normalize_url(raw.get("apply_url", "")),
        location=location,
        work_mode=raw.get("work_mode") or detect_work_mode(location, description, raw.get("workplace_hint", "")),
        experience_text=exp_text,
        min_experience_years=lo,
        max_experience_years=hi,
        employment_type=employment,
        description=description,
        skills=skills,
        eligibility=clean_whitespace(raw.get("eligibility")) or extract_eligibility(description),
        salary=clean_whitespace(raw.get("salary")) or extract_salary(description),
        deadline=raw.get("deadline") or extract_deadline(description),
        source=source,
        source_type=source_type,
        data_mode=data_mode,
        category=raw.get("category") or categorize_job(title, description),
        discovered_at=raw.get("discovered_at") or utc_now_iso(),
    )
    record.is_fresher_friendly = is_fresher_friendly(title, description, lo, employment)
    # When several jobs share one page URL (no per-job link), the URL cannot identify
    # a job, so the composite company|title|location key is used instead.
    id_url = "" if raw.get("url_is_shared") else record.apply_url
    record.job_id = make_job_id(id_url, record.company, record.title, record.location)
    return record
