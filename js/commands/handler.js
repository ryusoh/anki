/**
 * Terminal Command Handler
 * Routes commands to appropriate handlers and manages chart state
 * Uses trie for command validation and autocomplete
 */

import { createCommandTrie } from "../utils/trie.js";
import {
  showDue,
  getDueHelp,
  TIME_RANGES as DUE_RANGES,
  DEFAULT_RANGE as DUE_DEFAULT,
  destroyChart as destroyDueChart,
} from "./due.js";
import {
  showReviews,
  getReviewsHelp,
  TIME_RANGES as REVIEWS_RANGES,
  DEFAULT_RANGE as REVIEWS_DEFAULT,
  destroyChart as destroyReviewsChart,
} from "./reviews.js";

// Create command trie for validation
const commandTrie = createCommandTrie();

// Combined time ranges (use due ranges as canonical)
export const TIME_RANGES = DUE_RANGES;
export const DEFAULT_RANGE = DUE_DEFAULT;

let currentChart = null;

/**
 * Validate command against trie
 * @param {string} command - Command to validate
 * @returns {{valid: boolean, error?: string, suggestions?: string[]}}
 */
export function validateCommand(command) {
  return commandTrie.validate(command);
}

/**
 * Get autocomplete suggestions
 * @param {string} prefix - Current input prefix
 * @param {number} limit - Max suggestions
 * @returns {string[]} - Suggestions
 */
export function getAutocomplete(prefix, limit = 5) {
  return commandTrie.autocomplete(prefix, limit);
}

/**
 * Get all registered commands
 * @returns {string[]} - All commands
 */
export function getAllCommands() {
  return commandTrie.getAllCommands();
}

export function clearCurrentChart() {
  // Destroy any existing chart instances
  destroyDueChart();
  destroyReviewsChart();

  const section = document.getElementById("runningAmountSection");
  const legend = document.getElementById("chartLegend");

  if (section) {
    section.classList.add("is-hidden");
  }

  if (legend) {
    legend.innerHTML = "";
    legend.style.display = "none";
  }

  currentChart = null;
}

