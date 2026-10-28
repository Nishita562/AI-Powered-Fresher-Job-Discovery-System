"""Fresher / entry-level keyword rules (ported from the Node.js prototype).

Changes from ``legacy/nodejs_prototype/src/keywords.js``:
* matching now uses word boundaries — the original substring test made
  "intern" match "internal"/"international" and "lead" match "leadership";
* experience ranges are parsed numerically by ``extractors.parse_experience``
  instead of relying only on fixed strings such as "0-1 year".
"""

from __future__ import annotations

import re

FRESHER_KEYWORDS = [
    "fresher", "freshers", "entry level", "entry-level", "graduate trainee",
    "graduate program", "graduate programme", "campus hire", "campus placement",
    "no experience required", "trainee engineer", "management trainee",
    "associate trainee", "trainee", "intern", "interns", "internship", "early career",
    "early talent", "new grad", "new graduate", "recent graduate", "university graduate",
    "apprentice", "apprenticeship", "junior", "associate software engineer",
    "graduate engineer trainee", "sde-1", "sde 1", "sde i", "software engineer i",
]

SENIOR_EXCLUSION_KEYWORDS = [
    "senior", "sr.", "sr", "lead", "principal", "staff", "architect", "director",
    "vice president", "vp", "head of", "manager", "chief", "distinguished",
]

# Senior words that can never describe an entry-level role (unlike "manager"/"architect",
# which appear in titles such as "Associate Product Manager").
STRONG_SENIOR_KEYWORDS = ["senior", "sr.", "sr", "lead", "principal", "staff", "director", "vice president", "vp",
                          "head of", "chief", "distinguished"]

ROLE_KEYWORDS = [
    "software engineer", "software developer", "sde", "developer", "programmer",
    "data analyst", "data scientist", "data engineer", "machine learning", "ml engineer",
    "ai engineer", "qa engineer", "test engineer", "systems engineer", "associate engineer",
    "it analyst", "support engineer", "web developer", "full stack", "backend",
    "frontend", "devops", "cloud engineer", "security analyst", "business analyst",
]


def _compile(words: list[str]) -> re.Pattern[str]:
    body = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<![a-z0-9])(?:{body})(?![a-z0-9])", re.IGNORECASE)


_FRESHER_RE = _compile(FRESHER_KEYWORDS)
_SENIOR_RE = _compile(SENIOR_EXCLUSION_KEYWORDS)
_ROLE_RE = _compile(ROLE_KEYWORDS)
_STRONG_SENIOR_RE = _compile(STRONG_SENIOR_KEYWORDS)


def has_fresher_signal(text: str) -> bool:
    return bool(text and _FRESHER_RE.search(text))


def has_senior_signal(text: str) -> bool:
    return bool(text and _SENIOR_RE.search(text))


def has_strong_senior_signal(text: str) -> bool:
    return bool(text and _STRONG_SENIOR_RE.search(text))


def has_role_signal(text: str) -> bool:
    return bool(text and _ROLE_RE.search(text))


def matched_keywords(text: str, kind: str = "fresher") -> list[str]:
    pattern = {"fresher": _FRESHER_RE, "senior": _SENIOR_RE, "role": _ROLE_RE}[kind]
    return sorted({m.group(0).lower() for m in pattern.finditer(text or "")})
