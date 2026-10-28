# Viva Questions and Answers

**Project:** AI-Powered Fresher Job Discovery System Using Playwright
**Course:** B.Tech AIML, 7th Semester Minor Project (GGSIPU, AIML-451)

Each answer is written to be spoken in about 30 to 60 seconds. File, class and function names refer to the project folder, so you can open the code if the panel asks you to show something. All numbers come from the measurements recorded on 25 October 2026.

## Key numbers to remember

| Item | Value |
|---|---|
| Company catalogue (`data/companies.csv`) | 518 companies, 22 industries |
| URL check on 25 Oct 2026 | 474 verified (URL responded), 44 unverified, 0 missing |
| URL types | 423 homepage URLs, 95 careers-page URLs |
| Public job boards | 20 (15 Greenhouse, 5 Lever) |
| Sample dataset (`data/sample_jobs.json`) | 133 fictional jobs, 22 fictional companies, seed 42 |
| Offline demo crawl | 5 fixture pages, 21 listings seen, 14 jobs saved, 1 duplicate removed, 5/5 OK, about 18 to 23 s |
| Live crawl, 25 Oct 2026 (Groww + Paytm, max 4 detail pages) | 206 listings (196 Paytm + 10 Groww), 8 entry-level jobs saved, 26 s |
| Tests | 100 pytest tests, all passed in about 30 s (macOS arm64, Python 3.13) |
| Skill dictionary (`config/skills.json`) | 123 canonical skills with aliases |
| Score weights | text 0.50, skill 0.30, preference 0.20 |
| Eligibility factors | 1.0 eligible, 0.9 unknown, 0.5 needs more experience |

---

## 1. Project objective and scope

### Q1. What is the objective of your project?
The objective is to help fresh graduates find entry-level openings (fresher roles, internships and graduate-trainee programmes) that are spread across many company career pages. The system uses Playwright browser automation to visit public career pages and job boards. It then extracts structured fields such as experience, salary, deadline and skills with rule-based extraction, removes duplicates and stores the records in SQLite. Finally, it ranks the jobs against a candidate's profile or resume using TF-IDF vectors and cosine similarity, combined with transparent skill, preference and eligibility rules. Everything is presented in an 8-page Streamlit web interface.

### Q2. What problem does it solve for a fresher?
A fresher normally checks dozens of career pages by hand, and many listings either ask for several years of experience or do not state the requirement at all. General job portals mix senior and junior roles, so the student spends a lot of time filtering out irrelevant results. Our system keeps only listings with fresher signals, such as the word-boundary keywords "intern", "graduate trainee" and "entry level" or a parsed experience requirement of at most one year, and it excludes titles containing senior words. Each recommendation comes with a plain-English explanation of why it matched. The student can also track their own application status locally.

### Q3. What is in scope and what is out of scope?
In scope:
- collecting public listings from public Greenhouse and Lever boards and from generic career pages
- an offline demo crawl of 5 local fixture pages
- a 518-company catalogue
- field extraction, deduplication and SQLite storage
- TF-IDF recommendation, K-Means clustering and resume skill extraction
- analytics and CSV/JSON export

Out of scope: logging in to any website, bypassing CAPTCHAs or bot protection, applying to jobs on the user's behalf, and predicting hiring outcomes. It is a single-user local application, not a hosted multi-user portal.

### Q4. How did the project evolve from the original prototype?
The first version was a Node.js and Playwright prototype made of 6 JavaScript files, now kept in `legacy/nodejs_prototype/`: scraper.js, keywords.js, loadCompanies.js, validateUrls.js, generateReport.js and logger.js. It scraped pages with generic CSS selectors, used a substring keyword filter, and read a 111-row companies.csv that contained duplicates. We ported it to Python and extended it with site-specific adapters, regex extraction, deduplication, SQLite, the recommender, clustering, resume parsing and the Streamlit UI. We also fixed a real bug. Substring matching made "intern" match "internal" and "international", and "lead" match "leadership". `src/keywords.py` now uses word-boundary regular expressions, and `test_keyword_word_boundaries_fix_legacy_bugs` in `tests/test_extractors.py` checks exactly these cases.

### Q5. What are the three data modes, and why are they shown everywhere?
Every job record has a `data_mode` field with one of three values:
- `sample`: the fictional offline dataset
- `demo_fixture`: collected by Playwright from local, fictional demo pages
- `live`: collected from real public job boards

The UI shows these as the badges SAMPLE, DEMO CRAWL and LIVE on every job card and in the sidebar. This prevents anyone from mistaking a fictional demonstration record for a real vacancy. The SQLite `jobs` table also has a CHECK constraint, so no other value can be stored.

---

## 2. Why Playwright / browser automation

### Q6. Why did you use Playwright instead of requests and BeautifulSoup?
Many modern career pages are built with JavaScript, so the job list is not in the raw HTML that `requests` downloads; the browser renders it later. Playwright drives a real Chromium browser, runs the JavaScript and lets us read the page after rendering. Our QuantaLeap AI fixture page shows this: its jobs are inserted by a script after 800 ms, and a plain HTTP client would never see them. Playwright also has built-in waiting (`wait_until="domcontentloaded"`, `wait_for_load_state("networkidle")`), timeouts and HTTP status codes. The trade-off is that it is heavier and slower than plain HTTP. That is acceptable here because we crawl slowly on purpose to stay polite.

### Q7. Why Playwright and not Selenium?
Playwright installs matching browser binaries itself (`python -m playwright install chromium`), so there is no separate WebDriver to manage. It waits automatically for pages and network activity, which avoids fragile fixed sleeps. Its Python API supports browser contexts with a custom user agent and viewport, which we set in `BrowserManager.__enter__`. Selenium would also work, but Playwright is quicker to set up and more reliable on JavaScript-heavy pages. The original prototype already used Playwright, so keeping it also preserved the logic that already worked.

### Q8. What is the difference between headless and headed mode?
Headless mode runs Chromium without a visible window. It is the default (`HEADLESS = True` in `config/settings.py`) because it is faster and uses fewer resources. Headed mode opens a visible browser window so a person can watch the automation, which helps with debugging and demonstrations. In the UI this is the checkbox "Show the browser window while crawling (headed mode)", and on the command line it is the `--headed` flag. Both modes run exactly the same code.

### Q9. Walk us through what happens when the crawler opens one page.
1. `BrowserManager.goto(url)` in `src/browser_manager.py` checks robots.txt through `RobotsCache.allowed()`. If the page is disallowed, it is skipped.
2. `_wait_politely()` waits so the same host is never hit more often than every 1.5 seconds, or its robots.txt `Crawl-delay` if that is larger.
3. It calls `page.goto()` with `wait_until="domcontentloaded"` and a 25-second timeout, then checks the HTTP status.
4. It waits up to 5 seconds for network idle so client-side boards can load, then waits a short settle time.
5. `_looks_blocked()` checks the page title and body for CAPTCHA or anti-bot text.

