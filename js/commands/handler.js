/**
 * Terminal Command Handler
 * Routes commands to appropriate handlers and manages chart state
 */

import { showDue, getDueHelp, TIME_RANGES as DUE_RANGES, DEFAULT_RANGE as DUE_DEFAULT } from './due.js';
import { showReviews, getReviewsHelp, TIME_RANGES as REVIEWS_RANGES } from './reviews.js';

// Combined time ranges (use due ranges as canonical)
export const TIME_RANGES = DUE_RANGES;
export const DEFAULT_RANGE = DUE_DEFAULT;

let currentChart = null;

export function clearCurrentChart() {
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
    
    // Handle time range shortcuts (e.g., "1m", "2y", "all")
    if (normalized in TIME_RANGES) {
        clearCurrentChart();
        const message = showDue(normalized);
        appendLine(message, "success");
        currentChart = "due";
        return { handled: true, command: "due", range: normalized };
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
            appendLine("Valid ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all", "muted");
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
            appendLine("Valid ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all", "muted");
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
    getDueHelp().forEach(line => appendLine(line, "muted"));
    getReviewsHelp().forEach(line => appendLine(line, "muted"));
    appendLine("", "muted");
    appendLine("Quick ranges (no command needed):", "muted");
    appendLine("  1m, 2m, 3m, 6m, 1y, 2y, all, etc.", "muted");
}

export function listCharts(appendLine) {
    appendLine("Charts available:", "muted");
    getDueHelp().slice(0, 1).forEach(line => appendLine(line, "muted"));
    getReviewsHelp().slice(0, 1).forEach(line => appendLine(line, "muted"));
    appendLine("", "muted");
    appendLine("Time ranges:", "muted");
    appendLine("  1m, 2m, 3m, 6m | 1y, 2y, 3y, 5y, 10y | all", "muted");
    appendLine("", "muted");
    appendLine("Examples:", "muted");
    appendLine("  due            - Next 30 days (default)", "muted");
    appendLine("  due 3m         - Next 3 months", "muted");
    appendLine("  reviews        - Last 30 days (default)", "muted");
    appendLine("  reviews 6m     - Last 6 months", "muted");
    appendLine("  2m             - Quick: 2 months (due chart)", "muted");
}

export function getCurrentChart() {
    return currentChart;
}
