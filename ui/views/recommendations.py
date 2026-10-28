"""AI Recommendations page: candidate profile, optional resume parsing, ranked explainable matches."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from src.recommendation import CandidateProfile
from src.resume_parser import ResumeParseError, parse_resume
from src.skills import all_skills, normalize_skill_list
from ui import state
from ui.components import (ELIGIBILITY_BADGE, badge, chips, empty_state, job_details, notice, page_header,
                           recommendation_breakdown, render_link_button, save_job, score_html)
from ui.components import esc


def _resume_section() -> None:
    with st.expander("Optional: extract skills from your resume (PDF or DOCX)", expanded=bool(st.session_state.resume_skills)):
        notice("<b>Privacy:</b> the file is read in memory on this computer only. It is not uploaded to any server, "
               "not written to disk and not stored in the database. The extracted text is kept only for this browser "
               "session and is cleared when you press <i>Clear resume</i> or close the app.", "info")
        upload = st.file_uploader("Resume file", type=["pdf", "docx"], accept_multiple_files=False,
                                  help=f"PDF or DOCX, up to {settings.MAX_RESUME_MB} MB. Scanned images cannot be read.")
        c1, c2 = st.columns(2)
        if c1.button("Extract skills", disabled=upload is None, icon=":material/document_scanner:", width="stretch"):
            try:
                parsed = parse_resume(upload.getvalue(), upload.name)
                st.session_state.resume_text = parsed["text"]
                st.session_state.resume_skills = parsed["skills"]
                st.session_state.resume_name = upload.name
                st.session_state.rec_skills = sorted(set(st.session_state.get("rec_skills", [])) | set(parsed["skills"]))
                state.flash(f"Read {parsed['characters']:,} characters from {upload.name} and found "
                            f"{len(parsed['skills'])} skills. Review them below before searching.")
            except ResumeParseError as exc:
                state.flash(str(exc), "error")
            st.rerun()
        if c2.button("Clear resume", disabled=not st.session_state.resume_text, icon=":material/delete:", width="stretch"):
            st.session_state.resume_text, st.session_state.resume_skills, st.session_state.resume_name = "", [], ""
            st.rerun()
        if st.session_state.resume_name:
            st.markdown(f"Detected in **{esc(st.session_state.resume_name)}**: " + (chips(st.session_state.resume_skills, limit=40)
                        or "no dictionary skills found"), unsafe_allow_html=True)
            st.caption("These were added to the skills box above the form — remove any that are wrong.")


def _profile_form() -> CandidateProfile | None:
    prof: CandidateProfile | None = st.session_state.profile
    if "rec_skills" not in st.session_state:
        st.session_state.rec_skills = list(prof.skills) if prof else []
    options = sorted(set(all_skills()) | set(st.session_state.rec_skills))
    with st.form("profile_form", border=True):
        st.markdown("**Your profile**")
        skills = st.multiselect("Skills", options, key="rec_skills", placeholder="Choose from the skill dictionary",
                                help="Detected resume skills are pre-selected here so you can confirm or correct them.")
        extra = st.text_input("Other skills (comma-separated)", placeholder="e.g. opencv, fastapi, power bi")
        c1, c2 = st.columns(2)
        roles = c1.text_input("Preferred job roles (comma-separated)",
                              value=", ".join(prof.preferred_roles) if prof else "",
                              placeholder="e.g. Data Analyst, Machine Learning Engineer")
        locations = c2.text_input("Preferred locations (comma-separated)",
                                  value=", ".join(prof.preferred_locations) if prof else "",
                                  placeholder="e.g. Bengaluru, Pune, Remote")
        c3, c4, c5 = st.columns(3)
        experience = c3.number_input("Your experience (years)", 0.0, 15.0, float(prof.experience_years) if prof else 0.0, 0.5)
        accept_remote = c4.checkbox("Remote jobs are fine", value=prof.accept_remote if prof else True)
        hide_inel = c5.checkbox("Hide jobs that need more experience", value=st.session_state.get("rec_hide", True))
        top_n = st.slider("Number of recommendations", 5, 30, st.session_state.get("rec_topn", 10))
        submitted = st.form_submit_button("Get recommendations", type="primary", icon=":material/auto_awesome:")
    if not submitted:
        return None
    all_sk = normalize_skill_list(list(skills) + [s for s in extra.split(",") if s.strip()])
    profile = CandidateProfile(
        skills=all_sk,
        preferred_roles=[r.strip() for r in roles.split(",") if r.strip()],
        preferred_locations=[l.strip() for l in locations.split(",") if l.strip()],
        experience_years=float(experience), accept_remote=accept_remote,
        resume_text=st.session_state.resume_text,
    )
    st.session_state.rec_hide, st.session_state.rec_topn = hide_inel, top_n
    if profile.is_empty():
        st.error("Please add at least one skill, a preferred role or a resume before searching.")
        return None
    st.session_state.profile, st.session_state.profile_is_demo = profile, False
    return profile


def _recommendation_card(rank: int, rec, job: dict, tracked: bool) -> None:
    with st.container(border=True):
        a, b, c = st.columns([0.9, 4.2, 1.5], vertical_alignment="top")
        with a:
            st.markdown(score_html(rec.score, f"#{rank} relevance"), unsafe_allow_html=True)
        with b:
            elig, css = ELIGIBILITY_BADGE[rec.eligibility]
            st.markdown(f'<div class="job-title">{esc(job["title"])}</div>'
                        f'<div class="job-meta">{esc(job["company"])} · {esc(job.get("location") or "Location not stated")}</div>'
                        + badge(elig, css) + badge(job.get("employment_type") or "Not specified"), unsafe_allow_html=True)
            if rec.matched_skills:
                st.markdown('<span class="small-muted">Matched:</span> ' + chips(rec.matched_skills, "chip chip-match"),
                            unsafe_allow_html=True)
            if rec.missing_skills:
                st.markdown('<span class="small-muted">Not in your profile:</span> ' + chips(rec.missing_skills, "chip chip-miss"),
                            unsafe_allow_html=True)
            st.caption(rec.explanation)
        with c:
            st.markdown(recommendation_breakdown(rec, with_badge=False), unsafe_allow_html=True)
            if st.button("Details", key=f"rd_{job['job_id']}", width="stretch", icon=":material/description:"):
                job_details(job)
            if tracked:
                st.button("Saved", key=f"rs_{job['job_id']}", disabled=True, width="stretch")
            else:
                st.button("Save", key=f"rs_{job['job_id']}", width="stretch", on_click=save_job, args=(job,))
            render_link_button(job, f"rec_{job['job_id']}")


def render() -> None:
    state.show_flash()
    page_header("AI Job Recommendations",
                "TF-IDF text vectors + cosine similarity, combined with skill, preference and eligibility checks.")
    jobs = state.get_jobs()
    if jobs.empty:
        empty_state("No job records to recommend from", "Load the sample dataset or run a crawl first.")
        return
    _resume_section()
    if st.button("Fill in the demo profile", help="Example AIML-student profile so the panel can see the feature quickly"):
        st.session_state.rec_skills = list(state.DEMO_PROFILE.skills)
        st.session_state.profile, st.session_state.profile_is_demo = state.DEMO_PROFILE, True
        st.rerun()
    _profile_form()
    profile = st.session_state.profile
    with st.expander("How is the relevance score calculated?"):
        st.markdown(f"""