The method returns a `NavResult(ok, status, final_url, error)` object instead of raising an exception, so the caller can record the failure and move on.

### Q10. Why do you use only one browser and one page at a time?
The original prototype loaded pages in parallel (`CONCURRENCY = 4`). That is faster, but it puts more load on websites and makes politeness harder to guarantee. Our `BrowserManager` owns one Chromium instance, one browser context and one page. Companies are processed one after another in batches of 5 (`BATCH_SIZE`). This keeps memory use low on a student laptop and makes rate limiting simple. Speed is not critical for this use case: a two-company live crawl took about 26 seconds.

---

## 3. Python modules and architecture

### Q11. Describe the overall architecture.
The system has five layers:
1. **Collection:** `data/companies.csv` is read by `src/company_catalog.py`. `src/job_scraper.py` builds `CompanyTarget` objects, the adapters in `src/adapters/` read the pages, and `src/browser_manager.py` handles navigation.
2. **Processing:** `build_job_record()` in `src/extractors.py` normalises each job, and `deduplicate()` in `src/deduplication.py` removes duplicates.
3. **Storage:** the `JobStore` class in `src/storage.py` manages three SQLite tables.
4. **AI/ML:** `src/recommendation.py` (TF-IDF, cosine similarity and the score), `src/clustering.py` (K-Means) and `src/resume_parser.py`.
5. **Presentation:** `app.py` and the `ui/` package with 8 pages.

Crawls started from the UI run as a background process through `src/crawl_runner.py`. The same crawl can be run from `src/cli.py`. The architecture diagram is on the Settings & About page (screenshot `21_about_architecture.png`).

### Q12. What does `run_crawl()` in `src/job_scraper.py` do?
`run_crawl(targets, mode, ...)` is the orchestrator. It opens one `BrowserManager` and goes through the targets in batches of `BATCH_SIZE`. For each target it picks the adapter class from the `ADAPTERS` dictionary using `target.platform` and calls `adapter.collect(target)`. Raw rows are converted with `build_job_record()`. Each batch is deduplicated and saved immediately with `JobStore.upsert_jobs()`, so a later failure never loses work that already succeeded. It fills a `CrawlSummary` (companies attempted, succeeded and failed, listings seen, jobs saved, new jobs, duplicates removed, pages visited, seconds and errors) and writes it to the `crawl_runs` table in a `finally` block. If one adapter raises an exception, the error is logged and the crawl continues with the next company.

### Q13. What is the `JobRecord` model?
`JobRecord` in `src/models.py` is a Python dataclass with the 21 fields listed in `JOB_FIELDS`. Examples are title, company, location, work_mode, min/max_experience_years, employment_type, description, skills, eligibility, salary, deadline, apply_url, source, data_mode, category, is_fresher_friendly and discovered_at. The same field order is used for the SQLite table, the CSV export and the JSON export, so every part of the system shares one schema. Unknown values stay empty or `None`; the docstring states that they are "never guessed". `from_dict()` cleans incoming values, for example converting NaN to `None` and a comma-separated skills string into a list.

### Q14. Where is configuration stored, and why?
All tunable values are in `config/settings.py`. These include paths, `HEADLESS`, `NAV_TIMEOUT_MS` (25,000), `MAX_RETRIES` (2), `REQUEST_DELAY_SECONDS` (1.5), `BATCH_SIZE` (5), `MAX_DETAIL_PAGES_PER_COMPANY` (8), `RESPECT_ROBOTS_TXT`, `USER_AGENT`, the recommendation weights, the eligibility factors and the TF-IDF parameters. They can be overridden with environment variables or a local `.env` file (see `.env.example`). Website selectors are in `config/sources.json` and the skill dictionary is in `config/skills.json`. Keeping them out of the code means a layout change or a new skill needs only a configuration edit.

### Q15. How does the Streamlit UI avoid recomputing everything on every click?
Streamlit re-runs the whole page script on every interaction, so `ui/state.py` caches the expensive work. Job data is cached with `st.cache_data` and the fitted `JobRecommender` with `st.cache_resource`. Both cache keys include `data_signature()`, which is the pair of modification times of `database/jobs.db` and `data/sample_jobs.json`. Changing a filter or switching pages therefore never re-runs a crawl or re-fits TF-IDF, but new data from a crawl is picked up automatically because the file time changes. Match scores for the current profile are cached in `st.session_state` under a key built from an MD5 hash of the profile.

---

## 4. HTML selectors and website adapters

### Q16. What is an adapter, and why are there three?
An adapter is a small class that knows how to read one family of websites. All adapters inherit from `BaseAdapter` in `src/adapters/base.py` and implement `collect(target)`, which returns an `AdapterResult` (status, listings_seen, raw_jobs, error, detail_pages). The three adapters are:
- `GreenhouseAdapter`: public Greenhouse boards (`job-boards.greenhouse.io/<token>`)
- `LeverAdapter`: public Lever boards (`jobs.lever.co/<token>`)
- `GenericCareerPageAdapter`: the Python port of the original Node.js scraper, for any other career page

The structured job boards give clean, reliable fields, while the generic adapter is a best-effort fallback. This is the Strategy design pattern: `run_crawl()` chooses the adapter at run time from the `ADAPTERS` dictionary.

### Q17. Give examples of the CSS selectors you use.
- **Greenhouse:** each job is `tr.job-post` (a table row with class `job-post`). The title is `p.body--medium`, the location is `p.body__secondary`, and the detail-page description is `div.job__description`.
- **Lever:** each job is `div.posting`. The title uses the attribute selector `[data-qa='posting-name']`, the link is `a.posting-title`, and `.commitment` and `.workplaceTypes` give the employment type and work mode.
- **Generic:** the adapter tries attribute-contains selectors in order, such as `[class*='job-card']`, `[class*='job-listing']` and `li[class*='job']`, and finally `article` and `tr`.

All selectors are stored in `config/sources.json`, not in Python code.

### Q18. How does the generic adapter handle an unknown career page?
`GenericCareerPageAdapter._listing_elements()` tries each selector in `listing_selectors`. It accepts the first one that matches between 1 and 500 elements that contain text. For each element, the first line becomes the title and the remaining lines become the description; table cells are split on tab characters. A row is kept only if its title has no senior word and the text shows an entry-level signal or a relevant role. If no selector matches, the adapter falls back to the prototype's method: it scans visible text lines longer than 20 characters that contain a fresher keyword, keeping at most 25. Jobs without their own link point to the career page and are marked `url_is_shared`, so they get a composite ID instead of a URL-based one.

