# AI-Powered Fresher Job Discovery System Using Playwright

A B.Tech AIML minor project (AIML-451). The system collects fresher and entry-level job listings with **Playwright** browser automation, extracts structured fields, removes duplicates, stores them in **SQLite**, and ranks them for a candidate with an explainable **TF-IDF + cosine-similarity** recommender. A **Streamlit** dashboard ties everything together.

> **Data honesty.** Every job carries a data mode shown as a badge:
> **SAMPLE** = fictional offline demo records (`data/sample_jobs.json`, links on example.com) ·
> **DEMO CRAWL** = collected by Playwright from local fictional demo pages ·
> **LIVE** = collected from real public job boards at the time shown on the card.
> The company catalogue is a directory of employers. It does not mean a company has a vacancy.

---

## 1. Quick start on a Mac (Apple Silicon or Intel)

You need **Python 3.12 or 3.13**. Miniconda is recommended; your existing Conda environments are not touched.

```bash
cd ~/Downloads/ai-powered-fresher-job-discovery-system
chmod +x setup.sh run.sh
./setup.sh
```

`setup.sh` creates a dedicated environment named **`fresherjobs`**. It uses Conda with Python 3.12 if Conda is installed, and otherwise a local `.venv`. It then installs the pinned packages, downloads Playwright's Chromium (about 150 MB, one time), and runs the tests.

To start the app:

```bash
./run.sh
```

Then open **http://localhost:8501** in Safari or Chrome. To stop the app, press **Ctrl + C** in the Terminal window. Any running crawl is a separate process; use **Stop crawl** on the *Collect Jobs* page first, and it will close its browser by itself.

### Manual setup (if you prefer to type each step)

```bash
conda env create -f environment.yml         # creates the "fresherjobs" environment (Python 3.12)
conda activate fresherjobs
python -m playwright install chromium       # browser used by Playwright
python -m pytest                            # run the tests
streamlit run app.py                        # start the dashboard
```

