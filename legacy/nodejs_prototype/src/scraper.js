/**
 * scraper.js
 * -----------
 * Automates visiting each company's career page with Playwright, extracts
 * visible job-listing text, filters it for fresher/entry-level relevance,
 * and writes the consolidated results to output/fresher_jobs.csv and
 * output/fresher_jobs.json.
 *
 * Usage:
 *   node src/scraper.js
 *   HEADLESS=false node src/scraper.js        # watch the browser work
 *   CONCURRENCY=5 node src/scraper.js         # tune parallel pages
 */

const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const pLimit = require("p-limit");
const { createObjectCsvWriter } = require("csv-writer");

const { loadCompanies } = require("./loadCompanies");
const { isFresherRelevant } = require("./keywords");
const logger = require("./logger");

const HEADLESS = process.env.HEADLESS !== "false";
const CONCURRENCY = parseInt(process.env.CONCURRENCY || "4", 10);
const NAV_TIMEOUT_MS = parseInt(process.env.NAV_TIMEOUT_MS || "25000", 10);
const MAX_RETRIES = parseInt(process.env.MAX_RETRIES || "2", 10);

// Selectors tried in order — career pages vary widely, so we cast a wide net
// and fall back to scanning the whole page body if nothing more specific matches.
const CANDIDATE_LISTING_SELECTORS = [
  "[class*='job-card']",
  "[class*='job-listing']",
  "[class*='job-tile']",
  "[class*='jobCard']",
  "[data-testid*='job']",
  "li[class*='job']",
  "div[class*='career'] li",
  "article",
  "tr",
];

async function extractListingTexts(page) {
  for (const selector of CANDIDATE_LISTING_SELECTORS) {
    try {
      const elements = await page.$$(selector);
      if (elements.length >= 1 && elements.length < 500) {
        const texts = [];
        for (const el of elements) {
          const text = (await el.innerText().catch(() => "")).trim();
          if (text) texts.push(text);
        }
        if (texts.length > 0) return texts;
      }
    } catch (_) {
      // try next selector
    }
  }
  // Fallback: whole-page text, split into rough chunks (paragraphs/lines)
  const bodyText = await page.evaluate(() => document.body.innerText || "");
  return bodyText
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 20);
}

async function scrapeCompany(browser, company) {
  const { companyName, careerUrl, sector } = company;
  const context = await browser.newContext({
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
  });
  const page = await context.newPage();
  page.setDefaultTimeout(NAV_TIMEOUT_MS);

  const result = {
    companyName,
    careerUrl,
    sector,
    status: "pending",
    listingsScanned: 0,
    fresherMatches: [],
    error: null,
  };

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      await page.goto(careerUrl, { waitUntil: "domcontentloaded", timeout: NAV_TIMEOUT_MS });
      // Give client-side rendered job boards a moment to populate
      await page.waitForTimeout(1500);

      const texts = await extractListingTexts(page);
      result.listingsScanned = texts.length;

      const matches = texts.filter((t) => isFresherRelevant(t));
      result.fresherMatches = matches.slice(0, 25).map((m) => m.slice(0, 300));
      result.status = "success";
      logger.info(
        `[OK] ${companyName}: scanned ${texts.length} elements, ${matches.length} fresher-relevant`
      );
      break;
    } catch (err) {
      logger.warn(`[Attempt ${attempt}/${MAX_RETRIES}] ${companyName} failed: ${err.message}`);
      result.error = err.message;
      result.status = "failed";
      if (attempt < MAX_RETRIES) await page.waitForTimeout(1000 * attempt);
    }
  }

  await context.close();
  return result;
}

async function run() {
  const companies = loadCompanies();
  logger.info(`Loaded ${companies.length} companies from config/companies.csv`);

  const browser = await chromium.launch({ headless: HEADLESS });
  const limit = pLimit(CONCURRENCY);

  const results = await Promise.all(
    companies.map((company) => limit(() => scrapeCompany(browser, company)))
  );

  await browser.close();

  const outDir = path.join(__dirname, "..", "output");
  fs.mkdirSync(outDir, { recursive: true });

  // JSON: full detail including matched listing snippets
  fs.writeFileSync(
    path.join(outDir, "fresher_jobs.json"),
    JSON.stringify(results, null, 2),
    "utf-8"
  );

  // CSV: one row per fresher-relevant listing found (flattened)
  const rows = [];
  for (const r of results) {
    if (r.status !== "success") continue;
    for (const match of r.fresherMatches) {
      rows.push({
        company: r.companyName,
        sector: r.sector,
        career_url: r.careerUrl,
        listing_snippet: match.replace(/\s+/g, " ").trim(),
      });
    }
  }

  const csvWriter = createObjectCsvWriter({
    path: path.join(outDir, "fresher_jobs.csv"),
    header: [
      { id: "company", title: "Company" },
      { id: "sector", title: "Sector" },
      { id: "career_url", title: "Career URL" },
      { id: "listing_snippet", title: "Listing Snippet" },
    ],
  });
  await csvWriter.writeRecords(rows);

  const summary = {
    companiesProcessed: results.length,
    successful: results.filter((r) => r.status === "success").length,
    failed: results.filter((r) => r.status === "failed").length,
    totalFresherListingsFound: rows.length,
  };
  fs.writeFileSync(
    path.join(outDir, "summary.json"),
    JSON.stringify(summary, null, 2),
    "utf-8"
  );

  logger.info("=== SCRAPE COMPLETE ===");
  logger.info(JSON.stringify(summary, null, 2));
  logger.info(`Results: ${path.join(outDir, "fresher_jobs.csv")}`);
}

run().catch((err) => {
  logger.error(`Fatal error: ${err.stack || err.message}`);
  process.exit(1);
});
