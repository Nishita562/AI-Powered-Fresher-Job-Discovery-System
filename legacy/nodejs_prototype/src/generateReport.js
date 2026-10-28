/**
 * generateReport.js
 * ------------------
 * Reads output/fresher_jobs.json (produced by scraper.js) and prints a
 * quick human-readable summary to the console: totals, per-sector
 * breakdown, and top companies by number of fresher openings found.
 *
 * Usage: node src/generateReport.js
 */

const path = require("path");
const fs = require("fs");

const OUT_DIR = path.join(__dirname, "..", "output");
const jsonPath = path.join(OUT_DIR, "fresher_jobs.json");

function main() {
  if (!fs.existsSync(jsonPath)) {
    console.error("No results found. Run `npm run scrape` first.");
    process.exit(1);
  }

  const results = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));

  const successful = results.filter((r) => r.status === "success");
  const failed = results.filter((r) => r.status !== "success");
  const totalMatches = successful.reduce((sum, r) => sum + r.fresherMatches.length, 0);

  const bySector = {};
  for (const r of successful) {
    bySector[r.sector] = bySector[r.sector] || { companies: 0, matches: 0 };
    bySector[r.sector].companies += 1;
    bySector[r.sector].matches += r.fresherMatches.length;
  }

  const topCompanies = [...successful]
    .sort((a, b) => b.fresherMatches.length - a.fresherMatches.length)
    .slice(0, 10);

  console.log("=========================================");
  console.log(" FRESHER JOB SCRAPE — SUMMARY REPORT");
  console.log("=========================================");
  console.log(`Companies processed : ${results.length}`);
  console.log(`Successful scrapes  : ${successful.length}`);
  console.log(`Failed scrapes      : ${failed.length}`);
  console.log(`Total fresher listings found : ${totalMatches}`);
  console.log("");
  console.log("-- By sector --");
  for (const [sector, stats] of Object.entries(bySector)) {
    console.log(`  ${sector}: ${stats.matches} listings across ${stats.companies} companies`);
  }
  console.log("");
  console.log("-- Top 10 companies by fresher openings found --");
  for (const c of topCompanies) {
    console.log(`  ${c.companyName}: ${c.fresherMatches.length}`);
  }
  console.log("");
  console.log(`Full data: ${jsonPath}`);
  console.log(`CSV export: ${path.join(OUT_DIR, "fresher_jobs.csv")}`);
}

main();