### Q19. How do you decide which detail pages to open?
Opening every job's detail page would be slow and impolite, so `BaseAdapter.detail_priority(title)` ranks the listings:

| Return value | Meaning |
|---|---|
| `None` | senior or unrelated title (skipped) |
| 0 | entry-level and technical title |
| 1 | entry-level title |
| 2 | technical title with no stated level |

`visit_details()` sorts the rows by this priority and opens at most `max_detail_pages` (default 8; the UI slider defaults to 5). For each opened page it reads the description with the `_OUTERMOST_TEXT_JS` script and removes boilerplate lines such as "Apply now".

### Q20. What happens if a website changes its layout?
The selectors stop matching, so the adapter finds zero listings or empty fields. It does not crash, because every helper (`_text`, `_href`) catches exceptions and returns an empty string. The crawl summary then shows the company with 0 jobs or with an error, so the problem is visible. The fix is usually a one-line selector edit in `config/sources.json`, with no change to Python code. The offline fixtures in `data/fixtures/career_pages/` and the integration test `tests/test_scraper_fixtures.py` let us confirm that the adapters still work after an edit.

### Q21. How does pagination work on Greenhouse boards?
`GreenhouseAdapter.collect()` loads the board URL, then loads pages 2, 3 and so on by appending `?page=N`, up to `max_pages = 5` from `config/sources.json`. It stops early if a page adds no new job links or if the row count reaches `MAX_LISTINGS_PER_COMPANY` (200). Seen links are kept in a set, so the same job is never added twice across pages. Lever boards show all postings on one page, so the Lever adapter reads a single page, also capped at 200 listings.

---

## 5. Data extraction and cleaning (`src/extractors.py`)

### Q22. How do you extract the experience requirement?
`parse_experience()` uses four regular expressions:

| Pattern | Matches, for example |
|---|---|
| `_RANGE_RE` | "0-2 years", "1 to 3 yrs" |
| `_PLUS_RE` | "3+ years" |
| `_MIN_RE` | "minimum 5 years", "at least 2 years" |
| `_PLAIN_RE` | "4 years of professional experience" |

Ranges and "N+" patterns are accepted only if the letters "exp" appear within 60 characters. This stops "a 4-year B.Tech degree" from being read as experience. Implausible values are rejected: a minimum above 30 years, a maximum above 40, or a maximum lower than the minimum. The earliest valid match in the text is used. If no number is found, `_FRESHER_EXP_RE` looks for phrases such as "fresher", "no prior experience", "0 years" or "entry level" and returns 0 to 1 years. Otherwise the function returns `None`, which the UI shows as "Experience not specified".

### Q23. How are the salary and the deadline extracted?
`extract_salary()` matches a currency (₹, Rs, INR, $, USD) followed by an amount with optional units (LPA, lakh, k, crore) and an optional period (per month, per annum, CTC, stipend). It also matches forms such as "4-6 LPA" and "7 LPA". A match is accepted only if a salary-related word (salary, CTC, stipend, compensation, package, pay, LPA, or a currency sign) is nearby, so "a team of 25 engineers" is never treated as a salary.

`extract_deadline()` first finds a keyword such as "apply by", "last date to apply", "application deadline" or "closing date". It then parses a date within the next 40 characters in one of four formats: YYYY-MM-DD, DD/MM/YYYY (Indian day-first), "30 November 2026" or "December 1, 2026". Invalid dates such as 31/02/2026 are rejected. Both functions return an empty string when nothing is published.

### Q24. How do you detect employment type, work mode and eligibility?
- **Employment type:** `detect_employment_type()` applies ordered regex rules (Internship, Apprenticeship, Graduate Trainee, Contract, Part-time, Full-time). It checks the title first, then the source's own employment field, then the description. So "Software Engineer Intern" stays an internship even if the board's badge says "Full Time Employee".
- **Work mode:** `detect_work_mode()` checks the location and the board's workplace field for Hybrid, Remote or On-site. In the description it accepts only strong phrases such as "fully remote" or "work from home", so "you will work with remote teams" correctly stays Unknown.
- **Eligibility:** `extract_eligibility()` splits the description into sentences. It keeps up to two sentences (at most 300 characters) that mention B.Tech, BCA, MCA, degree, graduate, batch, CGPA, percentage or eligibility.

### Q25. How is a job classified as fresher-friendly?
`is_fresher_friendly()` checks the evidence in this order:
1. A senior word in the title (senior, lead, principal, staff, director, manager, architect and so on) excludes the job. The exception is a title that also has a fresher signal and no strong senior word, so "Associate Product Manager – Fresher" is kept.
2. If a minimum experience was parsed, the job is fresher-friendly only when that minimum is at most 1 year.
3. Internship, Graduate Trainee and Apprenticeship employment types are included.
4. Otherwise, fresher keywords in the title or description decide.

All keyword matching uses the word-boundary patterns in `src/keywords.py`.

### Q26. How is the text cleaned before extraction?
`src/text_utils.py` has three main helpers:
- `strip_html()` turns block tags (p, div, br, li, h1 to h6, tr) into line breaks, removes the other tags and decodes HTML entities.
- `clean_whitespace()` collapses runs of spaces, including non-breaking spaces.
- `normalize_for_matching()` lower-cases the text and removes accents and punctuation, but keeps the characters + # . / - so that skill names such as c++, c#, node.js and ci/cd survive.

`build_job_record()` also removes a trailing " — Company" suffix from titles and normalises the application URL. If the title or company is missing, it returns `None`, so incomplete rows are dropped rather than stored half-empty.

### Q27. How are skills extracted?
`src/skills.py` matches aliases from `config/skills.json`, a dictionary of 123 canonical skills. For example, "scikit-learn" has the alias "sklearn" and "kubernetes" has "k8s". Each skill is compiled into one regex with custom boundaries, `(?<![a-z0-9+#])` and `(?![a-z0-9+#])`, so "java" does not match inside "javascript" and "c" does not match inside "c++". Ambiguous short names such as "go", "r" and "c" are matched only through explicit aliases such as "golang" or "r programming". The method is fully transparent: every detected skill can be traced back to a dictionary alias, and the user can correct the list in the UI.

### Q28. How are jobs assigned to a category?
`categorize_job()` uses `CATEGORY_RULES`, a list of 10 categories such as Data Science & AI, Data Analytics & BI, Software Development, QA & Testing, Cybersecurity and UI/UX, each with its own keywords. Each keyword hit in the title scores 3 points. Each hit in the description scores 1 point, with at most 3 points per keyword. The category with the highest total wins, and "Other" is returned when nothing matches. It is a transparent rule-based classifier, not a trained model.

