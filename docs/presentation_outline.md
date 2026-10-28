# Presentation Outline

**Project:** AI-Powered Fresher Job Discovery System Using Playwright
**Course:** B.Tech AIML, 7th Semester Minor Project (GGSIPU, AIML-451)
**Length:** 12 slides, about 9 minutes, plus questions

## Timing plan

| # | Slide | Time | Running total |
|---|---|---|---|
| 1 | Title and introduction | 0:30 | 0:30 |
| 2 | Problem statement | 0:45 | 1:15 |
| 3 | Objectives and scope | 0:35 | 1:50 |
| 4 | System architecture | 0:50 | 2:40 |
| 5 | Playwright workflow | 1:00 | 3:40 |
| 6 | Information extraction and deduplication | 0:45 | 4:25 |
| 7 | AI/ML: TF-IDF, cosine similarity and the relevance score | 1:30 | 5:55 |
| 8 | User interface walkthrough | 1:00 | 6:55 |
| 9 | Testing and results | 0:40 | 7:35 |
| 10 | Limitations and ethical scraping | 0:45 | 8:20 |
| 11 | Future scope | 0:25 | 8:45 |
| 12 | Conclusion | 0:25 | 9:10 |

For a 7-minute slot, shorten slides 6, 8 and 9 to about 30 seconds each and leave the live UI tour to the demonstration (see `docs/demo_script.md`).

**Slide design guidelines**
- Use one screenshot per slide, large and readable, from the `screenshots/` folder.
- Use at least 24 pt text and keep each bullet to one line where possible.
- Put the scoring formula and the worked-example table on slide 7 in a large font, because the panel will ask about them.
- Use the same colours as the application (indigo `#4F46E5`, teal `#0D9488`) for a consistent look.

---

## Slide 1 — Title and introduction
**Time:** 0:30
**Visual:** `01_dashboard.png` as a faded background or a small image on the right.

**Slide content**
- AI-Powered Fresher Job Discovery System Using Playwright
- B.Tech AIML, 7th Semester Minor Project (AIML-451), GGSIPU
- [Student name(s), enrolment number(s)] · Guide: [Guide name]
- Python · Playwright (Chromium) · scikit-learn · SQLite · Streamlit

**Speaker notes**
"Good morning. Our project is an AI-powered fresher job discovery system. It uses Playwright browser automation to collect fresher and internship listings from public company job boards, extracts structured information from them, and recommends the most relevant jobs to a student using an explainable text-similarity model. I will cover the problem, the architecture, the crawler, the AI part with a worked example, our test results and our limitations, and then show a short live demonstration."

---

## Slide 2 — Problem statement
**Time:** 0:45
**Visual:** a simple illustration of many career pages flowing into one dashboard, or no image.

**Slide content**
- Fresher openings are scattered across hundreds of company career pages and job boards.
- Many postings ask for years of experience or do not state the requirement at all.
- Modern career pages render jobs with JavaScript, so simple HTTP scraping misses them.
- Plain substring keyword filters are noisy: "intern" matches "international", and "lead" matches "leadership".

**Speaker notes**
"A final-year student usually opens dozens of career pages by hand. Most postings are for experienced candidates, and many do not even say how much experience they need. Many of these pages load their job lists with JavaScript, so a simple downloader sees an empty page. Our original Node.js prototype also showed that plain substring keyword matching gives false results. For example, 'intern' matched 'international' and 'lead' matched 'leadership'. We wanted a tool that collects listings politely, filters them correctly for freshers and explains its recommendations."

---

## Slide 3 — Objectives and scope
**Time:** 0:35
**Visual:** none (text slide), or small icons for the five objectives.

**Slide content**
- Collect public listings with Playwright from Greenhouse boards, Lever boards and generic career pages.
- Extract experience, salary, deadline, skills and eligibility; remove duplicates; store in SQLite.
- Rank jobs for a candidate profile or resume with explainable TF-IDF and cosine-similarity scoring.
- Provide an 8-page Streamlit UI covering search, recommendations, catalogue, tracker, analytics and crawler control.
- Out of scope: logging in, bypassing CAPTCHAs, auto-applying, predicting hiring outcomes.

