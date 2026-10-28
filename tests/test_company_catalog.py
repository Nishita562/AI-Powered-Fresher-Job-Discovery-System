import pandas as pd

from src.company_catalog import (URL_TYPES, VERIFICATION_STATUSES, catalogue_stats, crawlable, iter_batches,
                                 load_catalogue, paginate, search_catalogue)


def test_real_catalogue_is_valid():
    df = load_catalogue()
    assert 480 <= len(df) <= 550
    assert df["company_name"].str.lower().is_unique
    assert df["company_id"].is_unique
    assert set(df["verification_status"]) <= VERIFICATION_STATUSES
    assert set(df["url_type"]) <= URL_TYPES
    assert (df["career_url"].eq("") | df["career_url"].str.startswith("https://")).all()


def test_dedup_missing_url_and_ids(tmp_path):
    p = tmp_path / "c.csv"
    pd.DataFrame({"company_name": ["Acme Pvt Ltd", "ACME", "Beta Corp"],
                  "career_url": ["https://acme.example.com", "https://dup.example.com", ""],
                  "industry": ["IT Services", "IT Services", "SaaS"]}).to_csv(p, index=False)
    df = load_catalogue(p)
    assert df["company_name"].tolist() == ["Acme Pvt Ltd", "Beta Corp"]
    assert df.set_index("company_name").loc["Beta Corp", "verification_status"] == "missing"
    assert df.set_index("company_name").loc["Acme Pvt Ltd", "verification_status"] == "unverified"
    assert df["company_id"].tolist() == ["C0001", "C0002"]


def test_search_paginate_and_batches():
    df = load_catalogue()
    fintech = search_catalogue(df, industries=["Fintech"])
    assert len(fintech) > 0 and set(fintech["industry"]) == {"Fintech"}
    assert len(search_catalogue(df, query="infosys")) >= 1
    page, pages = paginate(df, page=999, page_size=25)
    assert pages == -(-len(df) // 25) and len(page) <= 25  # page clamped to the last one
    sizes = [len(b) for b in iter_batches(df.head(12), 5)]
    assert sizes == [5, 5, 2]


def test_crawlable_and_stats():
    df = load_catalogue()
    boards = crawlable(df)
    assert (boards["ats_board_token"] != "").sum() >= 10
    stats = catalogue_stats(df)
    assert stats["total"] == len(df) and sum(stats["by_status"].values()) == len(df)