---

## 6. Deduplication

### Q29. How do you detect duplicate jobs?
`src/deduplication.py` makes each `job_id` from the first 16 hexadecimal characters of the SHA-1 hash of the normalised application URL. `normalize_url()` lower-cases the scheme and host, removes the fragment and the trailing slash, and drops tracking parameters such as `utm_*`, `gh_src`, `lever-source`, `ref`, `fbclid` and `gclid`. When there is no URL, or several jobs share one page URL, the hash is taken of a composite key `company|title|location` instead, after lower-casing and removing punctuation. `deduplicate()` also checks the composite key separately, so the same job posted on two different URLs is still caught.

### Q30. At which stages does deduplication happen?
It happens at three stages:
1. **Within a crawl:** `run_crawl()` calls `deduplicate()` on every batch before saving.
2. **Across crawls:** `job_id` is the PRIMARY KEY of the SQLite `jobs` table, and `upsert_jobs()` updates an existing row instead of inserting a copy.
3. **Across sources:** `_finalise()` in `src/data_loader.py` runs `deduplicate()` again when sample and collected data are combined.

This is why re-running the demo crawl shows "Jobs saved 14" but "New jobs 0".

### Q31. Why hash the URL instead of storing the URL itself as the key?
A hash gives a short, fixed-length ID (16 hex characters, or 64 bits) that is safe to use as a primary key and as a widget key in the Streamlit interface. It is stable: the same normalised URL always gives the same ID, so the same job is recognised on every crawl. With 64 bits, an accidental collision is practically impossible for a dataset of thousands of jobs. The full URL is still stored in the `apply_url` column for the "Apply" button.

---

## 7. CSV vs JSON vs SQLite

### Q32. Why did you choose SQLite as the main store?
SQLite is a serverless, file-based database built into Python's standard library (`sqlite3`), so it needs no installation or database server. It gives transactions, a primary key for upserts, SQL queries, indexes and constraints. `src/storage.py` defines three tables:
- `jobs`: collected job records
- `applications`: the user's tracker, with a JSON snapshot of each job
- `crawl_runs`: the history of every crawl with its statistics and errors

A single-user local application fits SQLite well. The crawler process writes while the UI reads, and the connection timeout of 10 seconds handles brief locks.

### Q33. Why is the company catalogue a CSV file?
The catalogue is reference data that a person may want to read or extend. CSV opens directly in Excel or Google Sheets and is easy to edit and review. Adding a company needs no code change: `load_catalogue()` validates the columns, removes duplicate company names (for example "Acme Pvt Ltd" and "ACME"), and sets the verification status where it is missing. The verifier (`python -m src.cli verify-catalogue`) writes its results back into the same file.

### Q34. Where do you use JSON, and how do the CSV and JSON exports differ?
JSON is used where the data is nested or needs metadata: the sample dataset (`data/sample_jobs.json`), the selector configuration (`config/sources.json`), the skill dictionary, the crawl status file and exports. In the CSV export, `to_csv_bytes()` joins the skills list into one comma-separated string so it fits one cell. In the JSON export, `to_json_bytes()` keeps skills as a real list. It also adds `exported_at`, `record_count`, `data_modes` and a note that sample and demo_fixture records are fictional. CSV suits spreadsheets, while JSON suits programs that will process the data further.

---

## 8. Recommendation logic, TF-IDF and cosine similarity

### Q35. Explain TF-IDF as used in your project.
TF-IDF stands for Term Frequency – Inverse Document Frequency. It turns each text into a vector in which words that are frequent in that document but rare across the collection get high weight. `JobRecommender` uses scikit-learn's `TfidfVectorizer` with `sublinear_tf=True`, English stop words, unigrams and bigrams (`ngram_range=(1, 2)`) and at most 5,000 features. With scikit-learn's default smoothed IDF and L2 normalisation, the formulas are:

```
tf(t, d)  = 1 + ln(count of t in d)        (0 if t is absent)
idf(t)    = ln((1 + n) / (1 + df(t))) + 1
w(t, d)   = tf(t, d) × idf(t), then each document vector is divided by its L2 norm
```

Here n is the number of job documents and df(t) is the number of jobs that contain term t. A common word such as "team" gets a low weight, while a distinctive term such as "pytorch" or the bigram "machine learning" gets a high weight.

### Q36. What is cosine similarity, and why did you use it?
Cosine similarity measures the angle between two vectors:

```
cos(p, j) = (p · j) / (‖p‖ × ‖j‖)
```

TF-IDF weights are never negative, so the value lies between 0 (no shared terms) and 1 (identical direction). Because our vectors are already L2-normalised, the cosine equals their dot product. It compares the direction of the vectors rather than their length, so a long job description is not favoured just for being long. We compute it with `sklearn.metrics.pairwise.cosine_similarity`, and the test `test_cosine_similarity_of_identical_text_is_one` confirms that identical text gives 1.0.

### Q37. How are the job document and the candidate document built?
`build_job_document()` joins the job title (repeated twice, `TITLE_WEIGHT_REPEAT = 2`, to give it more weight), the skills, the category, the experience text, the employment type and the description. `CandidateProfile.to_document()` joins the candidate's skills, the preferred roles (repeated for extra weight) and the optional resume text. Before vectorising, `preprocess()` protects symbol-based skills by rewriting c++ as "cplusplus", c# as "csharp", node.js as "nodejs", .net as "dotnet" and ci/cd as "cicd". The vectoriser is fitted on the job documents only. The profile is then projected into the same vocabulary with `transform()`, so profile words that appear in no job are ignored.

### Q38. State the exact scoring formula and explain each component.
`JobRecommender.score_all()` computes:

```
score = 100 × F_elig × (0.50·S_text_rel + 0.30·S_skill + 0.20·S_pref) / (sum of weights used)
```

| Component | Definition |
|---|---|
| `S_text_rel` | cosine similarity divided by the best cosine in the current dataset, so the best text match is 1.0 |
| `S_skill` | number of the job's listed skills that the candidate has, divided by the number of skills the job lists |
| `S_pref` | mean of role match and location match |
| `F_elig` | 1.0 if the job's minimum experience fits the candidate, 0.9 if the job does not state it, 0.5 if it needs more |

Role match is the share of the words in the candidate's preferred role (minus stop words) that appear in the job title. Location match is 1 when a preferred city appears in the job's location, or when the job is remote and the candidate accepts remote work. The result is a relevance score from 0 to 100.

