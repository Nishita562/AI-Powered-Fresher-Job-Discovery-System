"""Dictionary-based skill extraction.

Skills are found by matching the aliases in ``config/skills.json`` on word
boundaries. This is deliberately transparent: every detected skill can be
traced back to an alias in the dictionary, and the user can correct the
result in the interface.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from config import settings
from src.text_utils import normalize_for_matching


@lru_cache(maxsize=4)
def load_skill_dictionary(path: str | None = None) -> dict[str, dict[str, list[str]]]:
    """Return ``{group: {canonical_skill: [aliases]}}``."""
    data = json.loads(Path(path or settings.SKILLS_JSON).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache(maxsize=4)
def _compiled_patterns(path: str | None = None) -> list[tuple[str, re.Pattern[str]]]:
    patterns = []
    for group in load_skill_dictionary(path).values():
        for canonical, aliases in group.items():
            # Only the aliases are matched: canonical names such as "go", "r" or "c" are
            # ordinary words/letters and would cause false positives on their own.
            alts = sorted({normalize_for_matching(a) for a in aliases}, key=len, reverse=True)
            body = "|".join(re.escape(a) for a in alts if a)
            # Custom boundaries: '+', '#' and alphanumerics continue a token, so
            # "java" does not match inside "javascript" and "c" not inside "c++".
            patterns.append((canonical, re.compile(rf"(?<![a-z0-9+#])(?:{body})(?![a-z0-9+#])")))
    return patterns


def all_skills() -> list[str]:
    return sorted({skill for group in load_skill_dictionary().values() for skill in group})


def skill_group_map() -> dict[str, str]:
    return {skill: group for group, skills in load_skill_dictionary().items() for skill in skills}


def extract_skills(text: str | None) -> list[str]:
    """Return canonical skills mentioned in ``text`` (sorted, unique)."""
    norm = normalize_for_matching(text)
    if not norm:
        return []
    return sorted({canonical for canonical, pattern in _compiled_patterns() if pattern.search(norm)})


def normalize_skill_list(skills: list[str] | str | None) -> list[str]:
    """Map free-text skills (e.g. typed by a user) to canonical names where possible.

    Unknown skills are kept in lower case so that user input is never discarded.
    """
    if not skills:
        return []
    if isinstance(skills, str):
        skills = re.split(r"[,;\n]", skills)
    result: set[str] = set()
    for raw in skills:
        raw = raw.strip()
        if not raw:
            continue
        found = extract_skills(raw)
        result.update(found if found else [normalize_for_matching(raw)])
    return sorted(s for s in result if s)
