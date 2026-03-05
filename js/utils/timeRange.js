/**
 * Time Range Parser
 * Dynamically parses range strings into a number of days.
 *
 * Supports:
 *   - Simple:  "3m", "2y", "15d", "all"
 *   - Combo:   "1y4m", "3m9d", "2y6m15d"
 *   - Months 1–12, any positive year count, any positive day count
 *
 * Returns the number of days, null for "all", or undefined for invalid input.
 */

export const DEFAULT_RANGE = "1m";

// Regex that matches one or more segments: Ny, Nm, Nd (in any order, but
// the entire string must be consumed by these segments).
const RANGE_RE = /^(?:(\d+)y)?(?:(\d+)m)?(?:(\d+)d)?$/;

/**
 * Parse a range string into a number of days.
 * @param {string} rangeKey - e.g. "3m", "2y", "1y4m", "3m9d", "all"
 * @returns {number|null|undefined} days (number), null for "all", undefined if invalid
 */
export function parseRange(rangeKey) {
  if (!rangeKey || typeof rangeKey !== "string") return undefined;

  const key = rangeKey.trim().toLowerCase();

  if (key === "all") return null;
  if (!key) return undefined;

  const match = key.match(RANGE_RE);
  if (!match) return undefined;

  const years = match[1] ? parseInt(match[1], 10) : 0;
  const months = match[2] ? parseInt(match[2], 10) : 0;
  const days = match[3] ? parseInt(match[3], 10) : 0;

  // At least one segment must be present
  if (years === 0 && months === 0 && days === 0) return undefined;

  // Months must be 1–12 when used alone or in combo
  if (months > 12) return undefined;

  // Years must be positive (0y alone is invalid but 0y6m is nonsensical)
  if (match[1] && years < 1) return undefined;

  const total = years * 365 + months * 30 + days;
  return total > 0 ? total : undefined;
}

/**
 * Check if a range string is valid.
 * @param {string} rangeKey
 * @returns {boolean}
 */
export function isValidRange(rangeKey) {
  return parseRange(rangeKey) !== undefined;
}

/**
 * Format a range for display.
 * @param {string} rangeKey
 * @returns {string}
 */
export function formatRange(rangeKey) {
  const days = parseRange(rangeKey);
  if (days === null) return "all time";
  if (days === undefined) return "unknown";
  return `${days} days`;
}