### Q39. Work through the example in your project.
The worked example is computed live on the Settings & About page (screenshot `22_worked_example.png`). The vectoriser is fitted on three sample jobs only. The profile is: skills python, machine learning, pandas, sql; preferred role Machine Learning Engineer; preferred location Bengaluru; 0 years of experience.

| Sample job | Cosine | S_text_rel | S_skill | S_pref | F_elig | Score |
|---|---|---|---|---|---|---|
| Machine Learning Engineer Intern (Mumbai) | 0.3232 | 1.0000 | 4/8 = 0.50 | (1.0 + 0) / 2 = 0.5 | 1.0 (eligible) | **75.0** |
| Senior Data Scientist (5+ years, Ahmedabad) | 0.1806 | 0.5589 | 2/7 = 0.2857 | 0 | 0.5 (not eligible) | **18.3** |
| Junior Data Analyst (Kochi) | 0.0337 | 0.1044 | 2/7 = 0.2857 | 0 | 1.0 (eligible) | **13.8** |

How each score is calculated:
- **ML Engineer Intern:** 0.5 × 1.0 + 0.3 × 0.5 + 0.2 × 0.5 = 0.75, so the score is 75.0. The role match is 1.0 because all three role words appear in the title; the location match is 0 because Mumbai is not Bengaluru.
- **Senior Data Scientist:** (0.2795 + 0.0857 + 0) × 0.5 = 0.1826, so the score is 18.3.
- **Junior Data Analyst:** 0.0522 + 0.0857 + 0 = 0.1379, so the score is 13.8.

### Q40. Why divide the cosine by the best cosine in the dataset?
A short profile of a few words is compared with long job descriptions full of other terms, so raw cosine values are small, typically 0.0 to 0.3. If the raw value were used directly, text similarity would contribute very little compared with skill match, and every score would look low. Dividing by the highest cosine in the current dataset rescales the text component so the best text match gets 1.0. The consequence is that `S_text_rel` is relative. It changes when the loaded dataset changes, and even a weak best match receives 1.0. For transparency, the raw cosine is always shown next to the Text bar (for example "cos 0.33").

### Q41. What happens when a score component cannot be computed?
If a job lists no recognisable skills, `S_skill` is `None`. If the candidate gives no preferred roles or locations, `S_pref` is `None`. A missing component is dropped, and the remaining weights are renormalised by dividing by the sum of the weights actually used. For example, with no skills on the job, the formula becomes (0.5·S_text_rel + 0.2·S_pref) / 0.7. A value of zero is not the same as missing: a location mismatch gives 0 and still counts, as in the worked example. The explanation text then says "job lists no recognisable skills, so skill match was not scored", and `test_job_without_skills_redistributes_weight` checks this case.

### Q42. What are "Similar jobs" and "Top TF-IDF keywords" in the job-details dialog?
`similar_jobs(job_id)` computes the cosine similarity between one job's TF-IDF vector and every other job's vector, and returns the closest ones. This is a content-based "more like this" feature. `top_terms(job_id)` returns the job's highest-weighted TF-IDF terms, which act as a lightweight keyword extractor. Both reuse the matrix that was fitted once for the recommender, so they cost almost nothing. They show that the same vector representation can support search, recommendation and exploration.

---

## 9. K-Means clustering and silhouette

### Q43. How do you use K-Means in the project?
`cluster_jobs()` in `src/clustering.py` groups the loaded jobs by the similarity of their text, without using any labels. It builds the same job documents and vectorises them with a separate `TfidfVectorizer` (at most 3,000 features, and `min_df=2`, so a term must appear in at least two jobs). It runs `KMeans(n_clusters=k, n_init=10, random_state=42)` for k from 3 to 10 (limited to n − 1) and computes the silhouette score for each k with cosine distance. It keeps the k with the highest silhouette. The Analytics page then shows the chosen k, a chart of silhouette against k, a table of clusters with example titles and the top 6 terms of each cluster centre, and a chart comparing clusters with the rule-based categories.

### Q44. What is the silhouette score, and what values did you get?
For each job i, a(i) is its mean distance to the other jobs in its own cluster, and b(i) is its mean distance to the jobs in the nearest other cluster. Then:

```
s(i) = (b(i) − a(i)) / max(a(i), b(i))
```

The silhouette score is the mean of s(i) over all jobs and ranges from −1 to 1; a higher value means better-separated clusters. Our values are low, around 0.15 to 0.20. On the 155-job dataset the app chose k = 10 with 0.187 (screenshot `14_analytics_clusters.png`); the exact value depends on the loaded data and the k range. The value also keeps rising slowly as k grows, with no clear peak, which means the clusters overlap. This is expected, because fresher job descriptions share a lot of vocabulary such as "intern", "python", "data" and "team". We report this honestly and treat the clusters as an exploration aid, not as definitive job classes.

### Q45. K-Means uses Euclidean distance. Why is it suitable for TF-IDF vectors compared with cosine?
Our TF-IDF vectors are L2-normalised, so each has length 1. For unit vectors, ‖a − b‖² = 2 × (1 − cos(a, b)). This means that Euclidean distance and cosine similarity rank pairs of documents in exactly the same order. Minimising Euclidean distance on these vectors is therefore equivalent to grouping documents by cosine similarity, which is why we can measure the silhouette with the cosine metric. This is a standard approach for clustering text documents.

---

## 10. Resume parsing and privacy

### Q46. How does resume parsing work?
`src/resume_parser.py` reads a PDF with `pypdf` or a DOCX file with `python-docx`, entirely in memory through `io.BytesIO`. For DOCX files it also reads text inside tables. The text is cleaned and passed to `extract_skills()`, the same dictionary matcher used for job descriptions. For example, the fictional demo resume `data/fixtures/resumes/sample_resume_fictional.pdf` gives 11 skills, including python, pandas, scikit-learn, sql and power bi. The detected skills are pre-filled in the Skills box, and the user must confirm or correct them before searching. The resume text is also added to the candidate's TF-IDF document.

### Q47. How do you protect the user's privacy?
The uploaded file is processed in memory on the local computer. It is never written to disk, never stored in the database and never sent to any server. The extracted text is kept only in the Streamlit session and is cleared with the "Clear resume" button or when the session ends. Upload size is limited to 5 MB (`MAX_RESUME_MB` and `maxUploadSize` in `.streamlit/config.toml`), and Streamlit usage statistics are disabled (`gatherUsageStats = false`). Tracker data stays in `database/jobs.db` on the same machine. This follows the principle of data minimisation.

