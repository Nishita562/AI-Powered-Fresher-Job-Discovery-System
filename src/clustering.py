"""Unsupervised grouping of jobs with K-Means on TF-IDF vectors.

No labels are needed, so no training data is fabricated. The number of
clusters is chosen by the silhouette coefficient (cosine distance), which
is reported honestly with the result.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

from src.recommendation import build_job_document, preprocess


@dataclass
class ClusterResult:
    labels: np.ndarray
    k: int
    silhouette: float
    top_terms: dict[int, list[str]]
    silhouette_by_k: dict[int, float]


def cluster_jobs(jobs: pd.DataFrame, k_min: int = 3, k_max: int = 10, random_state: int = 42) -> ClusterResult | None:
    if len(jobs) < k_min + 2:
        return None
    docs = [build_job_document(row) for _, row in jobs.iterrows()]
    vec = TfidfVectorizer(preprocessor=preprocess, stop_words="english", max_features=3000, min_df=2, sublinear_tf=True)
    try:
        X = vec.fit_transform(docs)
    except ValueError:
        return None
    terms = vec.get_feature_names_out()
    scores: dict[int, float] = {}
    models: dict[int, KMeans] = {}
    for k in range(k_min, min(k_max, len(jobs) - 1) + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=random_state).fit(X)
        if len(set(km.labels_)) < 2:
            continue
        scores[k] = float(silhouette_score(X, km.labels_, metric="cosine"))
        models[k] = km
    if not scores:
        return None
    best_k = max(scores, key=scores.get)
    km = models[best_k]
    top = {c: [terms[i] for i in np.argsort(-km.cluster_centers_[c])[:6]] for c in range(best_k)}
    return ClusterResult(labels=km.labels_, k=best_k, silhouette=scores[best_k], top_terms=top, silhouette_by_k=scores)
