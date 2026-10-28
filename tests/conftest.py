"""Shared pytest fixtures. A temporary database is configured *before* the
application modules are imported, so tests never touch database/jobs.db."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_TMP = tempfile.mkdtemp(prefix="jobdiscovery_tests_")
os.environ["JOBS_DB_PATH"] = str(Path(_TMP) / "test_jobs.db")

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.extractors import build_job_record  # noqa: E402
from src.storage import JobStore  # noqa: E402


def make_job(title, company="Acme Test Co", description="", location="Bengaluru, India", url=None, **kw):
    raw = {"title": title, "company": company, "description": description, "location": location,
           "apply_url": url if url is not None else f"https://example.com/jobs/{abs(hash((title, company, location)))}", **kw}
    return build_job_record(raw, source="unit test", source_type="sample", data_mode="sample")


@pytest.fixture
def jobs_df() -> pd.DataFrame:
    """Small, hand-written job set covering ML, data, web, HR and a senior role."""
    recs = [
        make_job("Machine Learning Intern", description="Build models with Python, scikit-learn, pandas and NumPy. "
                 "Machine learning on tabular data. No prior experience required. Stipend: ₹20,000 per month."),
        make_job("Junior Data Analyst", description="SQL, Excel and Power BI dashboards. Data analysis for sales teams. "
                 "Experience: 0-1 years.", location="Pune, India"),
        make_job("Frontend Developer Intern", description="React, JavaScript, HTML and CSS. Freshers welcome.",
                 location="Remote (India)"),
        make_job("HR Intern", description="Support recruitment drives and onboarding. Good communication skills.",
                 location="Noida, India"),
        make_job("Senior Data Scientist", description="Lead machine learning projects in Python. Minimum 5 years of experience.",
                 location="Bengaluru, India"),
    ]
    return pd.DataFrame([r.to_dict() for r in recs])


@pytest.fixture
def store(tmp_path) -> JobStore:
    return JobStore(tmp_path / "store.db")


def minimal_pdf(lines: list[str]) -> bytes:
    """Build a tiny valid one-page PDF containing ``lines`` of text (no extra dependency needed)."""
    content = "BT /F1 12 Tf 72 740 Td 14 TL " + " ".join(f"({l}) Tj T*" for l in lines) + " ET"
    stream = content.encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return out
