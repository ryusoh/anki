/**
 * Terminal Command Handler
 * Routes commands to appropriate handlers and manages chart state
 * Uses trie for command validation and autocomplete
 */

import { createCommandTrie } from "../utils/trie.js";
import {
  parseRange,
  isValidRange,
  formatRange,
  DEFAULT_RANGE,
} from "../utils/timeRange.js";
import { showDue, getDueHelp, destroyChart as destroyDueChart } from "./due.js";
import { showReviews, getReviewsHelp, destroyCharts } from "./reviews.js";
import { showRetention, destroyRetentionChart } from "./retention.js";
import { toggleZoom, getZoomState } from "./zoom.js";

// Create command trie for validation
const commandTrie = createCommandTrie();

export { parseRange, isValidRange, DEFAULT_RANGE };

let currentChart = null;
let activeTimeRange = DEFAULT_RANGE;

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
  // Destroy any existing chart instances (due, reviews, retention)
  destroyDueChart();
  destroyCharts();
  destroyRetentionChart();

  // Auto-unzoom if zoomed
  if (getZoomState()) {
    toggleZoom();
  }

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

  // Check if it's a valid dynamic range shortcut (e.g. "1y5m")
  const isShortcut = isValidRange(normalized);

  const dynamicPatterns = [
    /^plot\s+(due|reviews\s+time\s+deck|reviews\s+deck\s+time|reviews\s+deck|reviews\s+time|reviews|retention)\s+(.+)$/,
    /^(due|future|reviews\s+time\s+deck|reviews\s+deck\s+time|reviews\s+deck|reviews\s+time|reviews|retention)\s+(.+)$/,
    /^show\s+(due|future|reviews)\s+(.+)$/,
  ];
  const isDynamic = dynamicPatterns.some((re) => {
    const match = normalized.match(re);
    return match && isValidRange(match[match.length - 1]);
  });

  // If command is not valid in trie, not a shortcut, and not dynamic, reject it
  if (!validation.valid && !validation.isPartial && !isShortcut && !isDynamic) {
    appendLine(`Unknown command: ${input}`, "error");
    if (validation.suggestions && validation.suggestions.length > 0) {
      appendLine(`Did you mean: ${validation.suggestions.join(", ")}`, "muted");
    } else {
      appendLine(`Type 'help' for available commands`, "muted");
    }
    return { handled: true, command: "unknown", error: "not in trie" };
  }

  // Handle zoom command
  if (normalized === "zoom" || normalized === "z") {
    toggleZoom().then((result) => {
      appendLine(result.message, "success");
    });
    return { handled: true, command: "zoom" };
  }

  // Handle time range shortcuts - apply to current chart
  if (isValidRange(normalized)) {
    // Auto-unzoom if zoomed
    if (getZoomState()) {
      toggleZoom();
    }
    // Apply shortcut to current chart (don't switch)
    activeTimeRange = normalized;
    if (currentChart === "reviews") {
      const message = showReviews(normalized, false, false, false);
      appendLine(message, "success");
      return { handled: true, command: "reviews", range: normalized };
    } else if (currentChart === "reviews-cumulative") {
      const message = showReviews(normalized, false, false, true);
      appendLine(message, "success");
      return {
        handled: true,
        command: "reviews-cumulative",
        range: normalized,
      };
    } else if (currentChart === "reviews-time") {
      const message = showReviews(normalized, true, false, false);
      appendLine(message, "success");
      return { handled: true, command: "reviews-time", range: normalized };
    } else if (currentChart === "reviews-time-cumulative") {
      const message = showReviews(normalized, true, false, true);
      appendLine(message, "success");
      return {
        handled: true,
        command: "reviews-time-cumulative",
        range: normalized,
      };
    } else if (currentChart === "reviews-deck") {
      const message = showReviews(normalized, false, true, false);
      appendLine(message, "success");
      return { handled: true, command: "reviews-deck", range: normalized };
    } else if (currentChart === "reviews-deck-cumulative") {
      const message = showReviews(normalized, false, true, true);
      appendLine(message, "success");
      return {
        handled: true,
        command: "reviews-deck-cumulative",
        range: normalized,
      };
    } else if (currentChart === "reviews-time-deck") {
      const message = showReviews(normalized, true, true, false);
      appendLine(message, "success");
      return { handled: true, command: "reviews-time-deck", range: normalized };
    } else if (currentChart === "reviews-time-deck-cumulative") {
      const message = showReviews(normalized, true, true, true);
      appendLine(message, "success");
      return {
        handled: true,
        command: "reviews-time-deck-cumulative",
        range: normalized,
      };
    } else if (currentChart === "retention") {
      const message = showRetention(normalized);
      appendLine(message, "success");
      return { handled: true, command: "retention", range: normalized };
    } else if (currentChart === "due-deck") {
      const message = showDue(normalized, true);
      appendLine(message, "success");
      return { handled: true, command: "due-deck", range: normalized };
    } else {
      // Default to due chart
      const message = showDue(normalized, false);
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
  if (normalized === "p" || normalized === "plot") {
    appendLine(
      "Usage: plot <due|reviews|reviews time|retention> [range]",
      "muted",
    );
    appendLine("Subcommands:", "muted");
    appendLine(
      "  plot due [range]               - Due forecast chart",
      "muted",
    );
    appendLine(
      "  plot reviews [range]           - Review history chart",
      "muted",
    );
    appendLine(
      "  plot reviews deck [range]      - Review history by deck",
      "muted",
    );
    appendLine(
      "  plot reviews time [range]      - Review time history chart",
      "muted",
    );
    appendLine(
      "  plot reviews time deck [range] - Review time history by deck",
      "muted",
    );
    appendLine(
      "  plot retention [range]         - Retention rate chart",
      "muted",
    );
    appendLine("Examples: pd, pd 3m, pr, pr 1y, prt 1y, prd 1m", "muted");
    return { handled: true, command: "plot" };
  }
  if (normalized === "pd") {
    clearCurrentChart();
    const message = showDue(activeTimeRange);
    appendLine(message, "success");
    currentChart = "due";
    return { handled: true, command: "plot-due", range: activeTimeRange };
  }
  if (normalized === "pr") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, false);
    appendLine(message, "success");
    currentChart = "reviews";
    return { handled: true, command: "plot-reviews", range: activeTimeRange };
  }
  if (normalized === "prd") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, true);
    appendLine(message, "success");
    currentChart = "reviews-deck";
    return {
      handled: true,
      command: "plot-reviews-deck",
      range: activeTimeRange,
    };
  }
  if (normalized === "prt") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, false);
    appendLine(message, "success");
    currentChart = "reviews-time";
    return {
      handled: true,
      command: "plot-reviews-time",
      range: activeTimeRange,
    };
  }
  if (normalized === "prtd") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, true);
    appendLine(message, "success");
    currentChart = "reviews-time-deck";
    return {
      handled: true,
      command: "plot-reviews-time-deck",
      range: activeTimeRange,
    };
  }
  if (normalized === "prc") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, false, true);
    appendLine(message, "success");
    currentChart = "reviews-cumulative";
    return {
      handled: true,
      command: "plot-reviews-cumulative",
      range: activeTimeRange,
    };
  }
  if (normalized === "prdc") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, true, true);
    appendLine(message, "success");
    currentChart = "reviews-deck-cumulative";
    return {
      handled: true,
      command: "plot-reviews-deck-cumulative",
      range: activeTimeRange,
    };
  }
  if (normalized === "prtc") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, false, true);
    appendLine(message, "success");
    currentChart = "reviews-time-cumulative";
    return {
      handled: true,
      command: "plot-reviews-time-cumulative",
      range: activeTimeRange,
    };
  }
  if (normalized === "prtdc" || normalized === "prdtc") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, true, true);
    appendLine(message, "success");
    currentChart = "reviews-time-deck-cumulative";
    return {
      handled: true,
      command: "plot-reviews-time-deck-cumulative",
      range: activeTimeRange,
    };
  }
  if (normalized === "d") {
    clearCurrentChart();
    const message = showDue(activeTimeRange, false);
    appendLine(message, "success");
    currentChart = "due";
    return { handled: true, command: "due", range: activeTimeRange };
  }
  if (normalized === "dd") {
    clearCurrentChart();
    const message = showDue(activeTimeRange, true);
    appendLine(message, "success");
    currentChart = "due-deck";
    return { handled: true, command: "due-deck", range: activeTimeRange };
  }
  if (normalized === "r") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, false);
    appendLine(message, "success");
    currentChart = "reviews";
    return { handled: true, command: "reviews", range: activeTimeRange };
  }
  if (normalized === "rd") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, true);
    appendLine(message, "success");
    currentChart = "reviews-deck";
    return { handled: true, command: "reviews-deck", range: activeTimeRange };
  }
  if (normalized === "rc") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, false, true);
    appendLine(message, "success");
    currentChart = "reviews-cumulative";
    return {
      handled: true,
      command: "reviews-cumulative",
      range: activeTimeRange,
    };
  }
  if (normalized === "rdc") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, true, true);
    appendLine(message, "success");
    currentChart = "reviews-deck-cumulative";
    return {
      handled: true,
      command: "reviews-deck-cumulative",
      range: activeTimeRange,
    };
  }
  if (normalized === "rtc") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, false, true);
    appendLine(message, "success");
    currentChart = "reviews-time-cumulative";
    return {
      handled: true,
      command: "reviews-time-cumulative",
      range: activeTimeRange,
    };
  }
  if (normalized === "rtdc" || normalized === "rdtc") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, true, true);
    appendLine(message, "success");
    currentChart = "reviews-time-deck-cumulative";
    return {
      handled: true,
      command: "reviews-time-deck-cumulative",
      range: activeTimeRange,
    };
  }
  if (normalized === "c" || normalized === "cumulative") {
    if (currentChart && currentChart.startsWith("reviews")) {
      const isCumulative = !currentChart.endsWith("-cumulative");
      const isTime = currentChart.includes("time");
      const isDeck = currentChart.includes("deck");
      clearCurrentChart();
      const message = showReviews(
        activeTimeRange,
        isTime,
        isDeck,
        isCumulative,
      );
      appendLine(message, "success");
      let newChart = "reviews";
      if (isTime) newChart += "-time";
      if (isDeck) newChart += "-deck";
      if (isCumulative) newChart += "-cumulative";
      currentChart = newChart;
      return { handled: true, command: newChart, range: activeTimeRange };
    } else {
      clearCurrentChart();
      const message = showReviews(activeTimeRange, false, false, true);
      appendLine(message, "success");
      currentChart = "reviews-cumulative";
      return {
        handled: true,
        command: "reviews-cumulative",
        range: activeTimeRange,
      };
    }
  }
  if (normalized === "rt" || normalized === "t" || normalized === "time") {
    if (currentChart && currentChart.startsWith("reviews")) {
      const isCumulative = currentChart.endsWith("-cumulative");
      const isTime = !currentChart.includes("time");
      const isDeck = currentChart.includes("deck");
      clearCurrentChart();
      const message = showReviews(
        activeTimeRange,
        isTime,
        isDeck,
        isCumulative,
      );
      appendLine(message, "success");
      let newChart = "reviews";
      if (isTime) newChart += "-time";
      if (isDeck) newChart += "-deck";
      if (isCumulative) newChart += "-cumulative";
      currentChart = newChart;
      return { handled: true, command: newChart, range: activeTimeRange };
    } else {
      clearCurrentChart();
      const message = showReviews(activeTimeRange, true, false, false);
      appendLine(message, "success");
      currentChart = "reviews-time";
      return { handled: true, command: "reviews-time", range: activeTimeRange };
    }
  }

  if (normalized === "deck" || normalized === "dk") {
    if (currentChart && currentChart.startsWith("reviews")) {
      const isCumulative = currentChart.endsWith("-cumulative");
      const isTime = currentChart.includes("time");
      const isDeck = !currentChart.includes("deck");
      clearCurrentChart();
      const message = showReviews(
        activeTimeRange,
        isTime,
        isDeck,
        isCumulative,
      );
      appendLine(message, "success");
      let newChart = "reviews";
      if (isTime) newChart += "-time";
      if (isDeck) newChart += "-deck";
      if (isCumulative) newChart += "-cumulative";
      currentChart = newChart;
      return { handled: true, command: newChart, range: activeTimeRange };
    } else if (currentChart === "due") {
      clearCurrentChart();
      const message = showDue(activeTimeRange, true);
      appendLine(message, "success");
      currentChart = "due-deck";
      return { handled: true, command: "due-deck", range: activeTimeRange };
    } else if (currentChart === "due-deck") {
      clearCurrentChart();
      const message = showDue(activeTimeRange, false);
      appendLine(message, "success");
      currentChart = "due";
      return { handled: true, command: "due", range: activeTimeRange };
    } else {
      clearCurrentChart();
      const message = showReviews(activeTimeRange, false, true, false);
      appendLine(message, "success");
      currentChart = "reviews-deck";
      return { handled: true, command: "reviews-deck", range: activeTimeRange };
    }
  }
  if (normalized === "rtd") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, true);
    appendLine(message, "success");
    currentChart = "reviews-time-deck";
    return {
      handled: true,
      command: "reviews-time-deck",
      range: activeTimeRange,
    };
  }

  // Handle "plot due [range]" command (new umbrella syntax)
  const plotMatch = normalized.match(
    /^plot\s+(due\s+deck|due|reviews\s+time\s+deck\s+cumulative|reviews\s+deck\s+time\s+cumulative|reviews\s+deck\s+cumulative|reviews\s+time\s+cumulative|reviews\s+cumulative|reviews\s+time\s+deck|reviews\s+deck\s+time|reviews\s+deck|reviews\s+time|reviews|retention)\s*(.*)$/,
  );
  if (plotMatch) {
    const [, chartType, rangeStr] = plotMatch;
    const range = rangeStr.trim() || activeTimeRange;

    if (range && !isValidRange(range)) {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "plot", error: "invalid range" };
    }

    clearCurrentChart();
    activeTimeRange = range;
    if (chartType === "due") {
      const message = showDue(range, false);
      appendLine(message, "success");
      currentChart = "due";
      return { handled: true, command: "plot-due", range };
    } else if (chartType === "due deck") {
      const message = showDue(range, true);
      appendLine(message, "success");
      currentChart = "due-deck";
      return { handled: true, command: "plot-due-deck", range };
    } else if (chartType === "reviews time") {
      const message = showReviews(range, true, false, false);
      appendLine(message, "success");
      currentChart = "reviews-time";
      return { handled: true, command: "plot-reviews-time", range };
    } else if (chartType === "reviews") {
      const message = showReviews(range, false, false, false);
      appendLine(message, "success");
      currentChart = "reviews";
      return { handled: true, command: "plot-reviews", range };
    } else if (
      chartType === "reviews time deck" ||
      chartType === "reviews deck time"
    ) {
      const message = showReviews(range, true, true, false);
      appendLine(message, "success");
      currentChart = "reviews-time-deck";
      return { handled: true, command: "plot-reviews-time-deck", range };
    } else if (chartType === "reviews deck") {
      const message = showReviews(range, false, true, false);
      appendLine(message, "success");
      currentChart = "reviews-deck";
      return { handled: true, command: "plot-reviews-deck", range };
    } else if (chartType === "reviews time cumulative") {
      const message = showReviews(range, true, false, true);
      appendLine(message, "success");
      currentChart = "reviews-time-cumulative";
      return { handled: true, command: "plot-reviews-time-cumulative", range };
    } else if (chartType === "reviews cumulative") {
      const message = showReviews(range, false, false, true);
      appendLine(message, "success");
      currentChart = "reviews-cumulative";
      return { handled: true, command: "plot-reviews-cumulative", range };
    } else if (
      chartType === "reviews time deck cumulative" ||
      chartType === "reviews deck time cumulative"
    ) {
      const message = showReviews(range, true, true, true);
      appendLine(message, "success");
      currentChart = "reviews-time-deck-cumulative";
      return {
        handled: true,
        command: "plot-reviews-time-deck-cumulative",
        range,
      };
    } else if (chartType === "reviews deck cumulative") {
      const message = showReviews(range, false, true, true);
      appendLine(message, "success");
      currentChart = "reviews-deck-cumulative";
      return { handled: true, command: "plot-reviews-deck-cumulative", range };
    } else {
      const message = showRetention(range);
      appendLine(message, "success");
      currentChart = "retention";
      return { handled: true, command: "plot-retention", range };
    }
  }

  // Handle "due deck" command
  if (normalized === "due deck") {
    clearCurrentChart();
    const message = showDue(activeTimeRange, true);
    appendLine(message, "success");
    currentChart = "due-deck";
    return { handled: true, command: "due-deck", range: activeTimeRange };
  }

  // Handle "due" command
  if (normalized === "due" || normalized === "future") {
    clearCurrentChart();
    const message = showDue(activeTimeRange, false);
    appendLine(message, "success");
    currentChart = "due";
    return { handled: true, command: "due", range: activeTimeRange };
  }

  // Handle "reviews time deck" or "reviews deck time" command
  if (
    normalized === "reviews time deck" ||
    normalized === "reviews deck time"
  ) {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, true);
    appendLine(message, "success");
    currentChart = "reviews-time-deck";
    return {
      handled: true,
      command: "reviews-time-deck",
      range: activeTimeRange,
    };
  }

  // Handle "reviews time" command
  if (normalized === "reviews time") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, true, false);
    appendLine(message, "success");
    currentChart = "reviews-time";
    return { handled: true, command: "reviews-time", range: activeTimeRange };
  }

  // Handle "reviews deck" command
  if (normalized === "reviews deck") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, true);
    appendLine(message, "success");
    currentChart = "reviews-deck";
    return { handled: true, command: "reviews-deck", range: activeTimeRange };
  }

  // Handle "reviews" command
  if (normalized === "reviews") {
    clearCurrentChart();
    const message = showReviews(activeTimeRange, false, false);
    appendLine(message, "success");
    currentChart = "reviews";
    return { handled: true, command: "reviews", range: activeTimeRange };
  }

  // Handle "retention" command
  if (normalized === "retention") {
    clearCurrentChart();
    const message = showRetention(activeTimeRange);
    appendLine(message, "success");
    currentChart = "retention";
    return { handled: true, command: "retention", range: activeTimeRange };
  }

  // Handle "due deck [range]" command
  const dueDeckMatch = normalized.match(/^due\s+deck\s+(.+)$/);
  if (dueDeckMatch) {
    const [, range] = dueDeckMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showDue(range, true);
      appendLine(message, "success");
      currentChart = "due-deck";
      return { handled: true, command: "due-deck", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "due-deck", error: "invalid range" };
    }
  }

  // Handle "due [range]" command
  const dueMatch = normalized.match(/^(due|future)\s+(.+)$/);
  if (dueMatch && !normalized.startsWith("due deck")) {
    const [, , range] = dueMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showDue(range, false);
      appendLine(message, "success");
      currentChart = "due";
      return { handled: true, command: "due", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "due", error: "invalid range" };
    }
  }

  // Handle "reviews time deck cumulative [range]" or "reviews deck time cumulative [range]"
  const reviewsTimeDeckCumMatch = normalized.match(
    /^reviews\s+(time\s+deck|deck\s+time)\s+cumulative\s+(.+)$/,
  );
  if (reviewsTimeDeckCumMatch) {
    const [, , range] = reviewsTimeDeckCumMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showReviews(range, true, true, true);
      appendLine(message, "success");
      currentChart = "reviews-time-deck-cumulative";
      return { handled: true, command: "reviews-time-deck-cumulative", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-time-deck-cumulative",
        error: "invalid range",
      };
    }
  }

  // Handle "reviews time cumulative [range]"
  const reviewsTimeCumMatch = normalized.match(
    /^reviews\s+time\s+cumulative\s+(.+)$/,
  );
  if (
    reviewsTimeCumMatch &&
    !normalized.startsWith("reviews time deck") &&
    !normalized.startsWith("reviews deck time")
  ) {
    const [, range] = reviewsTimeCumMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showReviews(range, true, false, true);
      appendLine(message, "success");
      currentChart = "reviews-time-cumulative";
      return { handled: true, command: "reviews-time-cumulative", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-time-cumulative",
        error: "invalid range",
      };
    }
  }

  // Handle "reviews deck cumulative [range]"
  const reviewsDeckCumMatch = normalized.match(
    /^reviews\s+deck\s+cumulative\s+(.+)$/,
  );
  if (reviewsDeckCumMatch) {
    const [, range] = reviewsDeckCumMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showReviews(range, false, true, true);
      appendLine(message, "success");
      currentChart = "reviews-deck-cumulative";
      return { handled: true, command: "reviews-deck-cumulative", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-deck-cumulative",
        error: "invalid range",
      };
    }
  }

  // Handle "reviews cumulative [range]"
  const reviewsCumMatch = normalized.match(/^reviews\s+cumulative\s+(.+)$/);
  if (
    reviewsCumMatch &&
    !normalized.startsWith("reviews time") &&
    !normalized.startsWith("reviews deck")
  ) {
    const [, range] = reviewsCumMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showReviews(range, false, false, true);
      appendLine(message, "success");
      currentChart = "reviews-cumulative";
      return { handled: true, command: "reviews-cumulative", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-cumulative",
        error: "invalid range",
      };
    }
  }

  // Handle "reviews time deck [range]" or "reviews deck time [range]" command
  const reviewsTimeDeckMatch = normalized.match(
    /^reviews\s+(time\s+deck|deck\s+time)\s+(.+)$/,
  );
  if (reviewsTimeDeckMatch && !normalized.includes("cumulative")) {
    const [, , range] = reviewsTimeDeckMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showReviews(range, true, true, false);
      appendLine(message, "success");
      currentChart = "reviews-time-deck";
      return { handled: true, command: "reviews-time-deck", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-time-deck",
        error: "invalid range",
      };
    }
  }

  // Handle "reviews time [range]" command
  const reviewsTimeMatch = normalized.match(/^reviews\s+time\s+(.+)$/);
  if (
    reviewsTimeMatch &&
    !normalized.startsWith("reviews time deck") &&
    !normalized.startsWith("reviews deck time") &&
    !normalized.includes("cumulative")
  ) {
    const [, range] = reviewsTimeMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showReviews(range, true, false, false);
      appendLine(message, "success");
      currentChart = "reviews-time";
      return { handled: true, command: "reviews-time", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "reviews-time", error: "invalid range" };
    }
  }

  // Handle "reviews deck [range]" command
  const reviewsDeckMatch = normalized.match(/^reviews\s+deck\s+(.+)$/);
  if (reviewsDeckMatch && !normalized.includes("cumulative")) {
    const [, range] = reviewsDeckMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showReviews(range, false, true, false);
      appendLine(message, "success");
      currentChart = "reviews-deck";
      return { handled: true, command: "reviews-deck", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "reviews-deck", error: "invalid range" };
    }
  }

  // Handle "reviews [range]" command
  // Avoid capturing "reviews time", "reviews deck", "reviews time deck", "reviews deck time"
  const reviewsMatch = normalized.match(/^reviews\s+(.+)$/);
  if (
    reviewsMatch &&
    !normalized.startsWith("reviews time") &&
    !normalized.startsWith("reviews deck") &&
    !normalized.includes("cumulative")
  ) {
    const [, range] = reviewsMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showReviews(range, false, false, false);
      appendLine(message, "success");
      currentChart = "reviews";
      return { handled: true, command: "reviews", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "reviews", error: "invalid range" };
    }
  }

  // Handle "retention [range]" command
  const retentionMatch = normalized.match(/^retention\s+(.+)$/);
  if (retentionMatch) {
    const [, range] = retentionMatch;
    if (isValidRange(range)) {
      clearCurrentChart();
      activeTimeRange = range;
      const message = showRetention(range);
      appendLine(message, "success");
      currentChart = "retention";
      return { handled: true, command: "retention", range };
    } else {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "retention", error: "invalid range" };
    }
  }

  // Handle "show due [range]" command
  if (normalized.startsWith("show ")) {
    const parts = normalized.split(/\s+/);
    if (parts[1] === "due" || parts[1] === "future") {
      const range = parts[2] || activeTimeRange;
      if (isValidRange(range)) {
        clearCurrentChart();
        activeTimeRange = range;
        const message = showDue(range);
        appendLine(message, "success");
        currentChart = "due";
        return { handled: true, command: "due", range };
      }
    } else if (parts[1] === "reviews") {
      const range = parts[2] || activeTimeRange;
      if (isValidRange(range)) {
        clearCurrentChart();
        activeTimeRange = range;
        const message = showReviews(range, false, false, false);
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
  appendLine(
    " - plot reviews [range]: render review history chart (append cumulative for running total)",
    "muted",
  );
  appendLine(
    " - plot reviews deck [range]: render review history chart broken down by deck",
    "muted",
  );
  appendLine(
    " - plot reviews time [range]: render review time history chart",
    "muted",
  );
  appendLine(
    " - plot reviews time deck [range]: render review time by deck chart",
    "muted",
  );
  appendLine(" - plot retention [range]: render retention rate chart", "muted");
  appendLine(" - zoom (z): toggle terminal zoom", "muted");
  appendLine(" - clear: clear terminal output", "muted");
  appendLine("", "muted");
  appendLine("Time ranges:", "muted");
  appendLine("  1m-12m, 1y+ (e.g. 13y), Nd (e.g. 15d)", "muted");
  appendLine("  Combos: 1y4m, 3m9d, 2y6m15d", "muted");
  appendLine("  all (full history)", "muted");
  appendLine("", "muted");
  appendLine("Examples:", "muted");
  appendLine("  plot due          - Default: 1 month", "muted");
  appendLine("  plot due 3m9d     - 3 months and 9 days", "muted");
  appendLine("  plot reviews 1y   - 1 year", "muted");
  appendLine("  plot retention 1y4m - 1 year and 4 months", "muted");
  appendLine("", "muted");
  appendLine("Shortcuts (no 'plot' needed):", "muted");
  appendLine(
    "  due, reviews, time, cumulative - Show or toggle chart context",
    "muted",
  );
  appendLine(
    "  1m, 1y4m, all                  - Quick ranges for current chart",
    "muted",
  );
  appendLine("  z                              - Toggle zoom", "muted");
}

export function listCharts(appendLine) {
  appendLine("Charts available:", "muted");
  appendLine(" - plot due [range]: stacked mature vs. young cards", "muted");
  appendLine(
    " - plot reviews [range]: review history stacked by status",
    "muted",
  );
  appendLine(
    " - plot reviews time [range]: review time history stacked by status",
    "muted",
  );
  appendLine(" - plot retention [range]: retention rate line chart", "muted");
  appendLine("", "muted");
  appendLine("Time ranges:", "muted");
  appendLine("  1m-12m, 1y+, Nd, combos (1y4m, 3m9d), all", "muted");
  appendLine("", "muted");
  appendLine("Examples:", "muted");
  appendLine("  plot due            - Next 30 days (default)", "muted");
  appendLine("  plot due 3m9d       - Next 3 months and 9 days", "muted");
  appendLine("  plot reviews 1y     - Last 1 year history", "muted");
  appendLine("  plot retention 1y4m - Last 1 year and 4 months", "muted");
  appendLine("", "muted");
  appendLine("Shortcuts:", "muted");
  appendLine(
    "  due, reviews, time, cumulative - Quick chart access and context modification",
    "muted",
  );
  appendLine(
    "  2m, 1y4m, all                  - Ranges for current chart",
    "muted",
  );
}

export function getCurrentChart() {
  return currentChart;
}
