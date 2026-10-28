"""Explainable job recommendation using TF-IDF vectors and cosine similarity.

Pipeline
--------
1. Each job becomes a text document: title (repeated for weight) + skills +
   category + experience text + description.
2. The candidate profile becomes one document: skills + preferred roles +
   optional resume text.
3. ``TfidfVectorizer`` is fitted on the job corpus; the profile is projected
   into the same vocabulary.
4. Cosine similarity between the profile vector and every job vector is
   computed. Because a short profile is compared with long descriptions, raw
   cosine values are small (typically 0.0–0.3), so ``S_text`` is the cosine
   divided by the highest cosine in the current dataset (best match = 1.0).
   The raw cosine is still reported for transparency.
5. A transparent composite score is computed per job::

       base  = (0.50·S_text + 0.30·S_skill + 0.20·S_pref) / (sum of weights used)
       score = 100 · base · F_elig

   where ``S_skill`` = share of the job's listed skills the candidate has,
   ``S_pref`` = mean of role-match and location-match, and ``F_elig`` is an
   experience-eligibility factor (1.0 eligible, 0.9 unknown, 0.5 requires
   more experience). A component that cannot be computed (e.g. the job lists
   no skills) is left out and its weight is redistributed.

The score is a *relevance* score for ranking. It is not a probability of
being shortlisted or hired, and the weights are illustrative defaults
rather than values learned from data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from src.skills import extract_skills, normalize_skill_list
from src.text_utils import normalize_for_matching

_SPECIAL_TOKENS = [("c++", " cplusplus "), ("c#", " csharp "), ("node.js", " nodejs "), (".net", " dotnet "),
                   ("ci/cd", " cicd "), ("a/b", " abtesting "), ("ui/ux", " uiux "), ("pl/sql", " plsql ")]
_ROLE_STOP = set(ENGLISH_STOP_WORDS) | {"role", "job", "position", "opening", "level"}


def preprocess(text: str) -> str:
    """Normalise text for TF-IDF, protecting skill names that contain symbols."""
    text = normalize_for_matching(text)
    for raw, token in _SPECIAL_TOKENS:
        text = text.replace(raw, token)
    return re.sub(r"[./-]", " ", text)


def build_job_document(job: dict | pd.Series) -> str:
    skills = job.get("skills") or []
    if isinstance(skills, str):
        skills = [s for s in skills.split(",") if s]
    parts = [str(job.get("title", ""))] * settings.TITLE_WEIGHT_REPEAT
    parts += [" ".join(skills), str(job.get("category", "")), str(job.get("experience_text", "")),
              str(job.get("employment_type", "")), str(job.get("description", ""))]
    return " ".join(p for p in parts if p)


@dataclass
class CandidateProfile:
    skills: list[str] = field(default_factory=list)
    preferred_roles: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    accept_remote: bool = True
    resume_text: str = ""

    def normalized_skills(self) -> set[str]:
        return set(normalize_skill_list(self.skills))

    def is_empty(self) -> bool:
        return not (self.skills or self.preferred_roles or self.resume_text.strip())

    def to_document(self) -> str:
        # Preferred roles are repeated once so they weigh a little more than a single skill.
        return " ".join(self.skills + self.preferred_roles * 2 + [self.resume_text])


@dataclass
class Recommendation:
    job_id: str
    score: float                    # 0–100 relevance score (not a hiring probability)
    text_similarity: float          # raw cosine similarity in [0, 1]
    text_relative: float            # cosine / best cosine in the dataset (used in the score)
    skill_score: float | None       # share of job skills matched, None if job lists none
    preference_score: float | None
    eligibility: str                # eligible / unknown / not_eligible
    matched_skills: list[str]
    missing_skills: list[str]
    role_match: float | None
    location_match: float | None
    explanation: str


class JobRecommender:
    """Fit once on a job DataFrame, then rank jobs for any candidate profile."""

    def __init__(self, jobs: pd.DataFrame, weights: tuple[float, float, float] | None = None):
        self.jobs = jobs.reset_index(drop=True)
        self.weights = weights or (settings.WEIGHT_TEXT_SIMILARITY, settings.WEIGHT_SKILL_MATCH, settings.WEIGHT_PREFERENCE)
        if abs(sum(self.weights) - 1.0) > 1e-6:
            raise ValueError("Recommendation weights must sum to 1.0")
        self.vectorizer = TfidfVectorizer(
            preprocessor=preprocess,
            stop_words="english",
            ngram_range=settings.TFIDF_NGRAM_RANGE,
            sublinear_tf=True,
            max_features=settings.TFIDF_MAX_FEATURES,
        )
        self.job_matrix = None
        docs = [build_job_document(row) for _, row in self.jobs.iterrows()]
        if docs:
            try:
                self.job_matrix = self.vectorizer.fit_transform(docs)
            except ValueError:  # every document empty -> empty vocabulary
                self.job_matrix = None

    # ------------------------------------------------------------ components
    def text_similarities(self, profile: CandidateProfile) -> np.ndarray:
        if self.job_matrix is None or not profile.to_document().strip():
            return np.zeros(len(self.jobs))
        vec = self.vectorizer.transform([profile.to_document()])
        return cosine_similarity(vec, self.job_matrix).ravel()

    @staticmethod
    def job_skills(job: pd.Series) -> set[str]:
        skills = job.get("skills")
        if isinstance(skills, list) and skills:
            return set(skills)
        return set(extract_skills(f"{job.get('title', '')}. {job.get('description', '')}"))

    @staticmethod
    def role_match(profile: CandidateProfile, title: str) -> float | None:
        if not profile.preferred_roles:
            return None
        title_tokens = set(normalize_for_matching(title).replace("/", " ").split())
        best = 0.0
        for role in profile.preferred_roles:
            tokens = [t for t in normalize_for_matching(role).split() if t not in _ROLE_STOP]
            if tokens:
                best = max(best, sum(t in title_tokens for t in tokens) / len(tokens))
        return best

    @staticmethod
    def location_match(profile: CandidateProfile, location: str, work_mode: str) -> float | None:
        prefs = [p.strip().lower() for p in profile.preferred_locations if p.strip()]
        if not prefs:
            return None
        loc = (location or "").lower()
        if any(p in loc for p in prefs if p != "remote"):
            return 1.0
        if work_mode == "Remote" and (profile.accept_remote or "remote" in prefs):
            return 1.0
        return 0.0

    @staticmethod
    def eligibility(profile: CandidateProfile, min_exp) -> str:
        if min_exp is None or (isinstance(min_exp, float) and np.isnan(min_exp)):
            return "unknown"
        return "eligible" if float(min_exp) <= profile.experience_years else "not_eligible"

    # ------------------------------------------------------------ ranking
    def score_all(self, profile: CandidateProfile) -> list[Recommendation]:
        if self.jobs.empty:
            return []
        if profile.is_empty():
            raise ValueError("The candidate profile is empty. Add skills, a preferred role or a resume.")
        sims = self.text_similarities(profile)
        best = float(sims.max()) if len(sims) else 0.0
        cand_skills = profile.normalized_skills()
        w_text, w_skill, w_pref = self.weights
        results = []
        for i, job in self.jobs.iterrows():
            s_raw = float(sims[i])
            s_text = s_raw / best if best > 0 else 0.0
            jskills = self.job_skills(job)
            matched = sorted(cand_skills & jskills)
            missing = sorted(jskills - cand_skills)
            s_skill = len(matched) / len(jskills) if jskills else None
            r_match = self.role_match(profile, job.get("title", ""))
            l_match = self.location_match(profile, job.get("location", ""), job.get("work_mode", ""))
            prefs = [v for v in (r_match, l_match) if v is not None]
            s_pref = sum(prefs) / len(prefs) if prefs else None

            weighted, used = w_text * s_text, w_text
            if s_skill is not None:
                weighted, used = weighted + w_skill * s_skill, used + w_skill
            if s_pref is not None:
                weighted, used = weighted + w_pref * s_pref, used + w_pref
            elig = self.eligibility(profile, job.get("min_experience_years"))
            score = 100.0 * (weighted / used) * settings.ELIGIBILITY_FACTORS[elig]

            results.append(Recommendation(
                job_id=job["job_id"], score=round(score, 1), text_similarity=round(s_raw, 4), text_relative=round(s_text, 4),
                skill_score=None if s_skill is None else round(s_skill, 4),
                preference_score=None if s_pref is None else round(s_pref, 4),
                eligibility=elig, matched_skills=matched, missing_skills=missing,
                role_match=r_match, location_match=l_match,
                explanation=self._explain(job, s_raw, s_text, matched, jskills, r_match, l_match, elig, profile),
            ))
        results.sort(key=lambda r: (r.score, r.text_similarity), reverse=True)
        return results

    def recommend(self, profile: CandidateProfile, top_n: int = 10, hide_ineligible: bool = False) -> list[Recommendation]:
        recs = self.score_all(profile)
        if hide_ineligible:
            recs = [r for r in recs if r.eligibility != "not_eligible"]
        return recs[:top_n]

    def similar_jobs(self, job_id: str, top_n: int = 5) -> list[tuple[str, float]]:
        """Content-based 'more like this': cosine similarity between job vectors."""
        if self.job_matrix is None:
            return []
        idx = self.jobs.index[self.jobs["job_id"] == job_id]
        if len(idx) == 0:
            return []
        sims = cosine_similarity(self.job_matrix[idx[0]], self.job_matrix).ravel()
        order = [j for j in np.argsort(-sims) if j != idx[0]][:top_n]
        return [(self.jobs.loc[j, "job_id"], round(float(sims[j]), 4)) for j in order]

    def top_terms(self, job_id: str, n: int = 8) -> list[str]:
        """Highest-weighted TF-IDF terms of a job — a lightweight keyword extractor."""
        if self.job_matrix is None:
            return []
        idx = self.jobs.index[self.jobs["job_id"] == job_id]
        if len(idx) == 0:
            return []
        row = self.job_matrix[idx[0]].toarray().ravel()
        terms = self.vectorizer.get_feature_names_out()
        return [terms[i] for i in np.argsort(-row)[:n] if row[i] > 0]

    @staticmethod
    def _explain(job, s_raw, s_text, matched, jskills, r_match, l_match, elig, profile) -> str:
        parts = [f"Text similarity {s_raw:.2f} ({s_text:.0%} of the best match)"]
        if jskills:
            parts.append(f"matches {len(matched)}/{len(jskills)} listed skills"
                         + (f" ({', '.join(matched[:5])})" if matched else ""))
        else:
            parts.append("job lists no recognisable skills, so skill match was not scored")
        if r_match is not None:
            parts.append("title matches your preferred role" if r_match >= 0.5 else "title differs from your preferred roles")
        if l_match is not None:
            parts.append("location fits your preference" if l_match else "location outside your preference")
        parts.append({
            "eligible": "experience requirement fits",
            "unknown": "experience requirement not stated (score ×0.9)",
            "not_eligible": f"asks for {job.get('min_experience_years'):.0f}+ years — more than your {profile.experience_years:g} (score ×0.5)"
            if job.get("min_experience_years") is not None else "experience mismatch",
        }[elig])
        return "; ".join(parts) + "."


def recommendations_to_frame(recs: list[Recommendation], jobs: pd.DataFrame) -> pd.DataFrame:
    if not recs:
        return pd.DataFrame()
    rec_df = pd.DataFrame([r.__dict__ for r in recs])
    merged = rec_df.merge(jobs, on="job_id", how="left")
    return merged.rename(columns={"score": "match_score"})


def score_jobs_frame(jobs: pd.DataFrame, profile: CandidateProfile) -> pd.DataFrame:
    """Add a ``match_score`` column to ``jobs`` (used for 'sort by relevance')."""
    if jobs.empty or profile.is_empty():
        return jobs.assign(match_score=np.nan)
    recs = JobRecommender(jobs).score_all(profile)
    scores = {r.job_id: r.score for r in recs}
    return jobs.assign(match_score=jobs["job_id"].map(scores))