### Q48. What happens with a scanned or corrupt resume?
`extract_text()` validates the file before parsing. It rejects unsupported extensions, empty files, files over 5 MB, files whose first bytes do not look like a PDF (`%PDF`) or DOCX (`PK`), and password-protected PDFs, each with a clear message. Any other library error is converted into a `ResumeParseError` with a friendly message instead of a crash. If fewer than 20 characters of text are found, the user is told that the resume is probably a scanned image and is asked to type their skills manually, because we do not perform OCR. These cases are covered by `tests/test_resume_parser.py`.

---

## 11. Testing

### Q49. How did you test the system?
We wrote 100 pytest tests in 11 files, and all passed in about 30 seconds on macOS arm64 with Python 3.13 (`python -m pytest`).

| Test file | Tests |
|---|---|
| `test_extractors.py` | 28 |
| `test_recommendations.py` | 16 |
| `test_ui_smoke.py` | 12 |
| `test_filters.py` | 8 |
| `test_resume_parser.py` | 7 |
| `test_deduplication.py` | 6 |
| `test_storage.py` | 6 |
| `test_skills.py` | 5 |
| `test_company_catalog.py` | 4 |
| `test_export_and_data.py` | 4 |
| `test_scraper_fixtures.py` (integration) | 3 |

The unit tests check behaviour rather than accuracy figures. Examples: "a 4-year degree" is not read as experience, "Apply by 31/02/2026" gives no deadline, the score equals the documented formula, and a senior job is marked not eligible. `setup.sh` also runs the full test suite after installation.

### Q50. How do the Playwright integration tests work without internet?
`tests/test_scraper_fixtures.py` runs real Chromium against the 5 local fixture pages in `data/fixtures/career_pages/`. These pages use five layouts: cards, an HTML table, a JavaScript-rendered list, a Greenhouse-style board and a Lever-style board.

`test_fixture_crawl_end_to_end` runs `run_crawl(fixture_targets())` into a temporary database. It asserts that:
- 5 companies succeed with 1 duplicate removed and 14 jobs saved
- senior roles such as "Principal Research Scientist" are skipped
- the JavaScript-rendered "NLP Engineer Intern" is found
- the Machine Learning Intern is read as Remote with the salary "₹20,000 per month"

The second test checks that a stop request is honoured, and the third checks that `file://` URLs are allowed by the robots cache. The browser tests are skipped automatically if Chromium is not installed.

### Q51. How do you test the user interface?
`tests/test_ui_smoke.py` uses Streamlit's `AppTest` to run the pages headlessly without opening a browser. It checks that each of the 8 page views renders without an exception, and that the full app with navigation renders. It also checks three interactions: clicking "Try a demo profile" creates a profile, the recommendations page lists "Top ... matches" for the demo profile, and typing "nlp" in the keyword box returns results. Before any application module is imported, `tests/conftest.py` points `JOBS_DB_PATH` to a temporary folder, so tests never touch the real `database/jobs.db`.

---

## 12. Limitations

### Q52. What are the main limitations of your system?
- Website layouts change, so selectors in `config/sources.json` may need updating.
- Many company sites block automated browsers with HTTP 403/429 or CAPTCHAs, and we skip those sites by design.
- Rule-based extraction can miss unusual phrasing; such fields are left empty rather than guessed.
- TF-IDF matches words, not meanings, so "ML" and "statistical learning", or "Bengaluru" and "Bangalore", are not treated as the same.
- The text score is relative to the loaded dataset, and the weights are not learned from data.
- The sample dataset is fictional; only `live` records come from real job boards.
- The application is single-user and local, and there is no OCR for scanned resumes.

### Q53. Why did the live crawl save only 8 jobs out of 206 listings?
On 25 October 2026 the crawl of Groww (Greenhouse) and Paytm (Lever) scanned 206 listings: 196 from Paytm and 10 from Groww. Most were experienced or senior roles, which the system is designed to exclude, and detail pages were capped at 4 per company in that run. The 8 saved jobs were the entry-level ones, mostly HR and talent-acquisition internships at that moment. This shows that the filter is strict and that the results depend on what companies have posted on the day. It also shows a limitation: on any given day, the public boards of a few companies may contain few technical fresher roles.

### Q54. How accurate is your extraction?
We have not measured extraction accuracy on a labelled corpus, so we do not claim a percentage. Instead, the 28 tests in `tests/test_extractors.py` check specific positive and negative cases, such as salary formats, Indian day-first dates, invalid dates, degree durations and the legacy substring bugs. The design principle is "do not invent": if a salary, deadline or experience value is not clearly published, the field stays empty and the UI says "Not published" or "Experience not specified". Building a hand-labelled set of real postings to measure precision and recall is listed as future work.

---

## 13. Ethical scraping

### Q55. How does your crawler respect robots.txt?
Before every navigation, `BrowserManager.goto()` asks `RobotsCache.allowed(url)`, which uses Python's `urllib.robotparser` and caches one parser per host. If robots.txt disallows the path for our user agent, the page is skipped and logged as "Disallowed by robots.txt (skipped)". If robots.txt itself returns 401 or 403, we treat the whole site as disallowed. If robots.txt returns another 4xx (no file), the site is allowed, following the usual convention. A `Crawl-delay` value in robots.txt is honoured when it is larger than our own delay. Local `file://` fixture pages are not websites, so no robots check or delay applies to them.

### Q56. How do you limit the load you put on websites?
- `REQUEST_DELAY_SECONDS = 1.5` means at least 1.5 seconds between pages on the same host. This is deliberately higher than Lever's robots.txt `Crawl-delay` of 1.
- One browser and one page work at a time.
- Companies are processed in batches of 5, and the UI allows at most 5 companies per live crawl.
- Detail pages are capped (default 8, UI slider 1 to 15), and listings are capped at 200 per company.
- Retries are limited to `MAX_RETRIES = 2` attempts in total, with a back-off, and only for timeouts and 5xx errors.
- The user agent honestly identifies the tool: "FresherJobDiscovery/1.0 (B.Tech AIML academic project; low request rate)".

### Q57. What does the crawler do when it meets a CAPTCHA or bot protection?
It stops and skips the page; it never tries to get around the protection. HTTP 401, 403 and 429 responses are returned at once as "access restricted (not bypassed)", without any retry. After a page loads, `_looks_blocked()` searches the title and short page bodies for markers such as "captcha", "are you a robot", "verify you are human", "cf-challenge" and "unusual traffic". If one is found, the result is "CAPTCHA / anti-bot page detected (skipped, not bypassed)". We do not rotate user agents or IP addresses, solve CAPTCHAs, use stealth plugins or log in. Such companies simply appear in the error list of the crawl summary.

