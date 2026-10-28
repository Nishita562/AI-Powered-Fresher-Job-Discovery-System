"""Command-line interface.

Examples (run from the project folder with the environment activated)::

    python -m src.cli crawl --mode fixtures            # offline Playwright demo
    python -m src.cli crawl --mode live --companies "Groww,Meesho" --max-details 5
    python -m src.cli verify-catalogue --limit 50
    python -m src.cli export --dataset all
    python -m src.cli stats
"""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from config import settings


def _cmd_crawl(args: argparse.Namespace) -> int:
    from src.crawl_runner import STOP_FILE, write_status
    from src.job_scraper import fixture_targets, live_targets, run_crawl
    from src.models import utc_now_iso

    stop_requested = {"flag": False}

    def _on_term(signum, frame):  # graceful stop: finish current page, save, close browser
        stop_requested["flag"] = True

    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)

    companies = [c.strip() for c in args.companies.split(",")] if args.companies else None
    targets = fixture_targets() if args.mode == "fixtures" else live_targets(companies, args.limit)
    if args.mode == "fixtures" and companies:
        targets = [t for t in targets if t.company_name in companies]
    if not targets:
        print("No crawlable companies matched. Check names against data/companies.csv.")
        return 1
    status_path = Path(args.status_file) if args.status_file else None
    started = utc_now_iso()

    def progress(p: dict) -> None:
        line = f"[{p['done']}/{p['total']}] {p.get('current_company') or ''} — jobs saved: {p['jobs_saved']}"
        print(line, flush=True)
        if status_path:
            import os
            write_status({**p, "state": "running", "pid": os.getpid(), "started_at": started}, status_path)

    summary = run_crawl(
        targets, mode=args.mode, batch_size=args.batch_size,
        max_detail_pages=args.max_details, headless=not args.headed, progress=progress,
        should_stop=lambda: stop_requested["flag"] or STOP_FILE.exists(),
    )
    if status_path:
        write_status({**summary.__dict__, "state": summary.status, "total": len(targets),
                      "done": summary.companies_attempted, "started_at": started, "finished_at": utc_now_iso()},
                     status_path)
    print(f"\nCrawl {summary.status}: {summary.companies_succeeded}/{summary.companies_attempted} companies OK, "
          f"{summary.jobs_saved} jobs saved ({summary.new_jobs} new, {summary.duplicates_removed} duplicates removed) "
          f"in {summary.seconds}s")
    for err in summary.errors:
        print(f"  ! {err['company']}: {err['error']}")
    return 0 if summary.status in ("completed", "stopped") else 2


def _cmd_verify(args: argparse.Namespace) -> int:
    from src.catalogue_verifier import verify_catalogue

    stats = verify_catalogue(limit=args.limit, engine=args.engine, workers=args.workers,
                             only_unverified=args.only_unverified)
    print(stats)
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    from src.data_loader import load_jobs
    from src.export import export_to_files

    df = load_jobs(args.dataset)
    csv_path, json_path = export_to_files(df, stem=f"jobs_{args.dataset}")
    print(f"Exported {len(df)} jobs:\n  {csv_path}\n  {json_path}")
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    from src.company_catalog import catalogue_stats, load_catalogue
    from src.data_loader import load_jobs
    from src.storage import JobStore

    print("Catalogue:", catalogue_stats(load_catalogue()))
    print("Stored jobs by mode:", JobStore().count_jobs())
    print("Jobs available (all):", len(load_jobs("all")))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.cli", description="Fresher Job Discovery System CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("crawl", help="Collect jobs with Playwright")
    c.add_argument("--mode", choices=["fixtures", "live"], default="fixtures")
    c.add_argument("--companies", help="Comma-separated company names (default: all crawlable)")
    c.add_argument("--limit", type=int, help="Maximum number of companies (live mode)")
    c.add_argument("--batch-size", type=int, default=settings.BATCH_SIZE)
    c.add_argument("--max-details", type=int, default=settings.MAX_DETAIL_PAGES_PER_COMPANY)
    c.add_argument("--headed", action="store_true", help="Show the browser window")
    c.add_argument("--status-file", help=argparse.SUPPRESS)
    c.set_defaults(func=_cmd_crawl)

    v = sub.add_parser("verify-catalogue", help="Check that catalogue URLs respond")
    v.add_argument("--limit", type=int)
    v.add_argument("--engine", choices=["http", "playwright"], default="http")
    v.add_argument("--workers", type=int, default=12)
    v.add_argument("--only-unverified", action="store_true", help="Re-check only URLs not yet verified")
    v.set_defaults(func=_cmd_verify)

    e = sub.add_parser("export", help="Export jobs to CSV and JSON in exports/")
    e.add_argument("--dataset", choices=["all", "collected", "live", "sample"], default="all")
    e.set_defaults(func=_cmd_export)

    s = sub.add_parser("stats", help="Print catalogue and dataset statistics")
    s.set_defaults(func=_cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
