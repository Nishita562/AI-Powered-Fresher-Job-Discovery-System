import pytest

from src.extractors import (build_job_record, categorize_job, detect_employment_type, detect_work_mode,
                            extract_deadline, extract_eligibility, extract_salary, is_fresher_friendly, parse_experience)
from src.keywords import has_fresher_signal, has_senior_signal


@pytest.mark.parametrize("text, expected", [
    ("Experience: 0-2 years in Python", (0.0, 2.0)),
    ("We need 1 to 3 yrs of experience", (1.0, 3.0)),
    ("3+ years experience with SQL", (3.0, None)),
    ("Minimum 5 years of relevant experience", (5.0, None)),
    ("at least 2 years experience", (2.0, None)),
    ("4 years of professional experience", (4.0, None)),
    ("Freshers are welcome to apply", (0.0, 1.0)),
    ("No prior experience required", (0.0, 1.0)),
])
def test_parse_experience(text, expected):
    lo, hi, matched = parse_experience(text)
    assert (lo, hi) == expected
    assert matched


def test_parse_experience_ignores_degree_duration_and_missing():
    assert parse_experience("A 4-year B.Tech degree in CSE")[:2] == (None, None)
    assert parse_experience("Great culture and snacks") == (None, None, "")
    assert parse_experience("") == (None, None, "")


def test_parse_experience_field_mode():
    # A dedicated badge such as "0-1 years" has no word "experience" next to it.
    assert parse_experience("0-1 years")[:2] == (None, None)
    assert parse_experience("0-1 years", require_context=False)[:2] == (0.0, 1.0)


@pytest.mark.parametrize("text, expected", [
    ("CTC: 4-6 LPA for freshers", "4-6 LPA"),
    ("Stipend: ₹25,000 per month", "₹25,000 per month"),
    ("Salary: ₹4,50,000 per annum", "₹4,50,000 per annum"),
    ("Package of 7 LPA", "7 LPA"),
])
def test_extract_salary(text, expected):
    assert extract_salary(text) == expected


def test_extract_salary_never_invents():
    assert extract_salary("Competitive salary and benefits") == ""
    assert extract_salary("Join a team of 25 engineers in 3 cities") == ""


@pytest.mark.parametrize("text, expected", [
    ("Apply by 30 November 2026.", "2026-11-30"),
    ("Last date to apply: 15/12/2026", "2026-12-15"),
    ("Application deadline - 2026-11-05", "2026-11-05"),
    ("Applications close on December 1, 2026", "2026-12-01"),
])
def test_extract_deadline(text, expected):
    assert extract_deadline(text) == expected


def test_extract_deadline_requires_keyword_and_valid_date():
    assert extract_deadline("Posted on 12 October 2026") == ""
    assert extract_deadline("Apply by 31/02/2026") == ""  # invalid date is not guessed


def test_employment_type_priority():
    assert detect_employment_type("Software Engineer Intern", hint="Full Time Employee") == "Internship"
    assert detect_employment_type("Graduate Engineer Trainee") == "Graduate Trainee"
    assert detect_employment_type("Data Analyst", hint="Contract") == "Contract"
    assert detect_employment_type("Data Analyst", "Permanent full-time role") == "Full-time"
    assert detect_employment_type("Data Analyst") == "Not specified"


def test_work_mode():
    assert detect_work_mode("Remote (India)") == "Remote"
    assert detect_work_mode("Hybrid — Pune") == "Hybrid"
    assert detect_work_mode("Pune", "Work mode: on-site, five days a week") == "On-site"
    assert detect_work_mode("Pune", "You will work with remote teams") == "Unknown"


def test_eligibility_sentence():
    text = "You will build APIs. Eligibility: B.Tech/B.E. in CSE (2026 batch). We offer snacks."
    assert "B.Tech" in extract_eligibility(text)
    assert extract_eligibility("No education details here at all.") == ""


def test_keyword_word_boundaries_fix_legacy_bugs():
    # The Node.js prototype used substring matching, so these were false positives.
    assert not has_fresher_signal("Internal tools for international clients")
    assert not has_senior_signal("Shows leadership qualities")
    assert has_fresher_signal("Summer Intern 2026")
    assert has_senior_signal("Team Lead – Payments")


def test_is_fresher_friendly_rules():
    assert not is_fresher_friendly("Senior Software Engineer", "Freshers welcome", None)
    assert is_fresher_friendly("Associate Product Manager – Fresher", "", 0)
    assert not is_fresher_friendly("Data Analyst", "", 3.0)
    assert is_fresher_friendly("Data Analyst", "", 1.0)
    assert is_fresher_friendly("Business Analyst", "", None, "Internship")
    assert not is_fresher_friendly("Business Analyst", "Great team", None)


def test_categorize_job():
    assert categorize_job("Machine Learning Engineer Intern") == "Data Science & AI"
    assert categorize_job("QA Engineer – Fresher") == "QA & Testing"
    assert categorize_job("Junior Data Analyst") == "Data Analytics & BI"
    assert categorize_job("Gardener") == "Other"


def test_build_job_record_handles_missing_fields_gracefully():
    assert build_job_record({"title": "", "company": "X"}, source="t", source_type="t", data_mode="live") is None
    rec = build_job_record({"title": "Data Analyst – Acme", "company": "Acme"}, source="t", source_type="generic",
                           data_mode="live")
    assert rec.title == "Data Analyst"          # trailing company name removed
    assert rec.salary == "" and rec.deadline == "" and rec.apply_url == ""
    assert rec.employment_type == "Not specified"
    assert rec.min_experience_years is None


def test_shared_page_url_uses_composite_id():
    common = {"company": "Acme", "apply_url": "file:///tmp/careers.html", "url_is_shared": True}
    a = build_job_record({"title": "QA Trainee", **common}, source="t", source_type="generic", data_mode="demo_fixture")
    b = build_job_record({"title": "Cloud Support Associate", **common}, source="t", source_type="generic", data_mode="demo_fixture")
    assert a.job_id != b.job_id