### Q58. Is web scraping legal and ethical? What about personal data?
We collect only publicly displayed job postings, which are meant to be read by job seekers, and no personal data about individuals. We respect robots.txt and rate limits, never bypass access controls, identify ourselves honestly, and link back to the original posting through the "Apply" button rather than republishing it as our own. robots.txt is a technical convention and not a legal licence, so a website's terms of use should be reviewed before any large-scale or commercial use. For the user's own data, the resume is processed in memory and not stored, which follows the data-minimisation principle found in data-protection laws such as India's Digital Personal Data Protection Act, 2023. The sample data is fictional and uses the reserved example.com domain, so no real company is misrepresented.

---

## 14. Future scope

### Q59. What improvements would you make in the future?
- Use the public JSON job-board APIs of Greenhouse and Lever where available, and keep Playwright for JavaScript-heavy pages.
- Add adapters for more applicant tracking systems.
- Replace or combine TF-IDF with sentence embeddings (for example Sentence-BERT) to capture meaning and synonyms.
- Normalise locations ("Bangalore" and "Bengaluru") and skill synonyms.
- Add scheduled crawls with alerts for new matching jobs.
- Add OCR for scanned resumes.
- Deploy a multi-user version with PostgreSQL and authentication.
- Use named-entity recognition (for example spaCy) for more robust field extraction.

### Q60. How would you evaluate the recommender properly in future?
At present there is no labelled ground truth about which jobs suit which candidate, so no accuracy is claimed. In future, user actions such as saving, applying or reaching the interview stage in the Application Tracker could serve as implicit relevance labels. With those labels, we could measure ranking metrics such as Precision@k and nDCG. We could also run a small user study with classmates who rate the top 10 recommendations. Finally, the weights 0.5/0.3/0.2 could be tuned, or learned with a learning-to-rank model, once enough labelled data exists.

---

## 15. Questions about the actual source code

### Q61. What does `BrowserManager.goto` do when it receives HTTP 403?
It returns immediately with `NavResult(ok=False, status=403, final_url=page.url, error="HTTP 403: access restricted (not bypassed)")`. It does not retry, change headers or wait and try again; the same applies to 401 and 429. The adapter then marks the company as failed with that error, and `run_crawl()` adds it to `summary.errors` and moves on to the next company. By contrast, HTTP 5xx errors and timeouts are treated as temporary and retried up to `MAX_RETRIES` attempts with a back-off of 1.5 × attempt seconds. HTTP 404 returns at once as "page not found". In the catalogue check, 24 of the 44 unverified companies are unverified because of exactly this kind of HTTP 403 response.

### Q62. What does `RobotsCache` do if robots.txt returns 403 or cannot be downloaded?
`RobotsCache._parser()` downloads `<host>/robots.txt` once per host with our user agent and a 10-second timeout, and caches the parser. On an `HTTPError` with code 401 or 403, it parses the rules `User-agent: *` and `Disallow: /`, so the whole site is treated as disallowed. Other HTTP errors such as 404 mean there is no robots file, which by convention means the site is allowed. On a network error, it logs a warning and assumes the site is allowed so that the crawl does not crash. In that situation the page navigation itself usually fails and is reported. For non-HTTP URLs such as `file://`, it returns `None`, which means allowed with no crawl delay.

### Q63. How does `deduplicate()` choose which duplicate to keep?
For each record, `deduplicate()` looks for an existing record with the same `job_id` or the same composite key. On a collision it compares their `_richness()` score: description length + 50 × number of skills + 20 if a salary is present + 20 if a deadline is present. The richer record is kept; on a tie, the record seen first is kept. The earliest `discovered_at` of the two is preserved, and the original `job_id` is reused, so IDs stay stable. The function returns the list of unique records and the number removed. In the demo crawl, the "Data Analyst – Fresher" listing that appears twice on the Nimbus Analytics page (once as "Featured role") is the one duplicate removed.

### Q64. Why does the UI run crawls in a subprocess?
Streamlit re-runs the page script on every interaction, and a crawl takes 20 to 30 seconds or more. If the crawl ran inside the script, it would freeze the page or be interrupted by reruns. `crawl_runner.start_crawl()` therefore launches `python -m src.cli crawl --mode ... --status-file ...` with `subprocess.Popen(..., start_new_session=True)` and writes its output to `logs/crawl_subprocess.log`. This also isolates the Playwright browser from the web server: if Chromium crashes or hangs, the UI keeps working, and Playwright's synchronous driver stays out of Streamlit's server threads. Progress is shared through `database/crawl_status.json`, which the `_status_panel` fragment (`@st.fragment(run_every=2)`) reads every 2 seconds. The UI and the command line also share one code path, and `is_running()` ensures only one crawl runs at a time.

### Q65. How is a running crawl stopped safely?
The "Stop crawl" button calls `crawl_runner.stop_crawl()`. It writes a stop file (`database/crawl_status.stop`) and sends SIGTERM to the crawler process. In `src/cli.py`, the SIGTERM and SIGINT handlers only set a flag; they do not kill the process. `run_crawl()` receives `should_stop=lambda: flag or STOP_FILE.exists()` and checks it before each company. When it is true, the status becomes "stopped", the current batch is still deduplicated and saved, the `with BrowserManager(...)` block closes Chromium cleanly, and `finish_run()` records the run in `crawl_runs`. The integration test `test_stop_request_is_honoured` checks this behaviour.

### Q66. Why is the status file written to a temporary file and then renamed with `os.replace()`?
The crawler writes the status file while the UI reads it every 2 seconds. If the crawler wrote directly into the file, the UI could read a half-written file and fail to parse the JSON. `write_status()` therefore writes to `crawl_status.tmp` first and then calls `os.replace(tmp, path)`, which replaces the file in a single atomic step on the same file system. The reader sees either the old complete file or the new complete file, never a partial one. As an extra safeguard, `read_status()` returns an empty dictionary if the JSON cannot be decoded.

### Q67. What is `_OUTERMOST_TEXT_JS` in `src/adapters/base.py`, and why is it needed?
It is a small JavaScript function run inside the page through `page.evaluate()`. It selects all elements that match the description selector, keeps only the outermost ones (those not contained inside another match) and joins their `innerText`. Without this step, a selector such as `main, article, [class*='description']` could match both a container and an element inside it, and the same paragraph would be captured twice. Running it inside the browser also gives the rendered text after JavaScript has run. Afterwards, `visit_details()` removes boilerplate lines such as "Apply for this job" and "Back to jobs".

