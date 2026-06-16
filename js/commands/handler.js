/**
 * Terminal Command Handler
 * Routes commands to appropriate handlers and manages chart state
 * Uses trie for command validation and autocomplete
 */

import { createCommandTrie } from "../utils/trie.js";
import { parseRange, isValidRange, DEFAULT_RANGE } from "../utils/timeRange.js";
import { showDue, destroyChart as destroyDueChart } from "./due.js";
import { showReviews, destroyCharts } from "./reviews.js";
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
 * @returns {{valid: boolean, error?: string, suggestions?: string[], isPartial?: boolean}}
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
    legend.textContent = "";
    legend.style.display = "none";
  }

  currentChart = null;
}

function updateChartState(
  chartType,
  isTime,
  isDeck,
  isCumulative,
  appendLine,
  rangeOverride,
) {
  clearCurrentChart();
  const range = rangeOverride || activeTimeRange;

  if (chartType === "reviews") {
    const message = showReviews(range, isTime, isDeck, isCumulative);
    appendLine(message, "success");

    let newChart = "reviews";
    if (isTime) newChart += "-time";
    if (isDeck) newChart += "-deck";
    if (isCumulative) newChart += "-cumulative";

    currentChart = newChart;
    activeTimeRange = range;
    return { handled: true, command: newChart, range };
  } else if (chartType === "due") {
    const message = showDue(range, isDeck);
    appendLine(message, "success");
    currentChart = isDeck ? "due-deck" : "due";
    activeTimeRange = range;
    return { handled: true, command: currentChart, range };
  } else if (chartType === "retention") {
    const message = showRetention(range);
    appendLine(message, "success");
    currentChart = "retention";
    activeTimeRange = range;
    return { handled: true, command: "retention", range };
  }
}

function handleTimeRangeShortcut(normalized, appendLine) {
  // Auto-unzoom if zoomed
  if (getZoomState()) {
    toggleZoom();
  }
  // Apply shortcut to current chart (don't switch)
  activeTimeRange = normalized;

  if (currentChart && currentChart.startsWith("reviews")) {
    const isCumulative = currentChart.endsWith("-cumulative");
    const isTime = currentChart.includes("time");
    const isDeck = currentChart.includes("deck");
    return updateChartState(
      "reviews",
      isTime,
      isDeck,
      isCumulative,
      appendLine,
      normalized,
    );
  } else if (currentChart === "retention") {
    return updateChartState(
      "retention",
      false,
      false,
      false,
      appendLine,
      normalized,
    );
  } else if (currentChart === "due-deck") {
    return updateChartState("due", false, true, false, appendLine, normalized);
  } else {
    // Default to due chart
    return updateChartState("due", false, false, false, appendLine, normalized);
  }
}