**Speaker notes**
"We had four objectives: collection, extraction, recommendation and a usable interface. We started from a Node.js prototype of six JavaScript files with a 111-row company list that contained duplicates. We ported it to Python, fixed the keyword bugs with word-boundary regular expressions, and added everything else. We were also clear about what the system will not do. It never logs in, never bypasses bot protection, and never claims to predict whether someone will be hired."

---

## Slide 4 — System architecture
**Time:** 0:50
**Visual:** `21_about_architecture.png` (the architecture diagram from the Settings & About page), cropped to the diagram.

**Slide content**
- **Collection:** `companies.csv` (518 companies) → adapters (Greenhouse, Lever, Generic) → `BrowserManager`
- **Processing:** `extractors.py` (regex rules) → `deduplication.py` (URL hash and composite key)
- **Storage:** SQLite with the tables `jobs`, `applications` and `crawl_runs`, plus a fictional sample dataset
- **AI/ML:** TF-IDF and cosine similarity, an explainable score, K-Means clustering and a resume parser
- **UI:** Streamlit with 8 pages; crawls run in a separate background process

**Speaker notes**
"This is the pipeline. The company catalogue feeds the crawler. Each website family has its own adapter class, and one BrowserManager handles every page visit. Raw listings go through our extraction rules and the de-duplication step, and are saved in SQLite. The recommender and the clustering read from the database and from the fictional sample dataset. The Streamlit interface sits on top. One design point matters here: crawls run in a separate process started by `crawl_runner.py`, so the interface never freezes while Chromium is working, and the same crawl can also be run from the command line."

---

## Slide 5 — Playwright workflow
**Time:** 1:00
**Visual:** `17_crawl_in_progress.png` on the left and `18_crawl_completed.png` on the right. Keep `16_collect_jobs.png` as a backup.

**Slide content**
- For every page: robots.txt check → polite delay (at least 1.5 s per host) → `page.goto` (25 s timeout) → wait for network idle → check for a blocked page.
- HTTP 401/403/429 and CAPTCHA pages are skipped, never bypassed; only timeouts and 5xx errors are retried.
- Selectors live in `config/sources.json`; detail pages open fresher titles first, up to a per-company limit.
- Work is done in batches of 5 and saved after every batch; a Stop button ends a crawl cleanly.
- Offline demo crawl: 5/5 pages OK, 14 jobs, 1 duplicate removed, about 20 s. Live crawl of Groww and Paytm: 206 listings, 8 entry-level jobs, 26 s.

**Speaker notes**
"This is what happens for every page. BrowserManager first checks robots.txt, then waits at least one and a half seconds since the last request to that host, then opens the page in Chromium and waits for the JavaScript to finish. If the site answers 403 or 429, or shows a CAPTCHA, we record it and move on; we never try to get around it. The adapter reads the listings with CSS selectors from a config file and opens detail pages for fresher-looking titles first. For the demonstration we built five fictional local pages with five layouts: cards, a table, a JavaScript-rendered list, a Greenhouse-style board and a Lever-style board. Playwright collects 14 jobs from them and removes one duplicate in about 20 seconds. On 25 October we also ran a real crawl of Groww and Paytm: 206 listings were scanned in 26 seconds, and 8 entry-level jobs were saved."

---

## Slide 6 — Information extraction and deduplication
**Time:** 0:45
**Visual:** `05_job_details_dialog.png` (the job details dialog with extracted fields).

**Slide content**
- Regex rules in `src/extractors.py` read experience ("0-2 years", "3+ years", "minimum 5 years", "fresher"), salary (₹ amounts, LPA, stipends) and deadlines ("Apply by 30 November 2026").
- Rules also detect employment type, work mode, eligibility sentences, the category and whether a job is fresher-friendly.
- Skills are matched from a dictionary of 123 skills with aliases and word boundaries ("java" does not match "javascript").
- Values that are not published stay empty; nothing is guessed.
- Duplicates are found with a SHA-1 hash of the normalised URL plus a company|title|location key, and the richer record is kept.