### Q68. How does `JobStore.upsert_jobs()` preserve the first-seen date?
For each record, it first checks `SELECT 1 FROM jobs WHERE job_id = ?`. If the row exists, it updates every column except `job_id` and `discovered_at`, and sets `last_seen_at` to the current time. If the row is new, it inserts all fields and counts the row as new. It returns `(saved, newly_inserted)`, which is where the "Jobs saved" and "New jobs" figures in the crawl summary come from. As a result, a job keeps its original discovery date across crawls, while `last_seen_at` shows when it was last seen. `test_discovered_at_is_preserved_on_update` verifies this.

### Q69. How do the tests avoid touching the real database?
`config/settings.py` reads `DATABASE_PATH` from the `JOBS_DB_PATH` environment variable when the module is imported. `tests/conftest.py` creates a temporary folder with `tempfile.mkdtemp()` and sets `JOBS_DB_PATH` to a file inside it before it imports any application module. In addition, the `store` fixture creates a fresh `JobStore` in pytest's `tmp_path` for each storage test. So running the tests, even during a demonstration, never changes the user's tracker or collected jobs. The `minimal_pdf()` helper in the same file builds a tiny valid PDF in code, so the PDF tests need no external sample file.

### Q70. How is scraped text prevented from injecting HTML or scripts into the UI?
Job cards use custom HTML with `unsafe_allow_html=True` for badges and layout, so any text from a website could in principle contain tags. Every scraped value placed in that markup goes through `esc()` in `ui/components.py`, which calls `html.escape()`, so `<script>` is shown as plain text and never executed. The "Apply" button is shown only for `http://` or `https://` links. `fixture_path()` opens a `file://` preview only if the file is inside `data/fixtures/career_pages/`, which prevents path-traversal tricks. This follows the rule of never trusting data that comes from outside the application.

---

## 16. Tricky examiner questions

### Q71. Is this really AI?
It uses classical, explainable AI and machine-learning techniques rather than deep learning. The recommender is based on the TF-IDF vector space model with cosine similarity, a standard information-retrieval and NLP method. Clustering uses K-Means, an unsupervised machine-learning algorithm, with silhouette-based model selection. Extraction uses rule-based natural-language processing (regular expressions and a skill dictionary). There is no neural network, no large language model and no supervised model trained on hiring data. "AI-powered" in the title refers to these components, and we chose them on purpose because every score can be explained.

### Q72. Did you train a model? What is its accuracy?
No supervised model was trained. TF-IDF is a text-vectorisation method: "fitting" the vectoriser only learns the vocabulary and the IDF weights from the job texts, without any labels. K-Means is also unsupervised. Since there is no labelled data saying which jobs are right for which candidate, an accuracy figure cannot be computed honestly, and we do not claim one; the About page states this. What we can show is tested behaviour: an ML profile ranks the ML job first, the score equals the documented formula, and senior jobs are penalised, all checked by `tests/test_recommendations.py`.

### Q73. Is the score the probability of getting the job?
No. The score is a relevance score from 0 to 100, used only to rank jobs for one profile within the loaded dataset. It is not a probability of being shortlisted or hired, and the interface says so next to the score ("relevance score (0–100, not a hiring probability)"). It is calculated from text similarity, skill overlap, preferences and an eligibility factor, with no information about employers' decisions. Because the text component is relative to the best match in the dataset, scores from different datasets cannot be compared directly.

### Q74. Where do the weights 0.5, 0.3 and 0.2 come from?
They are illustrative default values chosen by judgement, not learned from data or experimentally optimised, and `config/settings.py` says so in a comment. The reasoning is that overall text similarity is the broadest signal, explicit skill overlap is the next most important, and role and location preferences matter but should not dominate. `JobRecommender` checks that the weights add up to 1.0 and raises a `ValueError` otherwise, which `test_weights_must_sum_to_one` verifies. They are easy to change in one place, and tuning or learning them from user feedback is part of future work.

### Q75. Your silhouette score is low. Did the clustering fail?
A low silhouette (around 0.15 to 0.20 on our data) means the groups overlap, not that the code is wrong. Fresher job descriptions share a lot of vocabulary ("intern", "python", "data", "team", "graduate"), so clean separation is not expected. The silhouette also keeps rising slowly as k increases, without a clear peak, which is another sign that there is no strong natural cluster structure. We report the measured value instead of hiding it, and we use the clusters only as an exploration aid. The Analytics page compares the clusters with our rule-based categories, and the top terms still form sensible themes such as cloud/networking or html/css/figma.

### Q76. Are your 133 sample jobs real? Isn't that fake data?
They are intentionally fictional, and the system labels them clearly. `scripts/generate_sample_data.py` generates 133 jobs for 22 fictional companies with a fixed random seed (42), and every link uses the reserved example.com domain. Each sample job goes through the same `build_job_record()` pipeline as scraped jobs. The sample data exists so that the demonstration, the analytics and the tests work offline, and so that we never show a real company's vacancy incorrectly. Real data comes from live crawls, such as the 8 jobs collected from Groww and Paytm on 25 October 2026. Every record carries a SAMPLE, DEMO CRAWL or LIVE badge.

### Q77. In your worked example, why does the senior job (18.3) rank above the junior analyst job (13.8)?
The Senior Data Scientist posting shares more text with the profile (cosine 0.1806 against 0.0337), because it talks about machine learning and Python. Even after the 0.5 eligibility penalty, its score (18.3) stays slightly above the Junior Data Analyst score (13.8), whose text is about SQL and dashboards rather than machine learning. The penalty halves a job's score but does not remove it, because some users may still want to see such roles. On the AI Recommendations page, the option "Hide jobs that need more experience" is ticked by default, so a fresher would not see the senior job at all. This is a deliberate design choice and is explained in the score text ("asks for 5+ years — more than your 0 (score ×0.5)").

### Q78. Greenhouse and Lever offer public JSON APIs. Why scrape HTML with a browser?
That is a fair point: for those two platforms, their public job-board APIs would be faster and more stable than reading HTML. We used browser automation because the project's objective is to demonstrate Playwright-based collection, and because the same approach also covers generic career pages that have no API and often need JavaScript rendering. The adapter design means that an API-based adapter could replace the HTML adapter for Greenhouse and Lever without changing the rest of the pipeline. We list this as future work.

### Q79. Your catalogue says 474 companies are "verified". Does that mean they are hiring?
No. "Verified" only means that the company's official URL responded with HTTP 2xx or 3xx when it was checked on 25 October 2026. The 44 unverified URLs are mostly protected sites, not dead links: 24 HTTP 403, 2 HTTP 429 and 5 anti-bot pages. The other unverified cases are 10 HTTP/2 protocol errors and 3 timeouts. Most entries (423) are homepage URLs, where we could not confirm an exact careers path, and 95 are careers-page URLs. Vacancies appear only when a crawl actually collects a listing. The Company Explorer page states this in a notice above the table.