function handleAbbreviations(normalized, appendLine) {
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

  // Plot shortcuts mapping
  const plotShortcuts = {
    pd: { chart: "due", deck: false },
    pr: { chart: "reviews", time: false, deck: false, cum: false },
    prd: { chart: "reviews", time: false, deck: true, cum: false },
    prt: { chart: "reviews", time: true, deck: false, cum: false },
    prtd: { chart: "reviews", time: true, deck: true, cum: false },
    prc: { chart: "reviews", time: false, deck: false, cum: true },
    prdc: { chart: "reviews", time: false, deck: true, cum: true },
    prtc: { chart: "reviews", time: true, deck: false, cum: true },
    prtdc: { chart: "reviews", time: true, deck: true, cum: true },
    prdtc: { chart: "reviews", time: true, deck: true, cum: true },
  };

  if (plotShortcuts[normalized]) {
    const s = plotShortcuts[normalized];
    if (s.chart === "due") {
      return updateChartState("due", false, s.deck, false, appendLine);
    } else {
      let cmd = "plot-reviews";
      if (s.time) cmd += "-time";
      if (s.deck) cmd += "-deck";
      if (s.cum) cmd += "-cumulative";
      const res = updateChartState(
        "reviews",
        s.time,
        s.deck,
        s.cum,
        appendLine,
      );
      res.command = cmd; // override command name for tests
      return res;
    }
  }

  // Switch shortcuts
  const switchShortcuts = {
    d: { chart: "due", deck: false },
    dd: { chart: "due", deck: true },
    r: { chart: "reviews", time: false, deck: false, cum: false },
    rd: { chart: "reviews", time: false, deck: true, cum: false },
    rc: { chart: "reviews", time: false, deck: false, cum: true },
    rdc: { chart: "reviews", time: false, deck: true, cum: true },
    rtc: { chart: "reviews", time: true, deck: false, cum: true },
    rtdc: { chart: "reviews", time: true, deck: true, cum: true },
    rdtc: { chart: "reviews", time: true, deck: true, cum: true },
    rtd: { chart: "reviews", time: true, deck: true, cum: false },
  };

  if (switchShortcuts[normalized]) {
    const s = switchShortcuts[normalized];
    if (s.chart === "due") {
      return updateChartState("due", false, s.deck, false, appendLine);
    } else {
      return updateChartState("reviews", s.time, s.deck, s.cum, appendLine);
    }
  }

  // Toggles
  if (normalized === "c" || normalized === "cumulative") {
    if (currentChart && currentChart.startsWith("reviews")) {
      const isCumulative = !currentChart.endsWith("-cumulative");
      const isTime = currentChart.includes("time");
      const isDeck = currentChart.includes("deck");
      return updateChartState(
        "reviews",
        isTime,
        isDeck,
        isCumulative,
        appendLine,
      );
    } else {
      return updateChartState("reviews", false, false, true, appendLine);
    }
  }

  if (normalized === "rt" || normalized === "t" || normalized === "time") {
    if (currentChart && currentChart.startsWith("reviews")) {
      const isCumulative = currentChart.endsWith("-cumulative");
      const isTime = !currentChart.includes("time");
      const isDeck = currentChart.includes("deck");
      return updateChartState(
        "reviews",
        isTime,
        isDeck,
        isCumulative,
        appendLine,
      );
    } else {
      return updateChartState("reviews", true, false, false, appendLine);
    }
  }

  if (normalized === "deck" || normalized === "dk") {
    if (currentChart && currentChart.startsWith("reviews")) {
      const isCumulative = currentChart.endsWith("-cumulative");
      const isTime = currentChart.includes("time");
      const isDeck = !currentChart.includes("deck");
      return updateChartState(
        "reviews",
        isTime,
        isDeck,
        isCumulative,
        appendLine,
      );
    } else if (currentChart === "due") {
      return updateChartState("due", false, true, false, appendLine);
    } else if (currentChart === "due-deck") {
      return updateChartState("due", false, false, false, appendLine);
    } else {
      return updateChartState("reviews", false, true, false, appendLine);
    }
  }

  return null;
}

