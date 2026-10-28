/**
 * Keyword sets used to classify a scraped job listing as relevant
 * for freshers / entry-level candidates.
 *
 * Matching is case-insensitive and works on the visible text of each
 * job card/listing element found on a career page.
 */

// Positive signals -> listing is likely open to freshers
const FRESHER_KEYWORDS = [
  "fresher",
  "freshers",
  "entry level",
  "entry-level",
  "graduate trainee",
  "graduate program",
  "graduate programme",
  "campus hire",
  "campus placement",
  "0 - 1 year",
  "0-1 year",
  "0 to 1 year",
  "0-1 years",
  "0 to 2 years",
  "no experience required",
  "trainee engineer",
  "management trainee",
  "associate trainee",
  "intern",
  "internship",
  "early career",
  "early talent",
  "new grad",
  "recent graduate",
  "0 years experience",
];

// Negative signals -> listing explicitly requires substantial experience
// (used to filter out false positives, e.g. "5+ years" pages that also
// happen to contain the word "graduate" in an unrelated sentence)
const SENIOR_EXCLUSION_KEYWORDS = [
  "5+ years",
  "7+ years",
  "10+ years",
  "minimum 5 years",
  "minimum 8 years",
  "senior",
  "lead",
  "principal",
  "architect",
  "director",
  "vice president",
  "vp,",
  "head of",
];

// Role/skill keywords relevant to CS/IT freshers - used for optional
// secondary filtering (e.g. only keep software/dev/data roles).
const ROLE_KEYWORDS = [
  "software engineer",
  "software developer",
  "sde",
  "sde-1",
  "sde 1",
  "developer",
  "programmer",
  "data analyst",
  "data scientist",
  "qa engineer",
  "test engineer",
  "systems engineer",
  "associate engineer",
  "it analyst",
  "support engineer",
  "web developer",
  "full stack",
  "backend developer",
  "frontend developer",
  "java developer",
  "python developer",
];

function containsAny(text, keywordList) {
  const lower = text.toLowerCase();
  return keywordList.some((kw) => lower.includes(kw.toLowerCase()));
}

/**
 * Decide whether a piece of listing text looks like a fresher-relevant opening.
 * @param {string} text - visible text of a job card / listing row
 * @param {object} [opts]
 * @param {boolean} [opts.requireRoleMatch=false] - also require a CS/IT role keyword
 * @returns {boolean}
 */
function isFresherRelevant(text, opts = {}) {
  const { requireRoleMatch = false } = opts;
  if (!text || text.trim().length === 0) return false;

  const hasFresherSignal = containsAny(text, FRESHER_KEYWORDS);
  const hasSeniorSignal = containsAny(text, SENIOR_EXCLUSION_KEYWORDS);

  if (!hasFresherSignal || hasSeniorSignal) return false;

  if (requireRoleMatch) {
    return containsAny(text, ROLE_KEYWORDS);
  }
  return true;
}

module.exports = {
  FRESHER_KEYWORDS,
  SENIOR_EXCLUSION_KEYWORDS,
  ROLE_KEYWORDS,
  containsAny,
  isFresherRelevant,
};
