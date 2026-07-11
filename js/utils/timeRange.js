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

export const RANGE_HELP =
  "Valid ranges: 1m-12m, 1y-Ny, Nd, combos (1y4m), YYYY, YYYYqN (2023q2), spans (2020:2023, f:2026, to:2028), all";

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
  /* c8 ignore next */
  return total > 0 ? total : undefined;
}

/**
 * Check if a range string is valid.
 * @param {string} rangeKey
 * @returns {boolean}
 */
export function isValidRange(rangeKey) {
  return parseRangeSpec(rangeKey) !== undefined;
}

/**
 * Format a range for display.
 * @param {string} rangeKey
 * @returns {string}
 */
export function formatRange(rangeKey) {
  const spec = parseRangeSpec(rangeKey);
  if (spec === undefined) return "unknown";
  if (spec.kind === "all") return "all time";
  if (spec.kind === "calendar") return spec.label;
  return `${spec.days} days`;
}

/**
 * @typedef {{ kind: "duration", days: number }
 *         | { kind: "all" }
 *         | { kind: "calendar", from: string|null, to: string|null, label: string }} RangeSpec
 */

const CALENDAR_RE = /^(\d{4})(?:q([1-4]))?$/;
const QUARTER_BOUNDS = {
  1: ["01-01", "03-31"],
  2: ["04-01", "06-30"],
  3: ["07-01", "09-30"],
  4: ["10-01", "12-31"],
};
const MIN_YEAR = 1970;
const MAX_YEAR = 2099;

/**
 * Parse one calendar unit ("2025", "2023q2") -> {from, to, label},
 * or undefined. Both bounds are always non-null for a unit.
 */
function parseCalendarUnit(token) {
  const match = token.match(CALENDAR_RE);
  if (!match) return undefined;
  const year = parseInt(match[1], 10);
  if (year < MIN_YEAR || year > MAX_YEAR) return undefined;
  if (match[2]) {
    const quarter = parseInt(match[2], 10);
    const [start, end] = QUARTER_BOUNDS[quarter];
    return {
      from: `${year}-${start}`,
      to: `${year}-${end}`,
      label: `${year} Q${quarter}`,
    };
  }
  return {
    from: `${year}-01-01`,
    to: `${year}-12-31`,
    label: `${year}`,
  };
}

/**
 * Parse a calendar token into a calendar RangeSpec.
 * Single units: "2025", "2023q2".
 * Spans:        "2020:2023", "2023q1:2024q2", "2023:2024q2".
 * Open-ended:   "f:2026" / "from:2026" (from unit start, no upper bound),
 *               "to:2028" (up to unit end, no lower bound).
 * @param {string} rangeKey
 * @returns {RangeSpec|undefined} calendar spec, or undefined if not calendar
 */
export function parseCalendarRange(rangeKey) {
  if (!rangeKey || typeof rangeKey !== "string") return undefined;
  const key = rangeKey.trim().toLowerCase();
  if (key.includes(":")) {
    const parts = key.split(":");
    if (parts.length !== 2 || !parts[0] || !parts[1]) return undefined;
    const [head, tail] = parts;
    if (head === "f" || head === "from") {
      const unit = parseCalendarUnit(tail);
      if (!unit) return undefined;
      return {
        kind: "calendar",
        from: unit.from,
        to: null,
        label: `from ${unit.label}`,
      };
    }
    if (head === "to") {
      const unit = parseCalendarUnit(tail);
      if (!unit) return undefined;
      return {
        kind: "calendar",
        from: null,
        to: unit.to,
        label: `to ${unit.label}`,
      };
    }
    const left = parseCalendarUnit(head);
    const right = parseCalendarUnit(tail);
    if (!left || !right) return undefined;
    // ISO strings compare lexicographically; reject inverted spans.
    if (left.from > right.to) return undefined;
    return {
      kind: "calendar",
      from: left.from,
      to: right.to,
      label: `${left.label} to ${right.label}`,
    };
  }
  const unit = parseCalendarUnit(key);
  if (!unit) return undefined;
  return { kind: "calendar", from: unit.from, to: unit.to, label: unit.label };
}

/**
 * Parse any range token into a RangeSpec.
 * @param {string} rangeKey
 * @returns {RangeSpec|undefined} undefined if invalid
 */
export function parseRangeSpec(rangeKey) {
  const calendar = parseCalendarRange(rangeKey);
  if (calendar) return calendar;
  const days = parseRange(rangeKey);
  if (days === null) return { kind: "all" };
  if (days === undefined) return undefined;
  return { kind: "duration", days };
}

/**
 * Map a calendar spec onto due-chart day offsets relative to `now`.
 * @param {RangeSpec} spec - must be kind "calendar"
 * @param {Date} [now] - injectable for tests
 * @returns {{start: number, end: number}|null} inclusive offsets, clamped to
 *   start >= 0; null when the whole window is in the past (end < 0)
 */
export function calendarRangeToDayOffsets(spec, now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const toLocal = (iso) => {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  };
  const diff = (target) => Math.round((target - today) / 86400000);
  const end = spec.to === null ? Infinity : diff(toLocal(spec.to));
  if (end < 0) return null;
  const start = spec.from === null ? 0 : Math.max(0, diff(toLocal(spec.from)));
  return { start, end };
}
