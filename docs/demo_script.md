# Live Demonstration Script

**Project:** AI-Powered Fresher Job Discovery System Using Playwright
**Course:** B.Tech AIML, 7th Semester Minor Project (GGSIPU, AIML-451)
**Length:** about 8 minutes
**Audience:** the evaluation panel

This script lists, for each step, exactly what to type, what to click, what to point at and what to say. Words in **bold** are the exact labels on the screen. A fallback plan for Wi-Fi or website problems is in Section 5.

---

## 1. Pre-demo checklist

### The day before
- [ ] Run the one-time setup if it has not been done on this laptop: `./setup.sh`. It creates the `fresherjobs` Conda environment with Python 3.12 if Conda is installed (otherwise a `.venv`), installs the packages and Chromium, and runs the tests.
- [ ] Run the tests and keep a screenshot of the result: `python -m pytest`. It should report 100 passed in about 30 s.
- [ ] Run one offline demo crawl: `python -m src.cli crawl --mode fixtures`. It should print 5/5 companies OK and 14 jobs saved.
- [ ] If you plan a live crawl, test it once at home: `python -m src.cli crawl --mode live --companies "Groww,Paytm" --max-details 4`.
- [ ] Copy the `screenshots/` folder and the presentation to a USB drive or phone as a last-resort backup.
- [ ] Keep a mobile hotspot ready in case the venue Wi-Fi fails.

### 15 minutes before the panel arrives
- [ ] Plug in the charger. Turn on Do Not Disturb. Close WhatsApp, Slack, mail and any music apps.
- [ ] Close other apps that may use port 8501, such as another Streamlit app or a Jupyter server. Check the port:
  ```bash
  lsof -iTCP:8501 -sTCP:LISTEN
  ```
  If this prints a line, quit that app, or end it with `kill <PID>` using the PID from the output.
- [ ] Open Terminal (Terminal 1) and start the app:
  ```bash
  cd /Users/tanishchhonkar/Pictures/nishita/ai-powered-fresher-job-discovery-system
  conda activate fresherjobs          # or: source .venv/bin/activate
  ./run.sh
  ```
  `run.sh` prints `Opening http://localhost:8501`. If it prints `Port 8501 is busy, trying 8502`, use the port it reports.
- [ ] Open the browser at **http://localhost:8501**. Set the zoom to 110 to 125 percent so the panel can read the screen.
- [ ] In the sidebar, check that **Dataset** is **All available data (sample + collected)** and that the badges show **SAMPLE 133 jobs**, **DEMO CRAWL 14 jobs** and **LIVE 8 jobs**. The LIVE count can grow after new live crawls.
- [ ] Open a second Terminal tab (Terminal 2, press Cmd+T), go to the project folder and activate the environment. Keep it ready for the test run and the command-line backup.
- [ ] In Finder, open `data/fixtures/resumes/` so the fictional resume `sample_resume_fictional.pdf` is easy to pick in the upload dialog.
- [ ] Open `screenshots/` in a second Finder window, in case you need the backup.

### Optional: let the demo crawl show new records
If the panel sees the crawl create new records, the demo is more convincing. Before the panel arrives, go to **Settings & About**, open the **Settings** tab and expand **Delete collected records**. Choose **demo_fixture**, tick the confirmation box and click **Delete**. The demo crawl will then show **New jobs 14** instead of 0, and the **DEMO CRAWL** badge will reappear in the sidebar. Do this only if you tested the offline crawl the day before.

### Last 2 minutes
- [ ] Reload the browser tab (Cmd+R) so no candidate profile from a previous session remains.
- [ ] Optional: start the test suite now in Terminal 2 (`python -m pytest`). It finishes in about 30 s and uses a temporary database, so it does not affect the running app. You will show its result in Step 9.
- [ ] Never click the **Deploy** button at the top right of the Streamlit page.
- [ ] Do not run `python -m src.cli verify-catalogue` during the demo. It checks all 518 URLs and rewrites the status columns in `data/companies.csv`.

