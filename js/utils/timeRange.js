/**
 * Time Range Parser
 * Dynamically parses range strings like "3m", "12m", "1y", "13y", "all".
 *
 * Supports:
 *   - 1m through 12m (months, 1–12)
 *   - Any positive integer + y (years, e.g. 1y, 2y, 13y)
 *   - "all" (returns null, meaning no limit)
 *
 * Returns the number of days, null for "all", or undefined for invalid input.
 */

export const DEFAULT_RANGE = "1m";

/**
 * Parse a range string into a number of days.
 * @param {string} rangeKey - e.g. "3m", "2y", "all"
 * @returns {number|null|undefined} days (number), null for "all", undefined if invalid
 */
export function parseRange(rangeKey) {
    if (!rangeKey || typeof rangeKey !== "string") return undefined;

    const key = rangeKey.trim().toLowerCase();

    if (key === "all") return null;

    // Match months: 1m through 12m
    const monthMatch = key.match(/^(\d+)m$/);
    if (monthMatch) {
        const months = parseInt(monthMatch[1], 10);
        if (months >= 1 && months <= 12) {
            return months * 30;
        }
        return undefined;
    }

    // Match years: any positive integer
    const yearMatch = key.match(/^(\d+)y$/);
    if (yearMatch) {
        const years = parseInt(yearMatch[1], 10);
        if (years >= 1) {
            return years * 365;
        }
        return undefined;
    }

    return undefined;
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
