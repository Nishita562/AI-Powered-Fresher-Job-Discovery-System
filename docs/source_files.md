# Important source files explained

| File | What it does | Look here when… |
|---|---|---|
| `app.py` | Streamlit entry point. It sets up the theme, session state, the 8-page navigation and the sidebar dataset selector. | the app does not start, or you want to add a page |
| `config/settings.py` | Every tunable value: timeouts, delays, batch size, score weights, eligibility factors and paths. Values can be overridden with `.env`. | you want to change crawler politeness or score weights |
| `config/sources.json` | CSS selectors for the Greenhouse, Lever and generic adapters, and the list of verified public boards. | a job site changed its layout |
| `config/skills.json` | Skill dictionary: canonical skill name → aliases (123 skills). | a skill is not detected |
| `src/browser_manager.py` | Playwright lifecycle; `goto()` with the robots.txt check, polite delay, retries, 403/429 handling and CAPTCHA detection. | pages fail to load, or you are asked about ethics |
| `src/adapters/base.py` | Shared adapter helpers, detail-page prioritisation (`detail_priority`) and detail-page reading. | you are explaining how detail pages are chosen |
| `src/adapters/greenhouse.py`, `lever.py`, `generic.py` | One adapter per website family. `generic.py` is the Python port of the original Node.js scraper. | you are adding a new website type |
| `src/job_scraper.py` | `run_crawl()`: builds targets, runs batches, extracts, de-duplicates, saves to SQLite and reports progress. | you are explaining the crawl workflow |
| `src/crawl_runner.py` | Starts and stops the crawl in a background process and reads and writes the status file. | the UI shows a stale crawl status |
| `src/cli.py` | Command line: `crawl`, `verify-catalogue`, `export`, `stats`. | you want to work without the UI |
| `src/extractors.py` | Regex rules for experience, salary, deadline, employment type, work mode, eligibility and category; the fresher rules; `build_job_record()`. | a field is extracted wrongly |
| `src/keywords.py` | Fresher, senior and role keyword lists with word-boundary matching (fixes the prototype's substring bug). | “intern” or “senior” detection looks wrong |
| `src/skills.py` | Dictionary-based skill extraction with custom boundaries. | skills are missed or wrongly found |
| `src/deduplication.py` | URL normalisation, `make_job_id()`, `deduplicate()`. | duplicates appear or distinct jobs merge |
| `src/recommendation.py` | **The AI/ML core**: TF-IDF, cosine similarity, the explainable score, similar jobs and keywords. | you are explaining or changing the recommender |
| `src/clustering.py` | K-Means clustering of jobs, with k chosen by silhouette. | you are explaining the Analytics clusters |
| `src/resume_parser.py` | In-memory PDF/DOCX text extraction with friendly errors. | a resume upload fails |
| `src/storage.py` | SQLite schema and all SQL (`jobs`, `applications`, `crawl_runs`). | you are working on persistence or the tracker |
| `src/company_catalog.py` | Loads, validates, de-duplicates, searches, paginates and batches the catalogue. | you are editing `data/companies.csv` |
| `src/catalogue_verifier.py` | Checks catalogue URLs (HTTP, then optionally a browser) and writes the status back. | you are re-verifying the catalogue |
| `src/job_filter.py` | `JobFilters`, `apply_filters()`, `sort_jobs()`. | a filter behaves unexpectedly |
| `src/data_loader.py`, `export.py`, `models.py` | Merge sample and stored data; CSV/JSON export; the `JobRecord` schema. | you are changing the record fields |
| `ui/state.py` | Session state and cached loading of data and the fitted model, so filters never re-crawl or re-fit. | the UI feels slow or shows old data |
| `ui/components.py` | Job cards, the details dialog, badges, score bars, safe links and pagination (all scraped text is HTML-escaped). | you are changing the look of a card |
| `ui/views/*.py` | One file per page. | you are changing a page |
| `scripts/generate_sample_data.py` | Rebuilds the 133-job fictional sample dataset (seed 42). | you are changing the sample data |
| `tests/` | 100 pytest tests, including a real Chromium crawl of the fixtures and AppTest UI tests. | something breaks; run `python -m pytest` |
| `data/fixtures/career_pages/` | Five fictional demo career pages used for the offline crawl and the tests. | you are preparing the demo |
| `legacy/nodejs_prototype/` | The original uploaded Node.js project, unchanged, for reference. | you are asked what you started from |