**Speaker notes**
"Once a page is read, our extraction rules turn free text into fields. For example, the experience rule only accepts '4-6 years' if the word 'experience' is nearby, so 'a 4-year B.Tech degree' is not mistaken for experience. A salary is accepted only if a word like CTC, stipend or LPA is nearby. Deadlines need a keyword like 'apply by' and a valid date, so 31 February is rejected. Skills come from a transparent dictionary of 123 skills. If a value is not published, we leave it empty instead of guessing. For duplicates, we remove tracking parameters from the URL and hash it. We also compare company, title and location, so the same job posted twice is caught."

---

## Slide 7 — AI/ML: TF-IDF, cosine similarity and the relevance score
**Time:** 1:30
**Visual:** one card from `07_recommendations.png` (score box, Text/Skills/Preference bars with the raw cosine, matched and missing skills), next to the worked-example table below recreated in large type. `22_worked_example.png` shows the same table computed live in the app.

**Slide content**
- **TF-IDF:** jobs and the candidate profile become vectors (unigrams and bigrams, sublinear tf, English stop words removed): tf = 1 + ln(count), idf = ln((1+n)/(1+df)) + 1, then L2 normalisation.
- **Cosine similarity:** cos(p, j) = (p · j) / (‖p‖ ‖j‖); S_text_rel = cosine ÷ best cosine in the dataset.
- **Score:** score = 100 × F_elig × (0.50·S_text_rel + 0.30·S_skill + 0.20·S_pref) / (sum of weights used)
- **Components:** S_skill = matched job skills ÷ job's listed skills; S_pref = mean(role match, location match); F_elig = 1.0 eligible, 0.9 unknown, 0.5 needs more experience.
- **Clustering:** K-Means on TF-IDF vectors, with k chosen by the silhouette score (cosine) over k = 3 to 10. The silhouette is low (about 0.15 to 0.20), so the clusters overlap.

**Worked example to show on the slide**

The profile is: skills python, machine learning, pandas, sql; role Machine Learning Engineer; location Bengaluru; 0 years of experience.

| Sample job | Cosine | S_text_rel | S_skill | S_pref | F_elig | Score |
|---|---|---|---|---|---|---|
| Machine Learning Engineer Intern (Mumbai) | 0.3232 | 1.00 | 4/8 = 0.50 | (1 + 0)/2 = 0.5 | 1.0 | **75.0** |
| Senior Data Scientist (5+ yrs) | 0.1806 | 0.5589 | 2/7 = 0.2857 | 0 | 0.5 | **18.3** |
| Junior Data Analyst | 0.0337 | 0.1044 | 2/7 = 0.2857 | 0 | 1.0 | **13.8** |

- ML Engineer Intern: 0.5×1.0 + 0.3×0.5 + 0.2×0.5 = 0.75 → **75.0**
- Senior Data Scientist: (0.2795 + 0.0857) × 0.5 → **18.3**
- Junior Data Analyst: 0.0522 + 0.0857 → **13.8**

**Speaker notes**
"This is the AI part. We fit a TF-IDF vectoriser on all job documents and project the candidate's skills, roles and resume text into the same space. Cosine similarity measures how close the two vectors point. A short profile against long descriptions gives small cosines, so we divide by the best cosine in the dataset, and the best text match becomes 1.0. We then combine three parts: 50 percent text, 30 percent skill overlap and 20 percent role and location preference. The result is multiplied by an eligibility factor. In the example, the ML intern role gets 75 because its text is the best match, it has 4 of its 8 listed skills, its title matches the preferred role, and the experience fits; only the location misses. The senior role is halved because it asks for 5 years. Two honest points: the weights are illustrative defaults, not learned from data, and the score ranks relevance; it is not a hiring probability. We also cluster jobs with K-Means. The silhouette is low, around 0.15 to 0.2, which tells us the clusters overlap, and we report that as measured. Please quote the silhouette value the app shows on the day, because it changes with the loaded data."