* **Text similarity** — your skills, preferred roles and resume text are turned into a TF-IDF vector and compared with each
  job's TF-IDF vector (title, skills, experience text and description) using cosine similarity. Because a short profile is
  compared with long descriptions, raw cosine values are small, so the score uses the cosine **relative to the best match in
  the current dataset** (best = 1.0). The raw cosine is shown next to every bar.
* **Skill match** — share of the job's listed skills that appear in your profile.
* **Preference** — average of *role match* (share of your preferred-role words found in the job title) and *location match*.
* **Eligibility factor** — ×{settings.ELIGIBILITY_FACTORS['eligible']} if the job's minimum experience fits yours,
  ×{settings.ELIGIBILITY_FACTORS['unknown']} if the job does not state it, ×{settings.ELIGIBILITY_FACTORS['not_eligible']} if it asks for more.

`score = 100 × F_elig × ({settings.WEIGHT_TEXT_SIMILARITY}·S_text_rel + {settings.WEIGHT_SKILL_MATCH}·S_skill + {settings.WEIGHT_PREFERENCE}·S_pref) / (sum of weights used)`

A component that cannot be computed (for example, a job that lists no skills) is left out and the remaining weights are
re-normalised. The weights are illustrative defaults, not learned from data. **The score ranks relevance; it is not the
probability of being shortlisted or hired.**""")

    if profile is None:
        empty_state("Enter your profile to see recommendations", "Choose a few skills, then press “Get recommendations”.")
        return
    if st.session_state.profile_is_demo:
        st.info("Showing results for the demo profile. Edit the form above and press “Get recommendations” to use your own.")
    recommender = state.get_recommender()
    try:
        recs = recommender.recommend(profile, top_n=st.session_state.get("rec_topn", 10),
                                     hide_ineligible=st.session_state.get("rec_hide", True))
    except ValueError as exc:
        st.error(str(exc))
        return
    st.session_state.pop("score_cache", None)  # refresh scores used by other pages
    if not recs:
        empty_state("No recommendations", "Every job needs more experience than your profile — untick “Hide jobs…” to see them.")
        return
    st.markdown(f"**Top {len(recs)} matches** from {len(jobs)} jobs · profile skills: " + chips(profile.skills, limit=15),
                unsafe_allow_html=True)
    by_id = jobs.set_index("job_id")
    tracked = state.get_store().tracked_ids()
    for rank, rec in enumerate(recs, start=1):
        job = by_id.loc[rec.job_id].to_dict() | {"job_id": rec.job_id}
        _recommendation_card(rank, rec, job, rec.job_id in tracked)
    table = pd.DataFrame([{"rank": i, "title": by_id.loc[r.job_id, "title"], "company": by_id.loc[r.job_id, "company"],
                           "score": r.score, "cosine": r.text_similarity, "text_relative": r.text_relative,
                           "skill_score": r.skill_score,
                           "preference_score": r.preference_score, "eligibility": r.eligibility,
                           "matched_skills": ", ".join(r.matched_skills), "missing_skills": ", ".join(r.missing_skills)}
                          for i, r in enumerate(recs, start=1)])
    st.download_button("Download these recommendations (CSV)", table.to_csv(index=False).encode(), "recommendations.csv",
                       "text/csv", icon=":material/download:")
