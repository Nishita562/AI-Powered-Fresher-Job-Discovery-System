"""Duplicate detection for job records.

Primary key: SHA-1 of the normalised application URL (tracking parameters,
fragments and trailing slashes removed). When a URL is missing, a composite
key of company + title + location is hashed instead. A second pass also
collapses records whose composite key matches even if their URLs differ
(the same job cross-posted on two pages).
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

if TYPE_CHECKING:  # pragma: no cover
    from src.models import JobRecord

_TRACKING_PARAMS = re.compile(r"^(utm_|gh_src|gh_jid_src|lever-source|source$|ref$|src$|fbclid|gclid)", re.I)


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not parts.scheme:
        return url
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING_PARAMS.match(k)])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _norm(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def composite_key(company: str, title: str, location: str) -> str:
    return f"{_norm(company)}|{_norm(title)}|{_norm(location)}"


def make_job_id(apply_url: str, company: str, title: str, location: str) -> str:
    basis = normalize_url(apply_url) or composite_key(company, title, location)
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def _richness(rec: "JobRecord") -> int:
    return len(rec.description or "") + 50 * len(rec.skills or []) + (20 if rec.salary else 0) + (20 if rec.deadline else 0)


def deduplicate(records: Iterable["JobRecord"]) -> tuple[list["JobRecord"], int]:
    """Return ``(unique_records, duplicates_removed)``.

    When two records collide, the one with more information is kept and the
    earliest ``discovered_at`` timestamp is preserved.
    """
    by_id: dict[str, "JobRecord"] = {}
    by_composite: dict[str, str] = {}
    duplicates = 0
    for rec in records:
        ckey = composite_key(rec.company, rec.title, rec.location)
        existing_id = rec.job_id if rec.job_id in by_id else by_composite.get(ckey)
        if existing_id is None:
            by_id[rec.job_id] = rec
            by_composite[ckey] = rec.job_id
            continue
        duplicates += 1
        current = by_id[existing_id]
        keep = rec if _richness(rec) > _richness(current) else current
        keep.discovered_at = min(current.discovered_at, rec.discovered_at)
        keep.job_id = existing_id
        by_id[existing_id] = keep
    return list(by_id.values()), duplicates