---

## 2. Timing overview

| Step | Page | What it shows | Time |
|---|---|---|---|
| 1 | Terminal and Dashboard | how the app starts, data-mode badges, key numbers | 0:00 – 0:50 |
| 2 | Collect Jobs: offline demo crawl | Playwright on 5 layouts, polite navigation, deduplication | 0:50 – 2:00 |
| 3 | Job Search | filters, job details, extracted fields, Save | 2:00 – 2:50 |
| 4 | AI Recommendations | resume parsing, TF-IDF ranking, score explanation | 2:50 – 4:20 |
| 5 | Company Explorer, then live crawl | 518-company catalogue, real public job boards | 4:20 – 5:20 |
| 6 | Application Tracker (crawl still running) | the UI stays responsive, local status tracking | 5:20 – 5:50 |
| 7 | Collect Jobs: live crawl result | real results, errors skipped and not bypassed | 5:50 – 6:15 |
| 8 | Analytics | charts, K-Means clusters, honest silhouette | 6:15 – 7:00 |
| 9 | Settings & About, Terminal 2 | worked example 75.0 / 18.3 / 13.8, 100 tests passed | 7:00 – 7:45 |
| 10 | Close | summary | 7:45 – 8:00 |

If you are short of time, skip Step 6 and shorten Step 8 to the clusters tab only.

---

## 3. Step-by-step script

### Step 1 — Starting point and Dashboard (0:00 – 0:50)

**Do**
1. Show Terminal 1 briefly and point to the output of `./run.sh`: `Opening http://localhost:8501 (press Ctrl+C in this window to stop the app)`.
2. Switch to the browser. You are on the **Dashboard**.
3. Point to the sidebar badges **SAMPLE**, **DEMO CRAWL** and **LIVE**.
4. Point to the four metric tiles: **Jobs in loaded dataset**, **Companies in catalogue** (518, with 474 verified URLs), **Strong matches** and **Tracked applications**.
5. Point to the quick-filter buttons **Fresher (N)**, **Internship (N)**, **Graduate Trainee (N)** and **Entry-level (N)**.

**Say**
"The app is started with one command, `./run.sh`, and opens in the browser on localhost. The whole system runs on this laptop. Every job carries one of three badges. SAMPLE means a fictional offline record, DEMO CRAWL means it was collected by Playwright from our local demo pages, and LIVE means it was collected from a real public job board. Fictional data can therefore never be mistaken for a real vacancy. The catalogue has 518 companies, and 474 of their URLs responded when we checked them on 25 October."

---

### Step 2 — Offline demo crawl with Playwright (0:50 – 2:00)

**Do**
1. In the sidebar, click **Collect Jobs (Playwright)**. The **Offline demo crawl** tab is open.
2. Point to the table of five fictional companies: Nimbus Analytics (generic), Riverstone Infotech (generic), QuantaLeap AI (generic), Orbit Fintech (greenhouse) and Meridian Health Systems (lever).
3. Tick **Show the browser window while crawling (headed mode)**.
4. Click **Start demo crawl**. A Chromium window opens and visits the pages one by one.
5. While it runs, about 20 s, point to the progress bar ("Crawling Nimbus Analytics — 1/5 companies") and explain the steps below.
6. When it finishes, point to the results: **Companies OK 5/5**, **Listings seen 21**, **Jobs saved 14**, **Duplicates removed 1**, and the per-company table.

**Say while it runs**
"This is real Chromium automation driven by Playwright. Our five local demo pages use five different layouts: job cards, an HTML table, a list that JavaScript renders after 800 milliseconds, a Greenhouse-style board and a Lever-style board. For every page, the BrowserManager first checks robots.txt, keeps a polite delay between requests to the same website, waits for the JavaScript to finish, and checks whether the page is a CAPTCHA or a block page. The crawl runs in a separate background process, so the interface stays responsive."