---

## Slide 8 — User interface walkthrough
**Time:** 1:00
**Visual:** a 2 × 3 grid of `01_dashboard.png`, `03_job_search.png`, `06_resume_skills_extracted.png`, `09_company_explorer.png`, `11_application_tracker.png` and `14_analytics_clusters.png`. Keep `08_score_explanation.png` (the profile form with the resume skills filled in) ready as a backup.

**Slide content**
- **Dashboard:** search, quick filters (Fresher, Internship, Graduate Trainee, Entry-level), key metrics, "Try a demo profile"
- **Job Search:** keyword AND search, filters, sorting by relevance, pagination, CSV/JSON export
- **AI Recommendations:** profile form, resume upload (PDF/DOCX, read in memory), ranked cards with matched and missing skills
- **Company Explorer** (518 companies), **Application Tracker** (Saved → Applied → Interview → Rejected/Offer), **Analytics**, **Collect Jobs**, **Settings & About**
- Every record carries a SAMPLE, DEMO CRAWL or LIVE badge

**Speaker notes**
"The interface has eight pages. The dashboard gives a quick search and summary numbers. Job Search has full filters, and its filters never trigger a new crawl, because the data and the model are cached. On AI Recommendations, a student can type skills or upload a resume. The file is read in memory and never stored, and every result shows matched skills in green and missing skills in red. The Company Explorer lists our 518-company catalogue. The tracker stores the student's own application status locally. Analytics computes every chart from the loaded data. Finally, every record carries a badge, so fictional sample data can never be confused with a real vacancy. I will show these pages live in the demonstration."

---

## Slide 9 — Testing and results
**Time:** 0:40
**Visual:** a screenshot of the terminal showing `100 passed` (take one before the presentation), or the table below. `18_crawl_completed.png` is a backup visual.

**Slide content**
- 100 pytest tests, all passed in about 30 s (macOS arm64, Python 3.13): unit, Playwright integration and Streamlit AppTest UI tests
- Offline demo crawl: 5/5 companies OK, 21 listings seen, 14 jobs saved, 1 duplicate removed, 18 to 23 s
- Live crawl on 25 Oct 2026 (Groww + Paytm, max 4 detail pages): 206 listings, 8 entry-level jobs, 26 s
- Catalogue check on 25 Oct 2026: 474 of 518 URLs verified, 44 unverified (mostly bot protection), 0 missing
- Worked example (75.0 / 18.3 / 13.8) is reproduced live by the app; a test checks that every score equals the formula

| Test file | Tests |
|---|---|
| test_extractors.py | 28 |
| test_recommendations.py | 16 |
| test_ui_smoke.py | 12 |
| test_filters.py | 8 |
| test_resume_parser.py | 7 |
| test_deduplication.py, test_storage.py | 6 each |
| test_skills.py | 5 |
| test_company_catalog.py, test_export_and_data.py | 4 each |
| test_scraper_fixtures.py (integration) | 3 |

**Speaker notes**
"We have 100 automated tests, and all pass in about 30 seconds. They include regex cases such as invalid dates and degree durations, a test that recomputes every score from the documented formula, an end-to-end Playwright crawl of the fixture pages, and Streamlit UI tests that render every page. We do not quote an accuracy percentage, because there is no labelled ground truth for job relevance. Instead, the tests check specific behaviours. For the catalogue, 'verified' means the URL responded on that date, not that the company is hiring. Most of the 44 unverified sites blocked automated access, which we respect."

---

## Slide 10 — Limitations and ethical scraping
**Time:** 0:45
**Visual:** `19_live_crawl_tab.png` (the live crawl tab with the politeness notice).

