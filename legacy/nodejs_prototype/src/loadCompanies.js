const fs = require("fs");
const path = require("path");
const { parse } = require("csv-parse/sync");

/**
 * Loads the company list (name, career_url, sector) from config/companies.csv.
 * The CSV is intentionally the single source of truth so the list can be
 * grown from ~100 seed entries up to 500 companies without touching code.
 */
function loadCompanies(csvPath = path.join(__dirname, "..", "config", "companies.csv")) {
  const raw = fs.readFileSync(csvPath, "utf-8");
  const records = parse(raw, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
  });

  return records
    .filter((r) => r.company_name && r.career_url)
    .map((r) => ({
      companyName: r.company_name,
      careerUrl: r.career_url,
      sector: r.sector || "Unspecified",
    }));
}

module.exports = { loadCompanies };