**Say after it finishes**
"All five companies were read successfully. From 21 listings, it saved 14 fresher-relevant jobs. Senior roles such as 'Principal Research Scientist' and 'Engineering Manager' were skipped. One duplicate was removed: Nimbus shows the same Data Analyst job twice, once as a featured role. If New jobs shows 0, the records already existed. They were updated rather than inserted twice, because the job ID is a hash of the normalised URL."

---

### Step 3 — Job Search and job details (2:00 – 2:50)

**Do**
1. Click **View collected jobs** below the crawl status. This switches the dataset to **Collected only (live + demo crawl)** and opens **Job Search**, showing DEMO CRAWL and LIVE cards.
2. On a DEMO CRAWL card, such as **Machine Learning Intern** from Nimbus Analytics, click **Demo page**. This shows the local page Playwright actually crawled. Close the dialog.
3. In the sidebar **Dataset** box, switch back to **All available data (sample + collected)**.
4. In **Keywords**, type `python intern` and press Enter. Point to the line "**N** of 155 jobs match"; every keyword must match.
5. Open **More filters** and show one filter, for example **Maximum experience required (years)** set to 1, or **Location**.
6. Click **Details** on one card. Point to the extracted fields: **Work mode**, **Employment type**, **Experience**, **Salary / stipend** ("Not published" if absent), **Application deadline**, **Eligibility**, **Skills found** and **Top TF-IDF keywords**.
7. Click **Save to tracker**, or close the dialog and click **Save** on the card.

**Say**
"Search and filtering never start a new crawl, because the data and the model are cached. The details dialog shows what our regular-expression rules extracted. Experience is read from phrases such as '0 to 2 years' or 'fresher'. A salary is accepted only near words like CTC or stipend, and a deadline only after words like 'apply by'. If a value is not published, we show 'Not published' instead of guessing. I will save this job to the tracker for later."

---

### Step 4 — AI Recommendations with resume parsing (2:50 – 4:20)

**Do**
1. In the sidebar, click **AI Recommendations**.
2. Expand **Optional: extract skills from your resume (PDF or DOCX)**. Point to the privacy notice.
3. Under **Resume file**, click Browse and choose `data/fixtures/resumes/sample_resume_fictional.pdf` (a fictional resume made for the demo).
4. Click **Extract skills**. Point to the message "Read 637 characters from sample_resume_fictional.pdf and found 11 skills", and to the skills now filled in the **Skills** box.
5. In the form, fill in:
   - **Preferred job roles**: `Machine Learning Engineer, Data Analyst`
   - **Preferred locations**: `Bengaluru, Remote`
   - **Your experience (years)**: `0`
   - Keep **Remote jobs are fine** and **Hide jobs that need more experience** ticked.