Without Conda, the steps are:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python -m pytest
streamlit run app.py
```

Which Python? `numpy 2.5` and `scipy 1.18` need Python ≥ 3.12, so use **3.12** (the default in `environment.yml`) or 3.13. Python 3.11 and older will not install these pinned versions.

---

## 2. What the system does

| Part | What it really does | Technique (honest label) |
|---|---|---|
| Browser automation | Opens public job boards / career pages, waits for JavaScript, reads listings and detail pages | Playwright (Chromium), configurable adapters |
| Website adapters | Greenhouse boards, Lever boards, generic career pages (ported from the original Node.js prototype) | CSS selectors in `config/sources.json` |
| Ethics controls | robots.txt check, 1.5 s per-host delay, one page at a time, 403/429/CAPTCHA pages skipped | `src/browser_manager.py` |
| Information extraction | Experience range, salary/stipend, deadline, employment type, eligibility, work mode, category | Regular-expression rules |
| Skill extraction | Skills in job text and resumes | Transparent dictionary of 123 skills with aliases |
| Deduplication | Same job on different URLs or pages | SHA-1 of normalised URL + company/title/location key |
| Recommendation | Ranks jobs for a profile and explains why | TF-IDF vectors, cosine similarity, weighted rules |
| Job clustering | Groups similar descriptions | K-Means (unsupervised) with the silhouette score |
| Resume parsing | Reads PDF/DOCX in memory and suggests skills | pypdf, python-docx |
| Storage & export | Jobs, application tracker, crawl history; CSV/JSON downloads | SQLite, pandas |

The recommender is **not** trained on hiring outcomes, so no accuracy figure is claimed. The score ranks relevance. **It is not the probability of being hired.**

### Dashboard pages
Dashboard · Job Search · AI Recommendations · Company Explorer · Application Tracker · Analytics · Collect Jobs (Playwright) · Settings & About.

---

## 3. The relevance score

```
score = 100 × F_elig × (0.50·S_text + 0.30·S_skill + 0.20·S_pref) / (sum of weights used)
```

* **S_text**: cosine similarity between the profile's TF-IDF vector and the job's TF-IDF vector, divided by the best cosine in the current dataset (best match = 1.0). A short profile compared with long descriptions gives small raw cosines (typically 0–0.3), so the raw value is always shown too.
* **S_skill**: matched skills ÷ skills listed by the job.
* **S_pref**: mean of *role match* (the share of preferred-role words found in the title) and *location match* (1 if the location or remote preference fits).
* **F_elig**: 1.0 when the job's minimum experience fits, 0.9 when it is not stated, 0.5 when the job needs more experience.
* A component that cannot be computed (for example, a job with no recognisable skills) is left out, and the remaining weights are re-normalised.
* The weights are illustrative defaults set in `config/settings.py`. They are not learned from data.

### Worked example (computed by the real code; also shown under *Settings & About*)

Profile: skills *python, machine learning, pandas, sql*; preferred role *Machine Learning Engineer*; location *Bengaluru*; 0 years of experience. The model is fitted on three sample jobs (a 404-term vocabulary).

| Sample job | cosine | S_text | S_skill | S_pref | F_elig | Score |
|---|---|---|---|---|---|---|
| Machine Learning Engineer Intern (Mumbai) | 0.323 | 1.000 | 4/8 = 0.500 | (1 + 0)/2 = 0.5 | 1.0 | 0.5·1 + 0.3·0.5 + 0.2·0.5 = 0.75 → **75.0** |
| Senior Data Scientist (5+ yrs, Ahmedabad) | 0.181 | 0.559 | 2/7 = 0.286 | 0 | 0.5 | (0.279 + 0.086)·0.5 → **18.3** |
| Junior Data Analyst (Kochi) | 0.034 | 0.104 | 2/7 = 0.286 | 0 | 1.0 | 0.052 + 0.086 → **13.8** |

The senior role still outranks the analyst role, because its wording is closer to the ML profile. The eligibility factor halves its score, and the *Hide jobs that need more experience* option removes it entirely.

---

## 4. Collecting jobs

From the UI: open **Collect Jobs (Playwright)**.

* **Offline demo crawl**: five local fictional career pages: a card layout, an HTML table, a JavaScript-rendered list, a Greenhouse-style board and a Lever-style board. It needs no internet and takes about 20 seconds. Expected result: 14 jobs saved and 1 duplicate removed.
* **Live crawl**: up to 5 companies per run. Companies with verified public Greenhouse/Lever boards are listed first. Results depend on the websites at that moment.

From the command line:

```bash
python -m src.cli crawl --mode fixtures
python -m src.cli crawl --mode live --companies "Groww,Paytm" --max-details 5
python -m src.cli verify-catalogue            # re-check catalogue URLs (HTTP)
python -m src.cli verify-catalogue --engine playwright --only-unverified
python -m src.cli export --dataset all        # CSV + JSON into exports/
python -m src.cli stats
```

Crawls from the UI run in a **background process** (`src/crawl_runner.py`), so the dashboard never freezes. Progress refreshes every 2 seconds. Results are saved after every batch of 5 companies, so stopping a crawl keeps the work already done.

### Data included in this ZIP

`database/jobs.db` already contains 14 **DEMO CRAWL** jobs (from the local fixture pages) and 8 **LIVE** jobs collected from the public boards of Groww and Paytm on 25 October 2026. Together with the 133 sample jobs, this is the 155-job dataset used in the report and screenshots. The live records are labelled with their collection time and may no longer be open. To start with an empty database, delete `database/jobs.db`; it is recreated automatically.

---

## 5. Project structure

```
app.py                     Streamlit entry point and navigation
config/settings.py         All tunable values (timeouts, delays, weights, paths); .env overrides
config/sources.json        Website adapter selectors + verified public job boards
config/skills.json         Skill dictionary (123 skills, aliases)
src/browser_manager.py     Playwright lifecycle, robots.txt, polite delay, retries, block detection
src/adapters/              greenhouse.py, lever.py, generic.py (+ base.py)
src/job_scraper.py         Batch crawl orchestration -> extraction -> dedup -> SQLite
src/crawl_runner.py        Background crawl process + JSON status file for the UI
src/extractors.py          Rule-based field extraction and fresher classification
src/keywords.py            Fresher / senior / role keyword rules (word-boundary regex)
src/skills.py              Dictionary-based skill extraction
src/deduplication.py       URL normalisation, job IDs, duplicate merging
src/recommendation.py      TF-IDF + cosine recommender, explainable score, similar jobs
src/clustering.py          K-Means job clusters + silhouette
src/resume_parser.py       PDF/DOCX text extraction in memory
src/company_catalog.py     Catalogue loading, search, pagination, batching
src/catalogue_verifier.py  URL reachability check for companies.csv
src/job_filter.py          Filters and sorting
src/storage.py             SQLite: jobs, applications, crawl_runs
src/export.py, data_loader.py, models.py, text_utils.py, logger.py, cli.py
ui/                        theme.py, components.py, state.py, nav.py, views/ (8 pages)
data/companies.csv         518-company catalogue
data/sample_jobs.json/.csv 133 fictional sample jobs
data/fixtures/             Demo career pages and a fictional sample resume
scripts/generate_sample_data.py
tests/                     100 pytest tests (unit, Playwright integration, Streamlit AppTest)
legacy/nodejs_prototype/   The original Node.js scraper this project grew from
docs/                      Report, viva questions, presentation outline, guides
screenshots/               Real screenshots of the running app
```

---

## 6. Testing

```bash
python -m pytest              # all tests
python -m pytest -m "not integration"   # skip the tests that launch Chromium
```

Result on the development Mac (Apple Silicon, macOS, Python 3.13): **100 passed**. The tests cover extraction rules, skills, filters, deduplication, SQLite storage, the recommender (formula consistency, empty profiles, missing skills, duplicates, eligibility), resume parsing, the catalogue, exports, a real Playwright crawl of the demo pages, and every Streamlit page.

---

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `zsh: permission denied: ./setup.sh` | `chmod +x setup.sh run.sh` |
| `conda: command not found` | Open a new Terminal after installing Miniconda, or run `USE_VENV=1 ./setup.sh` |
| `Executable doesn't exist … chromium` | `python -m playwright install chromium` (environment activated) |
| `ModuleNotFoundError: streamlit` | Activate the environment: `conda activate fresherjobs` or `source .venv/bin/activate` |
| `Port 8501 is already in use` | `./run.sh` picks the next free port automatically, or run `streamlit run app.py --server.port 8502` |
| Pip tries to build numpy/scipy from source | Your Python is too old; use Python 3.12 (`conda env create -f environment.yml`) |
| SSL certificate errors in `verify-catalogue` | Run `pip install --upgrade certifi` inside the environment |
| Live crawl finds 0 jobs or shows HTTP 403 | The site blocked automation or changed its layout. That is expected: use the demo crawl, or update selectors in `config/sources.json` |
| macOS asks to allow incoming connections for Python | Click *Allow* (Streamlit listens on localhost only) |
| The app shows old data | *Settings & About → Refresh data from disk* |
| A crawl seems stuck | *Collect Jobs → Stop crawl*, and check `logs/crawl_subprocess.log` |

---

## 8. Limitations

* Website layouts change. Adapters may need selector updates, which are made in configuration and not in code.
* Many company websites block automated browsers. Those pages are skipped, never bypassed.
* Regex and dictionary extraction can miss unusual wording. Unknown values stay empty and are never guessed.
* TF-IDF matches words, not meaning. Synonyms the dictionary does not know will not match.
* Company "About us" text inside job descriptions can add skills that are not real requirements.
* The catalogue's homepage URLs (423 of 518) are official domains, not exact careers paths.
* There is no authentication. The app is meant to run locally for one user.

## 9. Ethics and privacy

Only public pages that robots.txt allows are visited, one at a time, with a polite delay and a descriptive User-Agent. Logins, CAPTCHAs, paywalls and bot protection are never bypassed. Resumes are processed in memory and never stored. Tracker data stays in `database/jobs.db` on your computer. Streamlit usage statistics are disabled.
