# Implemented features, verification status and known gaps

Status as of 25 October 2026. Each row says **how** the item was verified on the development Mac (Apple M1, macOS 27.0, Python 3.13.7).

## 1. Acceptance checklist (from the project brief)

| Item | Status | How it was verified |
|---|---|---|
| Launches with the documented Mac setup | ✅ app launched, ⚠️ the `setup.sh` Conda path was not run here | `streamlit run app.py` was run many times, and the venv path of the setup was used. This Mac has no Conda installed, so `./setup.sh` with Conda must be tried on your Mac |
| Dashboard loads without errors | ✅ | Streamlit AppTest plus the real app in Chromium |
| Search works on the sample dataset | ✅ | AppTest (`test_job_search_keyword_filters_results`) and the browser script |
| Filters and sorting work | ✅ | 8 unit tests plus the browser script (filters expanded, keyword search) |
| Company catalogue can be searched and browsed | ✅ | Unit tests plus the browser script (search “fintech”) |
| Recommendation engine produces ranked results | ✅ | 16 unit tests plus the browser script |
| Score and explanation match the formula | ✅ | `test_score_matches_documented_formula`, and the worked example recomputed by hand |
| Resume parsing works (or a manual fallback exists) | ✅ | PDF and DOCX unit tests; sample resume uploaded in the browser (11 skills) |
| CSV and JSON export work | ✅ functions, ⚠️ buttons | Export functions are unit-tested and the CLI export was run. Download buttons were rendered but not clicked by the script |
| Saved jobs and tracker statuses persist | ✅ storage, ⚠️ UI edit | Save buttons were clicked in the browser and the jobs appeared in the tracker. Editing a status and pressing *Save changes* in the UI was not automated; the storage functions are unit-tested |
| UI distinguishes demo data from live results | ✅ | SAMPLE / DEMO CRAWL / LIVE badges on every card, and data-mode counts in the sidebar |
| Interface does not freeze while waiting for a website | ✅ | Crawls run in a subprocess; the demo crawl was started from the UI and progress updated while the page stayed usable |
| Tests cover the key recommendation and filtering functions | ✅ | **100 tests, all passed** |
| Report diagrams, screenshots and text match the application | ✅ | Diagrams were drawn from the code structure; screenshots were captured from the running app; numbers were computed by the code at build time |
| ZIP contains source, datasets, manifest and instructions | ✅ | The ZIP was extracted into a fresh folder and its tests were re-run (see the final notes) |

## 2. Implemented features

**Collection (Playwright)**
- Greenhouse, Lever and generic career-page adapters. Their selectors are in `config/sources.json`.
- robots.txt checks, a 1.5 s per-host delay (or the site's Crawl-delay if longer), retries only for timeouts and 5xx errors, and skipping of 401/403/429 responses and CAPTCHA pages.
- One Chromium page at a time. Companies are processed in batches of 5, and each batch is saved as it finishes.
- A background crawl process with live progress, a Stop button and run history.
- An offline demo crawl of 5 fictional pages: cards, a table, a JavaScript-rendered list, a Greenhouse-style board and a Lever-style board.
- A real live crawl was done on 25 Oct 2026 (Groww and Paytm: 206 listings, 8 jobs saved).

**Processing**
- Extraction of experience range, salary or stipend, deadline, employment type, work mode, eligibility, category and the fresher flag. Unknown values are left empty.
- A skill dictionary of 123 skills with aliases and word-boundary matching.
- Deduplication by normalised URL and by a company|title|location key. The richer record and the first-seen date are kept.

**Data**
- A 518-company catalogue: 474 URLs verified reachable, 44 unverified, 0 missing, and 20 verified public boards.
- 133 fictional sample jobs on example.com, a fictional sample resume in PDF and DOCX, and 5 fixture career pages.
- SQLite tables `jobs`, `applications` and `crawl_runs`, plus CSV/JSON export from the UI and the CLI.

**AI / ML**
- TF-IDF (1–2-grams, sublinear TF) with cosine similarity, relative text similarity and an explainable score: 0.5 text + 0.3 skills + 0.2 preference, multiplied by an eligibility factor.
- Matched and missing skills, a written explanation, similar jobs and the top TF-IDF keywords for each job.
- Resume parsing in memory (PDF and DOCX), with a manual skills fallback.
- K-Means job clusters, with k chosen by the silhouette score over k = 3…10.

**Interface (Streamlit, 8 pages)**
- Dashboard, Job Search, AI Recommendations, Company Explorer, Application Tracker, Analytics (Plotly), Collect Jobs and Settings & About.
- A custom theme, cards, badges, empty states, validation messages, pagination, a job-details dialog and download buttons.

## 3. Not implemented / limitations (deliberately or for lack of time)

- **No supervised ML model.** There is no legitimate labelled job-to-outcome dataset, so no accuracy, precision or recall is claimed.
- **No embeddings (BERT / Sentence-BERT).** Matching is lexical; embeddings are listed as future work.
- **No login, authentication or multi-user hosting.** The app is a local, single-user tool.
- **No automatic detection of closed listings.** A job's last-seen time is recorded, but the system cannot confirm the job is still open.
- **Generic adapter on arbitrary company sites is best-effort.** Many such sites block automation; they are skipped and never bypassed.
- **Weights are illustrative.** The 0.5 / 0.3 / 0.2 weights were not tuned on data.
- **Not verified here:** the Conda path of `setup.sh` (this Mac has no Conda), running on an M4 MacBook Air specifically, and clicking the download buttons in the UI.
