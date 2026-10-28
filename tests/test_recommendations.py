import math

import numpy as np
import pandas as pd
import pytest

from config import settings
from src.recommendation import CandidateProfile, JobRecommender, build_job_document, preprocess, score_jobs_frame
from tests.conftest import make_job

ML_PROFILE = CandidateProfile(skills=["python", "machine learning", "pandas", "scikit-learn"],
                              preferred_roles=["Machine Learning Engineer"], preferred_locations=["Bengaluru"])


def test_preprocess_protects_symbol_skills():
    text = preprocess("C++, C#, Node.js and CI/CD")
    assert "cplusplus" in text and "csharp" in text and "nodejs" in text and "cicd" in text


def test_tfidf_matrix_shape(jobs_df):
    rec = JobRecommender(jobs_df)
    assert rec.job_matrix.shape[0] == len(jobs_df)
    assert rec.job_matrix.shape[1] > 10


def test_cosine_similarity_of_identical_text_is_one(jobs_df):
    rec = JobRecommender(jobs_df)
    doc = build_job_document(jobs_df.iloc[0])
    sims = rec.text_similarities(CandidateProfile(resume_text=doc))
    assert math.isclose(sims[0], 1.0, rel_tol=1e-6)
    assert sims.argmax() == 0


def test_ml_profile_ranks_ml_job_first(jobs_df):
    recs = JobRecommender(jobs_df).score_all(ML_PROFILE)
    titles = jobs_df.set_index("job_id").loc[[r.job_id for r in recs], "title"].tolist()
    assert titles[0] == "Machine Learning Intern"
    assert titles.index("Machine Learning Intern") < titles.index("HR Intern")


def test_score_matches_documented_formula(jobs_df):
    for r in JobRecommender(jobs_df).score_all(ML_PROFILE):
        parts = [(settings.WEIGHT_TEXT_SIMILARITY, r.text_relative)]
        if r.skill_score is not None:
            parts.append((settings.WEIGHT_SKILL_MATCH, r.skill_score))
        if r.preference_score is not None:
            parts.append((settings.WEIGHT_PREFERENCE, r.preference_score))
        expected = 100 * sum(w * s for w, s in parts) / sum(w for w, _ in parts) * settings.ELIGIBILITY_FACTORS[r.eligibility]
        assert abs(expected - r.score) < 0.1
        assert 0 <= r.score <= 100


def test_relative_text_similarity_is_scaled_to_best_match(jobs_df):
    recs = JobRecommender(jobs_df).score_all(ML_PROFILE)
    assert max(r.text_relative for r in recs) == pytest.approx(1.0)
    best = max(recs, key=lambda r: r.text_similarity)
    for r in recs:
        assert r.text_relative == pytest.approx(r.text_similarity / best.text_similarity, abs=1e-3)


def test_eligibility_penalises_senior_job(jobs_df):
    recs = {r.job_id: r for r in JobRecommender(jobs_df).score_all(ML_PROFILE)}
    senior = jobs_df[jobs_df["title"] == "Senior Data Scientist"].iloc[0]["job_id"]
    assert recs[senior].eligibility == "not_eligible"
    hidden = JobRecommender(jobs_df).recommend(ML_PROFILE, top_n=10, hide_ineligible=True)
    assert senior not in {r.job_id for r in hidden}


def test_no_matching_skills_gives_zero_skill_score(jobs_df):
    profile = CandidateProfile(skills=["verilog"])
    for r in JobRecommender(jobs_df).score_all(profile):
        if r.skill_score is not None:
            assert r.skill_score == 0 and r.matched_skills == []


def test_job_without_skills_redistributes_weight():
    df = pd.DataFrame([make_job("Office Assistant", description="Help the office team every day.").to_dict(),
                       make_job("Python Developer", description="Python and Django").to_dict()])
    recs = {r.job_id: r for r in JobRecommender(df).score_all(CandidateProfile(skills=["python"]))}
    no_skill = recs[df.iloc[0]["job_id"]]
    assert no_skill.skill_score is None and "not scored" in no_skill.explanation


def test_empty_profile_raises(jobs_df):
    with pytest.raises(ValueError):
        JobRecommender(jobs_df).score_all(CandidateProfile())


def test_empty_job_set_returns_nothing():
    assert JobRecommender(pd.DataFrame()).score_all(ML_PROFILE) == []


def test_all_empty_descriptions_do_not_crash():
    df = pd.DataFrame([{"job_id": "1", "title": "", "skills": [], "description": ""},
                       {"job_id": "2", "title": "", "skills": [], "description": ""}])
    rec = JobRecommender(df)
    assert rec.job_matrix is None
    assert np.all(rec.text_similarities(ML_PROFILE) == 0)


def test_duplicate_jobs_get_identical_scores(jobs_df):
    dup = pd.concat([jobs_df.iloc[[0]], jobs_df.iloc[[0]].assign(job_id="copy")], ignore_index=True)
    a, b = JobRecommender(dup).score_all(ML_PROFILE)
    assert a.score == b.score and a.text_similarity == b.text_similarity


def test_weights_must_sum_to_one(jobs_df):
    with pytest.raises(ValueError):
        JobRecommender(jobs_df, weights=(0.5, 0.5, 0.5))


def test_similar_jobs_and_keywords(jobs_df):
    rec = JobRecommender(jobs_df)
    jid = jobs_df.iloc[0]["job_id"]
    similar = rec.similar_jobs(jid, 3)
    assert len(similar) == 3 and jid not in [s[0] for s in similar]
    assert rec.top_terms(jid, 5)


def test_score_jobs_frame_adds_column(jobs_df):
    out = score_jobs_frame(jobs_df, ML_PROFILE)
    assert out["match_score"].notna().all()
    assert score_jobs_frame(jobs_df, CandidateProfile())["match_score"].isna().all()