**Slide content**
- **Limitations:** website layouts change; many sites block bots; rule-based extraction can miss unusual phrasing; TF-IDF misses synonyms ("Bangalore" vs "Bengaluru").
- **Limitations:** the score is relative to the dataset; the weights are not learned; the sample data is fictional; the live yield depends on the day; there is no OCR for scanned resumes.
- **Ethics:** robots.txt is checked before every page, Crawl-delay is honoured, and pages on one host are at least 1.5 s apart.
- **Ethics:** one page at a time, batches of 5, an honest user agent, no login, and no CAPTCHA or bot-protection bypass.
- **Privacy:** resumes are processed in memory only; tracker data stays on the local machine; usage statistics are disabled.

**Speaker notes**
"We want to be open about the limitations. Websites change, many block automated browsers, and our rules can miss unusual wording. TF-IDF matches words, not meanings, so it cannot tell that Bangalore and Bengaluru are the same city. The live crawl found only eight entry-level jobs among 206 listings, because on that day most openings were for experienced candidates. On ethics, the crawler respects robots.txt and rate limits, identifies itself honestly as an academic project, and treats a 403, a 429 or a CAPTCHA as 'please do not enter'. It skips those sites instead of trying to get around them. Resumes never leave the computer and are not stored."

---

## Slide 11 — Future scope
**Time:** 0:25
**Visual:** none (text slide).

**Slide content**
- Use the public JSON job-board APIs where available; add more applicant-tracking-system adapters.
- Use semantic matching with sentence embeddings, plus normalisation of skill and location synonyms.
- Evaluate with user feedback (saved and applied jobs) using Precision@k and nDCG, then tune or learn the weights.
- Add scheduled crawls with alerts for new matching jobs, and OCR for scanned resumes.
- Build a multi-user deployment with PostgreSQL and authentication.

**Speaker notes**
"For future work, the most valuable step is proper evaluation. The tracker already records which jobs a student saves and applies to, and that feedback could be used to measure ranking quality and then tune the weights. We would also add sentence embeddings so the system understands synonyms, use the official board APIs where they exist, and add scheduled crawls with alerts."

---

## Slide 12 — Conclusion
**Time:** 0:25
**Visual:** `02_dashboard_recommended.png` (the dashboard with recommendations), with "Thank you — Questions?" at the bottom.

**Slide content**
- An end-to-end pipeline: polite Playwright collection → rule-based extraction → deduplication → SQLite → explainable ranking
- AI that can be explained: TF-IDF, cosine similarity, a transparent score, and unsupervised K-Means reported honestly
- Verified with 100 passing tests, an offline demo crawl and a real live crawl
- Built responsibly: robots.txt, rate limits, no bypassing, privacy-preserving resume handling

**Speaker notes**
"To conclude, we built a complete and working system: from polite browser automation to an explainable recommendation for each student. Every number we have shown can be traced back to code and tests, and we have been honest about what the model is and is not. Thank you. I will now show a short live demonstration, and then we are happy to take your questions."

---

## Backup material (not part of the timed talk)

Keep these ready in case the panel asks:
- **Catalogue verification breakdown:** 518 companies in 22 industries; 423 homepage and 95 careers-page URLs; 20 public boards (Greenhouse: Groww, Druva, HackerRank, InMobi and 11 others; Lever: Paytm, Meesho, CRED, Zeta, FamPay). Unverified reasons: 24 HTTP 403, 10 HTTP/2 protocol errors, 5 anti-bot pages, 3 timeouts, 2 HTTP 429.
- **Command-line commands:** `python -m src.cli crawl --mode fixtures`, `python -m src.cli crawl --mode live --companies "Groww,Paytm" --max-details 5`, `python -m src.cli stats`, `python -m src.cli export --dataset all`.
- **Other screenshots:** `04_job_search_filters.png`, `10_company_explorer_search.png`, `12_analytics_jobs.png`, `13_analytics_skills.png`, `15_analytics_catalogue.png`, `20_settings.png`.
- **Viva preparation:** see `docs/viva_questions.md`.