function handlePlotCommand(normalized, activeTimeRange, appendLine) {
  const plotMatch = normalized.match(
    /^plot\s+(due\s+deck|due|reviews\s+time\s+deck\s+cumulative|reviews\s+deck\s+time\s+cumulative|reviews\s+deck\s+cumulative|reviews\s+time\s+cumulative|reviews\s+cumulative|reviews\s+time\s+deck|reviews\s+deck\s+time|reviews\s+deck|reviews\s+time|reviews|retention)\s*(.*)$/,
  );
  if (plotMatch) {
    let [, chartType, rangeStr] = plotMatch;
    // Normalize chartType spaces to single space for easier comparison
    chartType = chartType.replace(/\s+/g, " ");
    const range = rangeStr.trim() || activeTimeRange;

    if (range && !isValidRange(range)) {
      appendLine(`Unknown range: ${range}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "plot", error: "invalid range" };
    }

    if (chartType === "due") {
      const res = updateChartState(
        "due",
        false,
        false,
        false,
        appendLine,
        range,
      );
      res.command = "plot-due";
      return res;
    } else if (chartType === "due deck") {
      const res = updateChartState(
        "due",
        false,
        true,
        false,
        appendLine,
        range,
      );
      res.command = "plot-due-deck";
      return res;
    } else if (chartType === "reviews time") {
      const res = updateChartState(
        "reviews",
        true,
        false,
        false,
        appendLine,
        range,
      );
      res.command = "plot-reviews-time";
      return res;
    } else if (chartType === "reviews") {
      const res = updateChartState(
        "reviews",
        false,
        false,
        false,
        appendLine,
        range,
      );
      res.command = "plot-reviews";
      return res;
    } else if (
      chartType === "reviews time deck" ||
      chartType === "reviews deck time"
    ) {
      const res = updateChartState(
        "reviews",
        true,
        true,
        false,
        appendLine,
        range,
      );
      res.command = "plot-reviews-time-deck";
      return res;
    } else if (chartType === "reviews deck") {
      const res = updateChartState(
        "reviews",
        false,
        true,
        false,
        appendLine,
        range,
      );
      res.command = "plot-reviews-deck";
      return res;
    } else if (chartType === "reviews time cumulative") {
      const res = updateChartState(
        "reviews",
        true,
        false,
        true,
        appendLine,
        range,
      );
      res.command = "plot-reviews-time-cumulative";
      return res;
    } else if (chartType === "reviews cumulative") {
      const res = updateChartState(
        "reviews",
        false,
        false,
        true,
        appendLine,
        range,
      );
      res.command = "plot-reviews-cumulative";
      return res;
    } else if (
      chartType === "reviews time deck cumulative" ||
      chartType === "reviews deck time cumulative"
    ) {
      const res = updateChartState(
        "reviews",
        true,
        true,
        true,
        appendLine,
        range,
      );
      res.command = "plot-reviews-time-deck-cumulative";
      return res;
    } else if (chartType === "reviews deck cumulative") {
      const res = updateChartState(
        "reviews",
        false,
        true,
        true,
        appendLine,
        range,
      );
      res.command = "plot-reviews-deck-cumulative";
      return res;
    } else {
      const res = updateChartState(
        "retention",
        false,
        false,
        false,
        appendLine,
        range,
      );
      res.command = "plot-retention";
      return res;
    }
  }
  return null;
}

function handleRegexCommands(normalized, activeTimeRange, appendLine) {
  // due deck [range]
  const dueDeckMatch = normalized.match(/^due\s+deck(?:\s+(.+))?$/);
  if (dueDeckMatch) {
    const range = dueDeckMatch[1] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("due", false, true, false, appendLine, range);
    } else if (dueDeckMatch[1]) {
      appendLine(`Unknown range: ${dueDeckMatch[1]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "due-deck", error: "invalid range" };
    }
  }

  // due [range]
  const dueMatch = normalized.match(/^(due|future)(?:\s+(.+))?$/);
  if (dueMatch && !normalized.includes("deck")) {
    const range = dueMatch[2] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("due", false, false, false, appendLine, range);
    } else if (dueMatch[2]) {
      appendLine(`Unknown range: ${dueMatch[2]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "due", error: "invalid range" };
    }
  }

  // reviews time deck cumulative [range]
  const rtdcMatch = normalized.match(
    /^reviews\s+(time\s+deck|deck\s+time)\s+cumulative(?:\s+(.+))?$/,
  );
  if (rtdcMatch) {
    const range = rtdcMatch[2] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("reviews", true, true, true, appendLine, range);
    } else if (rtdcMatch[2]) {
      appendLine(`Unknown range: ${rtdcMatch[2]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-time-deck-cumulative",
        error: "invalid range",
      };
    }
  }

  // reviews time cumulative [range]
  const rtcMatch = normalized.match(
    /^reviews\s+time\s+cumulative(?:\s+(.+))?$/,
  );
  if (rtcMatch && !normalized.includes("deck")) {
    const range = rtcMatch[1] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("reviews", true, false, true, appendLine, range);
    } else if (rtcMatch[1]) {
      appendLine(`Unknown range: ${rtcMatch[1]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-time-cumulative",
        error: "invalid range",
      };
    }
  }

  // reviews deck cumulative [range]
  const rdcMatch = normalized.match(
    /^reviews\s+deck\s+cumulative(?:\s+(.+))?$/,
  );
  if (rdcMatch && !normalized.includes("time")) {
    const range = rdcMatch[1] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("reviews", false, true, true, appendLine, range);
    } else if (rdcMatch[1]) {
      appendLine(`Unknown range: ${rdcMatch[1]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-deck-cumulative",
        error: "invalid range",
      };
    }
  }

  // reviews cumulative [range]
  const rcMatch = normalized.match(/^reviews\s+cumulative(?:\s+(.+))?$/);
  if (rcMatch && !normalized.includes("time") && !normalized.includes("deck")) {
    const range = rcMatch[1] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("reviews", false, false, true, appendLine, range);
    } else if (rcMatch[1]) {
      appendLine(`Unknown range: ${rcMatch[1]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-cumulative",
        error: "invalid range",
      };
    }
  }

  // reviews time deck [range]
  const rtdMatch = normalized.match(
    /^reviews\s+(time\s+deck|deck\s+time)(?:\s+(.+))?$/,
  );
  if (rtdMatch && !normalized.includes("cumulative")) {
    const range = rtdMatch[2] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("reviews", true, true, false, appendLine, range);
    } else if (rtdMatch[2]) {
      appendLine(`Unknown range: ${rtdMatch[2]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return {
        handled: true,
        command: "reviews-time-deck",
        error: "invalid range",
      };
    }
  }

  // reviews time [range]
  const rtMatch = normalized.match(/^reviews\s+time(?:\s+(.+))?$/);
  if (
    rtMatch &&
    !normalized.includes("deck") &&
    !normalized.includes("cumulative")
  ) {
    const range = rtMatch[1] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("reviews", true, false, false, appendLine, range);
    } else if (rtMatch[1]) {
      appendLine(`Unknown range: ${rtMatch[1]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "reviews-time", error: "invalid range" };
    }
  }

  // reviews deck [range]
  const rdMatch = normalized.match(/^reviews\s+deck(?:\s+(.+))?$/);
  if (
    rdMatch &&
    !normalized.includes("time") &&
    !normalized.includes("cumulative")
  ) {
    const range = rdMatch[1] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState("reviews", false, true, false, appendLine, range);
    } else if (rdMatch[1]) {
      appendLine(`Unknown range: ${rdMatch[1]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "reviews-deck", error: "invalid range" };
    }
  }

  // reviews [range]
  const rMatch = normalized.match(/^reviews(?:\s+(.+))?$/);
  if (
    rMatch &&
    !normalized.includes("time") &&
    !normalized.includes("deck") &&
    !normalized.includes("cumulative") &&
    !normalized.startsWith("show")
  ) {
    const range = rMatch[1] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState(
        "reviews",
        false,
        false,
        false,
        appendLine,
        range,
      );
    } else if (rMatch[1]) {
      appendLine(`Unknown range: ${rMatch[1]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "reviews", error: "invalid range" };
    }
  }

  // retention [range]
  const retMatch = normalized.match(/^retention(?:\s+(.+))?$/);
  if (retMatch && !normalized.startsWith("show")) {
    const range = retMatch[1] || activeTimeRange;
    if (isValidRange(range)) {
      return updateChartState(
        "retention",
        false,
        false,
        false,
        appendLine,
        range,
      );
    } else if (retMatch[1]) {
      appendLine(`Unknown range: ${retMatch[1]}`, "warn");
      appendLine("Valid ranges: 1m-12m, 1y-Ny, all", "muted");
      return { handled: true, command: "retention", error: "invalid range" };
    }
  }

  // show due [range] / show reviews [range]
  if (normalized.startsWith("show ")) {
    const parts = normalized.split(/\s+/);
    if (parts[1] === "due" || parts[1] === "future") {
      const range = parts[2] || activeTimeRange;
      if (isValidRange(range)) {
        return updateChartState("due", false, false, false, appendLine, range);
      }
    } else if (parts[1] === "reviews") {
      const range = parts[2] || activeTimeRange;
      if (isValidRange(range)) {
        return updateChartState(
          "reviews",
          false,
          false,
          false,
          appendLine,
          range,
        );
      }
    }
    appendLine(`Unknown chart: ${parts[1]}`, "warn");
    return { handled: true, command: "show", error: "unknown chart" };
  }

  return null;
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
    /^show\s+(due|future|reviews|.*)\s*(.*)$/,
  ];
  const isDynamic = dynamicPatterns.some((re) => {
    const match = normalized.match(re);
    // Let dynamic pattern pass even if invalid range so we can handle invalid range error msg
    // The previous check was requiring a VALID range. We just need to know if the pattern matches.
    return match !== null;
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
  if (isShortcut) {
    return handleTimeRangeShortcut(normalized, appendLine);
  }

  // Handle abbreviations (h, p, pr, d, etc.)
  const abbrRes = handleAbbreviations(normalized, appendLine);
  if (abbrRes) return abbrRes;

  // Handle plot command
  const plotRes = handlePlotCommand(normalized, activeTimeRange, appendLine);
  if (plotRes) return plotRes;

  // Handle regex/full commands
  const regexRes = handleRegexCommands(normalized, activeTimeRange, appendLine);
  if (regexRes) return regexRes;

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
