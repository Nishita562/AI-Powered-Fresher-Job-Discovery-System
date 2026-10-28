/**
 * validateUrls.js
 * ----------------
 * Company career-page URLs change over time (redesigns, ATS migrations,
 * subdomain changes). Run this BEFORE a full scrape to find dead/redirected
 * links so config/companies.csv can be corrected. Writes a report to
 * output/url_validation_report.csv.
 *
 * Usage: node src/validateUrls.js
 */

const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const pLimit = require("p-limit");
const { createObjectCsvWriter } = require("csv-writer");

const { loadCompanies } = require("./loadCompanies");
const logger = require("./logger");

const CONCURRENCY = parseInt(process.env.CONCURRENCY || "6", 10);
const TIMEOUT_MS = 15000;

async function checkUrl(browser, company) {
  const context = await browser.newContext();
  const page = await context.newPage();
  let status = "unknown";
  let httpStatus = null;
  let finalUrl = company.careerUrl;

  try {
    const response = await page.goto(company.careerUrl, {
      waitUntil: "domcontentloaded",
      timeout: TIMEOUT_MS,
    });
    httpStatus = response ? response.status() : null;
    finalUrl = page.url();
    status = httpStatus && httpStatus < 400 ? "OK" : "HTTP_ERROR";
  } catch (err) {
    status = "UNREACHABLE";
  }

  await context.close();
  return { ...company, status, httpStatus, finalUrl };
}

async function run() {
  const companies = loadCompanies();
  const browser = await chromium.launch({ headless: true });
  const limit = pLimit(CONCURRENCY);

  const results = await Promise.all(
    companies.map((c) => limit(() => checkUrl(browser, c)))
  );
  await browser.close();

  const outDir = path.join(__dirname, "..", "output");
  fs.mkdirSync(outDir, { recursive: true });

  const csvWriter = createObjectCsvWriter({
    path: path.join(outDir, "url_validation_report.csv"),
    header: [
      { id: "companyName", title: "Company" },
      { id: "careerUrl", title: "Configured URL" },
      { id: "finalUrl", title: "Final URL (after redirects)" },
      { id: "status", title: "Status" },
      { id: "httpStatus", title: "HTTP Status" },
    ],
  });
  await csvWriter.writeRecords(results);

  const broken = results.filter((r) => r.status !== "OK");
  logger.info(`Validated ${results.length} URLs — ${broken.length} need attention.`);
  logger.info(`Report written to output/url_validation_report.csv`);
}

run().catch((err) => {
  logger.error(`Fatal error: ${err.stack || err.message}`);
  process.exit(1);
});
