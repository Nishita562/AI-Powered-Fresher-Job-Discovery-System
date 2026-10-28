import pytest

from src.models import JobRecord
from tests.conftest import make_job


def test_upsert_counts_new_and_updates(store):
    a, b = make_job("A"), make_job("B")
    assert store.upsert_jobs([a, b]) == (2, 2)
    a.description = "updated description"
    assert store.upsert_jobs([a]) == (1, 0)
    df = store.load_jobs()
    assert len(df) == 2
    assert df.set_index("job_id").loc[a.job_id, "description"] == "updated description"


def test_discovered_at_is_preserved_on_update(store):
    rec = make_job("A", discovered_at="2026-10-01T00:00:00+00:00")
    store.upsert_jobs([rec])
    rec.discovered_at = "2026-10-24T00:00:00+00:00"
    store.upsert_jobs([rec])
    assert store.load_jobs().iloc[0]["discovered_at"].startswith("2026-10-01")


def test_skills_round_trip_and_mode_filter(store):
    rec = make_job("ML Intern", description="python and pandas")
    live = JobRecord.from_dict({**make_job("Live job").to_dict(), "data_mode": "live"})
    store.upsert_jobs([rec, live])
    df = store.load_jobs("sample")
    assert len(df) == 1 and isinstance(df.iloc[0]["skills"], list) and "python" in df.iloc[0]["skills"]
    assert store.count_jobs() == {"sample": 1, "live": 1}
    assert store.delete_jobs("live") == 1


def test_application_tracker_lifecycle(store):
    job = make_job("Data Analyst").to_dict()
    store.save_application(job)
    assert store.tracked_ids() == {job["job_id"]}
    store.update_application(job["job_id"], status="Applied", notes="Applied via portal")
    apps = store.load_applications()
    assert apps.iloc[0]["status"] == "Applied" and apps.iloc[0]["notes"] == "Applied via portal"
    store.save_application(job, "Interview")  # re-saving keeps notes
    assert store.load_applications().iloc[0]["notes"] == "Applied via portal"
    store.remove_application(job["job_id"])
    assert store.load_applications().empty


def test_invalid_status_rejected(store):
    with pytest.raises(ValueError):
        store.save_application(make_job("X").to_dict(), "Hired!!")


def test_crawl_run_history(store):
    run_id = store.start_run("fixtures")
    store.finish_run(run_id, companies_attempted=2, jobs_saved=5, status="completed", errors=[{"company": "x", "error": "403"}])
    runs = store.load_runs()
    assert runs.iloc[0]["status"] == "completed" and runs.iloc[0]["jobs_saved"] == 5