6. Click **Get recommendations**.
7. On the top card, point to the score box (**#1 relevance**), the badge **Experience fits**, the green **Matched** skills, the red **Not in your profile** skills, the explanation sentence, and the three bars **Text · 50%** (with the raw cosine, for example "cos 0.36"), **Skills · 30%** and **Preference · 20%**.
8. Expand **How is the relevance score calculated?** and point to the formula.

**Say**
"The resume is read in memory only. It is not uploaded anywhere and not stored on disk or in the database. Skills are found with a transparent dictionary of 123 skills, so every detected skill can be traced, and the student can correct the list. For ranking, we turn every job and this profile into TF-IDF vectors and measure cosine similarity. The score is 100 times the eligibility factor times 0.5 text similarity, plus 0.3 skill match, plus 0.2 role and location preference. The text part is the cosine divided by the best cosine in the dataset, and the raw cosine is shown here for transparency. Two honest points: the weights are illustrative defaults, not learned from data, and this is a relevance score for ranking, not a probability of getting the job."

**If the file dialog is awkward:** click **Fill in the demo profile** instead. It fills in an example AIML-student profile, and you can then continue from point 6.

---

### Step 5 — Company Explorer and a live crawl (4:20 – 5:20)

Do this step only if the internet connection works. If it does not, use Fallback A in Section 5.

**Do**
1. In the sidebar, click **Company Explorer**. Point to the tiles: **Companies 518** (22 industries), **Verified URLs 474**, **Unverified 44**, **Missing URL 0** and **Public job boards 20**.
2. Point to the notice that a "verified" URL does not mean the company currently has a vacancy.
3. Turn on **Only companies with a public job board (Greenhouse / Lever)**. The table now shows the 20 board companies, including Groww and Paytm.
4. Click **Collect Jobs (Playwright)** in the sidebar, then click the tab **Live crawl (public job boards)**.
5. **Companies to crawl** starts with **MongoDB** and **Druva**. Remove both (click their ×), then choose **Groww** and **Paytm**.
6. Set **Detail pages to open per company** to **4**.
7. Check once more that the box shows exactly **Groww** and **Paytm**, then click **Start live crawl**.

The **Open in Collect Jobs** button on the Company Explorer page also works: it sends the selected companies to this box (a bug where that selection was reset by other clicks was fixed and is covered by an automated test). Selecting the companies directly on the Live crawl tab, as above, is the simplest route during a demo.

**Say**
"This catalogue of 518 companies is plain data in a CSV file, so it can be extended without changing code. Twenty of the companies have public Greenhouse or Lever job boards, which are the most reliable to crawl. The live crawl visits only public pages that robots.txt allows, one page at a time with at least a one-and-a-half-second delay. A site that answers 403 or 429, or shows a CAPTCHA, is skipped and reported, never bypassed. When we ran this on 25 October, it scanned 206 listings in 26 seconds and kept 8 entry-level jobs. Today's numbers depend on what these companies have posted."

---

### Step 6 — Application Tracker while the crawl runs (5:20 – 5:50)

**Do**
1. While the live crawl is still running, click **Application Tracker** in the sidebar. The page opens at once, which shows that the UI is not blocked.
2. In the table, change the **Status** of the job you saved in Step 3 from **Saved** to **Applied**, and type a note such as `Applied via portal`.
3. Click **Save changes**. Point to the message "Saved: 1 updated, 0 removed." and to the bar chart **Applications by status**.

**Say**
"The crawler is still working in its own process, yet the app responds normally. That is why we run crawls in a subprocess: the interface keeps reading progress from a status file every two seconds. The tracker statuses are entered by the student and stored only in the local SQLite database. They are not fetched from employers."

---

### Step 7 — Live crawl result (5:50 – 6:15)

**Do**
1. Click **Collect Jobs (Playwright)** in the sidebar. The **Crawl status** section shows the finished live crawl.
2. Point to **Companies OK**, **Listings seen**, **Jobs saved** and **New jobs**, and to the per-company table.
3. If there are errors, expand the error list ("... company error(s) — skipped, not retried aggressively") and read one aloud.

**Say**
"Here is the real result from today. The filter is strict: most listings on these boards are for experienced candidates, so only entry-level roles are kept. If a company had blocked us, it would appear in this error list as skipped, not bypassed. The records are now in SQLite with the LIVE badge, and every other page picks them up automatically."

---

### Step 8 — Analytics and clustering (6:15 – 7:00)

**Do**
1. Click **Analytics** in the sidebar. On the **Jobs** tab, point briefly to **Jobs by category** and **Fresher-friendly share**.
2. Click the **Skills & matching** tab. Point to **Most frequently requested skills (top 20)** and to the distribution of relevance scores for the current profile.
3. Click the **Job clusters (K-Means)** tab. Point to **Chosen k**, **Silhouette (cosine)**, the chart **Silhouette score for each k**, and the cluster table with **top_terms**.

**Say**
"Every chart is computed live from the loaded records. Here we group jobs with K-Means, an unsupervised algorithm, so no labels are used. The number of clusters is chosen by the silhouette score with cosine distance. I want to be honest about this value: it is low, around 0.15 to 0.2, which means the clusters overlap. Fresher job descriptions share a lot of vocabulary. The top terms still form sensible groups, such as cloud and networking, or HTML, CSS and Figma, so we use the clusters to explore the data, not as exact classes."

Read the silhouette value that is on the screen. It changes with the loaded data: with the 155-job dataset (133 sample + 14 demo crawl + 8 live) the current code, which searches k = 3 to 10, chose k = 10 with a silhouette of 0.187, as in screenshot `14_analytics_clusters.png`.

---

### Step 9 — Worked example and the test suite (7:00 – 7:45)

**Do**
1. Click **Settings & About** in the sidebar, then the **About the project** tab.
2. Point to the table **Part / What it really does / Technique**, and the sentence "The recommender is not trained on hiring outcomes ... so no accuracy figure is claimed".
3. Scroll to **Worked example of the relevance score**. Point to the three rows: **Machine Learning Engineer Intern 75.0**, **Senior Data Scientist 18.3** and **Junior Data Analyst 13.8**.
4. Switch to Terminal 2 and show the pytest result: **100 passed**. If you did not start it earlier, run `python -m pytest`; it takes about 30 s.

**Say**
"This worked example is calculated live by the same code. The ML intern job gets 75: its text is the best match, it has 4 of its 8 listed skills, its title matches the preferred role, and the experience fits; only Mumbai misses Bengaluru. The senior job is halved because it needs five years. Finally, the project has 100 automated tests, and all pass. They include regular-expression cases, a check that every score equals the formula, a full Playwright crawl of the demo pages, and tests that render every page of the interface."

---

### Step 10 — Close (7:45 – 8:00)

**Say**
"To summarise, the system collects public listings politely with Playwright, extracts and de-duplicates them, stores them in SQLite, and ranks them with an explainable TF-IDF model that we have described honestly. Thank you; we are happy to take questions."

Leave the app running for questions. Stop it only afterwards (see Section 6).

---

## 4. Optional command-line demonstration (if the panel asks)

Run these in Terminal 2 with the environment activated:

```bash
python -m src.cli stats                     # catalogue totals, stored jobs by mode, jobs available
python -m src.cli crawl --mode fixtures     # the same offline crawl from the terminal
python -m src.cli crawl --mode live --companies "Groww,Paytm" --max-details 5
python -m src.cli export --dataset all      # writes timestamped CSV and JSON files to exports/
python -m src.cli crawl --mode fixtures --headed   # same, with the browser window visible
```

The command-line fixture crawl prints a line per company, such as `[1/5] Riverstone Infotech — jobs saved: 0`, and ends with a summary line such as `Crawl completed: 5/5 companies OK, 14 jobs saved (0 new, 1 duplicates removed) in 21.5s` (the time varies between about 18 and 23 s). The app picks up the new data automatically, because its cache is keyed on the database file's modification time.

---

## 5. Fallback plan

| Problem | What to do | What to say |
|---|---|---|
| **A. No Wi-Fi, or live sites are slow** | Skip Step 5 and Step 7. The offline demo crawl in Step 2 needs no internet, because it reads local `file://` pages. To show real data, set **Dataset** to **Live only**: it shows the 8 LIVE jobs collected from Groww and Paytm on 25 Oct 2026. Show `screenshots/19_live_crawl_tab.png` for the live tab. | "Live results depend on the network and the websites, so the project includes an offline demo crawl with the same Playwright code, plus the records from our live run on 25 October." |
| **B. Live crawl reports errors** (HTTP 403/429, CAPTCHA, timeout) | Expand the error list and read the message, for example "HTTP 403: access restricted (not bypassed)". | "This is the designed behaviour. We skip protected pages and never bypass them." |
| **C. Live crawl saves 0 new jobs** | Point to **Listings seen** and **Jobs saved**. | "The records already existed and were updated, or today's listings had no entry-level titles. The filter is deliberately strict." |
| **D. Chromium does not start** ("Could not launch Chromium. Run `python -m playwright install chromium`") | Run `python -m playwright install chromium`, which needs internet. If that is not possible, skip the crawl steps, show `16_collect_jobs.png`, `17_crawl_in_progress.png` and `18_crawl_completed.png`, and use the sample data for every other step. | "All AI features work on the stored data. Here are the screenshots of the same crawl." |
| **E. Port 8501 is busy** | `run.sh` picks the next free port automatically and prints it, so open that URL. To pick a port yourself, run `streamlit run app.py --server.port 8502`. | — |
| **F. Blank page or error in the browser** | In Terminal 1, press Ctrl+C, run `./run.sh` again (it takes about 5 s) and reload the browser. All data is kept in SQLite. | "One moment, I am restarting the local server." |
| **G. "A crawl is already running"** | Wait for it to finish (the demo crawl takes about 20 s), or click **Stop crawl**. | "Only one crawl runs at a time, on purpose." |
| **H. Resume upload fails** | Click **Fill in the demo profile**, or type the skills in the form. | "Resume upload is optional; the profile can be typed in." |
| **I. Numbers look out of date** | **Settings & About**, **Settings** tab, **Refresh data from disk**. | — |
| **J. Laptop failure** | Present from the backup copy: show the slides, then the screenshots in order from `01_dashboard.png` to `22_worked_example.png`. | "Here are screenshots of every page from our test run." |

If the internet works but a live crawl is too risky in front of the panel, follow Fallback A and mention that a live run is available on request.

---

## 6. Stopping the app safely

1. **If a crawl is running**, open **Collect Jobs (Playwright)** and click **Stop crawl**, or let it finish (about 20 s for the demo crawl). The crawler runs in its own process session, so Ctrl+C in Terminal 1 does **not** stop it. When stopped, it finishes the current company, saves the batch, closes Chromium and records the run as "stopped".
2. **Stop the web app:** click Terminal 1, where `./run.sh` is running, and press **Ctrl+C** once. Wait until the shell prompt returns. If it does not return within a few seconds, press Ctrl+C once more.
3. **Close the browser tab.** If it shows "Connection error", that only means the server has stopped.
4. **Optional checks:**
   ```bash
   lsof -iTCP:8501 -sTCP:LISTEN          # prints nothing when the port is free
   ps aux | grep "src.cli crawl"         # shows only the grep line when no crawler is left
   conda deactivate
   ```
5. **Data safety:** jobs are saved to SQLite after every crawl batch, and tracker changes are saved when you click **Save changes**. Nothing else needs saving. Avoid `kill -9` unless a process does not respond to Ctrl+C or `kill <PID>`.

---

## 7. Quick reference

| Purpose | Command |
|---|---|
| One-time setup (environment, Chromium, tests) | `./setup.sh` |
| Activate the environment | `conda activate fresherjobs` (or `source .venv/bin/activate`) |
| Install the Playwright browser | `python -m playwright install chromium` |
| Run all tests | `python -m pytest` |
| Start the app | `./run.sh` or `streamlit run app.py` → http://localhost:8501 |
| Offline demo crawl | `python -m src.cli crawl --mode fixtures` |
| Live crawl | `python -m src.cli crawl --mode live --companies "Groww,Paytm" --max-details 5` |
| Statistics | `python -m src.cli stats` |
| Export CSV and JSON | `python -m src.cli export --dataset all` |
| Re-check catalogue URLs (not during the demo) | `python -m src.cli verify-catalogue` |
| Stop the app | Ctrl+C in the terminal running `./run.sh` |

For likely panel questions and model answers, see `docs/viva_questions.md`.