export function handleCommand(input, appendLine) {
  const normalized = input.toLowerCase().trim();

  if (!normalized) {
    return { handled: false };
  }

  // Validate command against trie
  const validation = commandTrie.validate(normalized);

  // If command is not valid and not a partial match, reject it
  if (!validation.valid && !validation.isPartial) {
    appendLine(`Unknown command: ${input}`, "error");
    if (validation.suggestions && validation.suggestions.length > 0) {
      appendLine(`Did you mean: ${validation.suggestions.join(", ")}`, "muted");
    } else {
      appendLine(`Type 'help' for available commands`, "muted");
    }
    return { handled: true, command: "unknown", error: "not in trie" };
  }

  // Handle time range shortcuts - apply to current chart
  if (normalized in TIME_RANGES) {
    // Apply shortcut to current chart (don't switch)
    if (currentChart === "reviews") {
      const message = showReviews(normalized);
      appendLine(message, "success");
      return { handled: true, command: "reviews", range: normalized };
    } else {
      // Default to due chart
      const message = showDue(normalized);
      appendLine(message, "success");
      currentChart = "due";
      return { handled: true, command: "due", range: normalized };
    }
  }

  // Handle abbreviations
  if (normalized === "h" || normalized === "?") {
    showHelp(appendLine);
    return { handled: true, command: "help" };
  }
  if (normalized === "p") {
    appendLine("Usage: plot due|reviews [range]", "muted");
    appendLine("Examples: pd, pd 3m, pr, pr 1y", "muted");
    return { handled: true, command: "plot" };
  }
  if (normalized === "pd") {
    clearCurrentChart();
    const message = showDue(DEFAULT_RANGE);
    appendLine(message, "success");
    currentChart = "due";
    return { handled: true, command: "plot-due", range: DEFAULT_RANGE };
  }
  if (normalized === "pr") {
    clearCurrentChart();
    const message = showReviews(DEFAULT_RANGE);
    appendLine(message, "success");
    currentChart = "reviews";
    return { handled: true, command: "plot-reviews", range: DEFAULT_RANGE };
  }
  if (normalized === "d") {
    clearCurrentChart();
    const message = showDue(DEFAULT_RANGE);
    appendLine(message, "success");
    currentChart = "due";
    return { handled: true, command: "due", range: DEFAULT_RANGE };
  }
  if (normalized === "r") {
    clearCurrentChart();
    const message = showReviews(DEFAULT_RANGE);
    appendLine(message, "success");
    currentChart = "reviews";
    return { handled: true, command: "reviews", range: DEFAULT_RANGE };
  }

  // Handle "plot due [range]" command (new umbrella syntax)
  const plotMatch = normalized.match(/^plot\s+(due|reviews)\s*(.*)$/);
  if (plotMatch) {
    const [, chartType, rangeStr] = plotMatch;
    const range = rangeStr.trim() || DEFAULT_RANGE;

    if (range && !(range in TIME_RANGES)) {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine(
        "Valid ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all",
        "muted",
      );
      return { handled: true, command: "plot", error: "invalid range" };
    }

    clearCurrentChart();
    if (chartType === "due") {
      const message = showDue(range);
      appendLine(message, "success");
      currentChart = "due";
      return { handled: true, command: "plot-due", range };
    } else {
      const message = showReviews(range);
      appendLine(message, "success");
      currentChart = "reviews";
      return { handled: true, command: "plot-reviews", range };
    }
  }

  // Handle "due" command
  if (normalized === "due" || normalized === "future") {
    clearCurrentChart();
    const message = showDue(DEFAULT_RANGE);
    appendLine(message, "success");
    currentChart = "due";
    return { handled: true, command: "due", range: DEFAULT_RANGE };
  }

  // Handle "reviews" command
  if (normalized === "reviews") {
    clearCurrentChart();
    const message = showReviews(DEFAULT_RANGE);
    appendLine(message, "success");
    currentChart = "reviews";
    return { handled: true, command: "reviews", range: DEFAULT_RANGE };
  }

  // Handle "due [range]" command
  const dueMatch = normalized.match(/^(due|future)\s+(.+)$/);
  if (dueMatch) {
    const [, range] = dueMatch;
    if (range in TIME_RANGES) {
      clearCurrentChart();
      const message = showDue(range);
      appendLine(message, "success");
      currentChart = "due";
      return { handled: true, command: "due", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine(
        "Valid ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all",
        "muted",
      );
      return { handled: true, command: "due", error: "invalid range" };
    }
  }

  // Handle "reviews [range]" command
  const reviewsMatch = normalized.match(/^reviews\s+(.+)$/);
  if (reviewsMatch) {
    const [, range] = reviewsMatch;
    if (range in TIME_RANGES) {
      clearCurrentChart();
      const message = showReviews(range);
      appendLine(message, "success");
      currentChart = "reviews";
      return { handled: true, command: "reviews", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine(
        "Valid ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all",
        "muted",
      );
      return { handled: true, command: "reviews", error: "invalid range" };
    }
  }

  // Handle "show due [range]" command
  if (normalized.startsWith("show ")) {
    const parts = normalized.split(/\s+/);
    if (parts[1] === "due" || parts[1] === "future") {
      const range = parts[2] || DEFAULT_RANGE;
      if (range in TIME_RANGES) {
        clearCurrentChart();
        const message = showDue(range);
        appendLine(message, "success");
        currentChart = "due";
        return { handled: true, command: "due", range };
      }
    } else if (parts[1] === "reviews") {
      const range = parts[2] || DEFAULT_RANGE;
      if (range in TIME_RANGES) {
        clearCurrentChart();
        const message = showReviews(range);
        appendLine(message, "success");
        currentChart = "reviews";
        return { handled: true, command: "reviews", range };
      }
    }
    appendLine(`Unknown chart: ${parts[1]}`, "warn");
    return { handled: true, command: "show", error: "unknown chart" };
  }

  return { handled: false };
}

export function showHelp(appendLine) {
  appendLine("Available commands:", "muted");
  appendLine(" - help: show this message", "muted");
  appendLine(" - charts: list available charts", "muted");
  appendLine(" - plot due [range]: render upcoming reviews chart", "muted");
  appendLine(" - plot reviews [range]: render review history chart", "muted");
  appendLine(" - clear: clear terminal output", "muted");
  appendLine("", "muted");
  appendLine("Time ranges:", "muted");
  appendLine("  1m, 2m, 3m, 6m (months)", "muted");
  appendLine("  1y, 2y, 3y, 5y, 10y (years)", "muted");
  appendLine("  all (full history)", "muted");
  appendLine("", "muted");
  appendLine("Examples:", "muted");
  appendLine("  plot due          - Default: 1 month", "muted");
  appendLine("  plot due 3m       - 3 months", "muted");
  appendLine("  plot reviews 1y   - 1 year", "muted");
  appendLine("", "muted");
  appendLine("Shortcuts (no 'plot' needed):", "muted");
  appendLine("  due, reviews     - Show default charts", "muted");
  appendLine("  1m, 3m, 1y, all  - Quick ranges for current chart", "muted");
}

export function listCharts(appendLine) {
  appendLine("Charts available:", "muted");
  appendLine(" - plot due [range]: stacked mature vs. young cards", "muted");
  appendLine(" - plot reviews [range]: review count + retention rate", "muted");
  appendLine("", "muted");
  appendLine("Time ranges:", "muted");
  appendLine("  1m, 2m, 3m, 6m | 1y, 2y, 3y, 5y, 10y | all", "muted");
  appendLine("", "muted");
  appendLine("Examples:", "muted");
  appendLine("  plot due            - Next 30 days (default)", "muted");
  appendLine("  plot due 3m         - Next 3 months", "muted");
  appendLine("  plot reviews        - Last 30 days (default)", "muted");
  appendLine("  plot reviews 6m     - Last 6 months", "muted");
  appendLine("", "muted");
  appendLine("Shortcuts:", "muted");
  appendLine("  due, reviews        - Quick chart access", "muted");
  appendLine("  2m, 1y, all         - Ranges for current chart", "muted");
}

export function getCurrentChart() {
  return currentChart;
}
