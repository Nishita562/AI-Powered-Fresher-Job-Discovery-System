from src.deduplication import composite_key, deduplicate, make_job_id, normalize_url
from tests.conftest import make_job


def test_normalize_url_removes_tracking_and_trailing_slash():
    a = normalize_url("https://Jobs.Example.com/role/123/?utm_source=linkedin&gh_src=abc&id=7#apply")
    assert a == "https://jobs.example.com/role/123?id=7"
    assert normalize_url("") == ""


def test_job_id_is_stable_and_url_based():
    assert make_job_id("https://x.com/j/1?utm_medium=x", "A", "B", "C") == make_job_id("https://x.com/j/1/", "Other", "Title", "")
    assert make_job_id("", "Acme", "Data Analyst", "Pune") == make_job_id("", " acme ", "data analyst", "PUNE")


def test_same_url_is_duplicate():
    a = make_job("Data Analyst", url="https://example.com/j/1?utm_source=x")
    b = make_job("Data Analyst (Fresher)", url="https://example.com/j/1")
    unique, removed = deduplicate([a, b])
    assert len(unique) == 1 and removed == 1


def test_cross_posted_job_with_different_urls_is_duplicate():
    a = make_job("QA Engineer", company="Acme", location="Pune", url="https://boards.example.com/acme/1")
    b = make_job("QA Engineer", company="ACME", location="pune", url="https://acme.example.com/careers/qa")
    unique, removed = deduplicate([a, b])
    assert removed == 1 and len(unique) == 1


def test_richer_record_kept_and_first_seen_preserved():
    poor = make_job("ML Intern", url="https://example.com/1", discovered_at="2026-10-01T00:00:00+00:00")
    rich = make_job("ML Intern", url="https://example.com/1", discovered_at="2026-10-20T00:00:00+00:00",
                    description="Python, pandas, scikit-learn, machine learning. Stipend: ₹20,000 per month.")
    unique, _ = deduplicate([poor, rich])
    assert unique[0].description.startswith("Python")
    assert unique[0].discovered_at.startswith("2026-10-01")


def test_distinct_jobs_are_kept():
    unique, removed = deduplicate([make_job("A"), make_job("B"), make_job("C")])
    assert removed == 0 and len(unique) == 3
    assert composite_key("Acme", "Data Analyst", "Pune") == "acme|data analyst|pune"
