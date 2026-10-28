"""Text normalisation helpers used before extraction, matching and TF-IDF."""

from __future__ import annotations

import html
import re
import unicodedata

_WS = re.compile(r"\s+")
_TAG = re.compile(r"<[^>]+>")
_NON_TEXT = re.compile(r"[^a-z0-9+#./\s-]")


def clean_whitespace(text: str | None) -> str:
    """Collapse runs of whitespace (including non-breaking spaces) into single spaces."""
    if not text:
        return ""
    text = text.replace(" ", " ").replace("​", "")
    return _WS.sub(" ", text).strip()


def clean_multiline(text: str | None) -> str:
    """Like ``clean_whitespace`` but keeps line breaks (at most one blank line in a row)."""
    if not text:
        return ""
    lines = [clean_whitespace(line) for line in text.replace("\r", "\n").split("\n")]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


_BLOCK_TAG = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr)\b[^>]*>", re.I)


def strip_html(text: str | None) -> str:
    """Remove HTML tags and decode entities, keeping paragraph/line structure."""
    if not text:
        return ""
    text = _BLOCK_TAG.sub("\n", text)
    return clean_multiline(html.unescape(_TAG.sub(" ", text)))


def normalize_for_matching(text: str | None) -> str:
    """Lower-case, strip accents and punctuation (keeping + # . / - used in skill names)."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("–", "-").replace("—", "-")
    text = _NON_TEXT.sub(" ", text)
    return clean_whitespace(text)


def truncate(text: str, limit: int = 280) -> str:
    text = clean_whitespace(text)
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"
