# Fresher Jobs Scraper — Playwright Automation

Automates visiting the career pages of Indian companies, scans each page's
job listings, and flags openings that look suitable for freshers /
entry-level candidates (0–1 year experience, graduate trainee, internship
converts, etc.).

## Project Structure

```
job-scraper-project/
├── config/
│   └── companies.csv        # company_name, career_url, sector (seed list — extend to 500)
├── src/
│   ├── scraper.js           # main Playwright automation
│   ├── validateUrls.js      # pre-flight check: which career URLs are still live
│   ├── generateReport.js    # console summary of the last scrape
│   ├── keywords.js          # fresher/entry-level keyword rules
│   ├── loadCompanies.js     # CSV loader
│   └── logger.js            # winston logger (console + logs/scraper.log)
├── output/                  # generated: fresher_jobs.csv, fresher_jobs.json, summary.json
├── logs/                    # generated: scraper.log
├── package.json
└── README.md
```

## Setup

```bash
npm install
npm run install-browsers     # downloads the Chromium binary Playwright needs
```

## Usage

```bash
# 1. (Recommended) Check which career-page URLs are still valid
npm run validate-urls

# 2. Run the scrape
npm run scrape

# 3. Print a quick summary to the console
npm run report
```

Environment variables (optional):

| Variable        | Default | Purpose                                   |
|-----------------|---------|--------------------------------------------|
| `HEADLESS`      | `true`  | Set to `false` to watch the browser run    |
| `CONCURRENCY`   | `4`     | Number of career pages scraped in parallel |
| `NAV_TIMEOUT_MS`| `25000` | Per-page navigation timeout                |
| `MAX_RETRIES`   | `2`     | Retry attempts per company on failure      |

## Outputs

- `output/fresher_jobs.csv` — one row per fresher-relevant listing found (Company, Sector, Career URL, Listing Snippet)
- `output/fresher_jobs.json` — full detail per company, including scrape status and errors
- `output/summary.json` — aggregate counts (processed / successful / failed / total matches)
- `output/url_validation_report.csv` — output of `validate-urls`

## How the fresher-relevance filter works

`src/keywords.js` scans each listing's visible text for positive signals
(`fresher`, `entry level`, `graduate trainee`, `0-1 year`, `intern`, etc.)
and excludes listings that also contain senior-level signals (`5+ years`,
`senior`, `lead`, `architect`, ...). This is a heuristic, not a guarantee —
career sites phrase experience requirements inconsistently, so spot-check
results before relying on them.

## Important limitations (read before presenting this as production-ready)

1. **`config/companies.csv` ships with ~100 seed companies, not 500.**
   Verified, current career-page URLs for exactly 500 Indian companies
   can't be reliably hard-coded — companies frequently migrate career
   sites to third-party ATS platforms (Workday, Greenhouse, Lever, SAP
   SuccessFactors, etc.), which changes the URL and page structure.
   Expand the CSV using a source you can verify (e.g. each company's own
   website, or a company directory export) and re-run
   `npm run validate-urls` after every batch you add.
2. **No universal job-board layout exists.** `scraper.js` tries a list of
   common CSS selector patterns and falls back to whole-page text
   extraction, but some sites (heavily JS-driven SPAs, sites requiring
   a location/keyword search before showing results, sites behind bot
   protection like Cloudflare/Akamai) will need a site-specific selector
   added to `CANDIDATE_LISTING_SELECTORS` or a small custom handler.
3. **Respect each site's Terms of Service and `robots.txt`.** Some
   career sites disallow automated scraping. This project is intended
   for personal/academic job-search use with reasonable request rates
   (`CONCURRENCY` defaults to 4) — do not repurpose it for high-volume
   or commercial data collection without checking each site's terms.
4. **Rate limiting / IP blocks.** Large batch runs may trigger CAPTCHAs
   or temporary blocks. The retry logic handles transient failures, not
   CAPTCHAs — a blocked company will simply show up as `"status":
   "failed"` in the output for manual follow-up.
