/**
 * Terminal Main Entry Point
 * Initializes terminal UI and loads command modules
 */

import { handleCommand, showHelp, listCharts, getCurrentChart, getAutocomplete, getAllCommands } from './commands/handler.js';

const PROMPT = "lz@anki:~$";
let statsReady = false;

// Focus terminal input when clicking anywhere on the terminal
document.addEventListener("DOMContentLoaded", () => {
    const terminal = document.getElementById("terminal");
    const terminalInput = document.getElementById("terminalInput");

    if (terminal && terminalInput) {
        terminal.addEventListener("click", (e) => {
            if (e.target !== terminalInput) {
                terminalInput.focus();
            }
        });
    }
});

function appendLine(text, variant = "info") {
    const terminalOutput = document.getElementById("terminalOutput");
    if (!terminalOutput) return;

    const line = document.createElement("div");
    line.className = `terminal-line variant-${variant}`;
    line.textContent = text;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function printPrompt(command) {
    appendLine(`${PROMPT} ${command}`, "prompt");
}

function clearTerminal() {
    const terminalOutput = document.getElementById("terminalOutput");
    if (terminalOutput) {
        terminalOutput.innerHTML = "";
    }
}

function handleCommandWrapper(rawInput, historyState) {
    const input = (rawInput || "").trim();
    printPrompt(input);

    if (!input) return;

    historyState.entries.push(input);
    historyState.index = historyState.entries.length;

    const normalized = input.toLowerCase();

    if (normalized === "help" || normalized === "?") {
        showHelp(appendLine);
        return;
    }

    if (normalized === "charts" || normalized === "list") {
        listCharts(appendLine);
        return;
    }

    if (normalized === "clear" || normalized === "cls") {
        clearTerminal();
        return;
    }

    // Delegate to command handler
    const result = handleCommand(input, appendLine);

    if (!result.handled) {
        appendLine(`Unknown command: ${input}`, "error");
    }
}

// Tab autocomplete state
let autocompleteState = {
    suggestions: [],
    currentIndex: 0,
    originalInput: ''
};

function setupAutocomplete(input, historyState) {
    input.addEventListener("keydown", (event) => {
        // Tab key for autocomplete
        if (event.key === "Tab") {
            event.preventDefault();
            const currentInput = input.value.trim();
            
            if (!currentInput) {
                // Show all commands if input is empty
                const allCommands = getAllCommands();
                appendLine("Available commands: " + allCommands.slice(0, 20).join(", ") + (allCommands.length > 20 ? "..." : ""), "muted");
                return;
            }
            
            // Get suggestions
            const suggestions = getAutocomplete(currentInput, 10);
            
            if (suggestions.length === 0) {
                appendLine("No matching commands", "muted");
                autocompleteState = { suggestions: [], currentIndex: 0, originalInput: '' };
                return;
            }
            
            // Cycle through suggestions
            if (autocompleteState.suggestions.length === 0 || 
                autocompleteState.originalInput !== currentInput) {
                autocompleteState = {
                    suggestions,
                    currentIndex: 0,
                    originalInput: currentInput
                };
            } else {
                autocompleteState.currentIndex = (autocompleteState.currentIndex + 1) % autocompleteState.suggestions.length;
            }
            
            // Apply suggestion
            input.value = autocompleteState.suggestions[autocompleteState.currentIndex];
            
            // Show remaining suggestions if multiple
            if (suggestions.length > 1) {
                appendLine(`Tab ${autocompleteState.currentIndex + 1}/${suggestions.length}: ${suggestions.join(" | ")}`, "muted");
            }
        }
        
        // Escape key to clear autocomplete
        if (event.key === "Escape") {
            autocompleteState = { suggestions: [], currentIndex: 0, originalInput: '' };
        }
        
        // Arrow up/down for history (existing)
        if (event.key === "ArrowUp") {
            if (!historyState.entries.length) return;
            event.preventDefault();
            historyState.index = Math.max(0, historyState.index - 1);
            input.value = historyState.entries[historyState.index] ?? "";
        } else if (event.key === "ArrowDown") {
            if (!historyState.entries.length) return;
            event.preventDefault();
            historyState.index = Math.min(historyState.entries.length, historyState.index + 1);
            input.value = historyState.entries[historyState.index] ?? "";
        } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "l") {
            event.preventDefault();
            clearTerminal();
        } else if (event.key === "Enter") {
            // Reset autocomplete on enter
            autocompleteState = { suggestions: [], currentIndex: 0, originalInput: '' };
            
            const value = input.value;
            input.value = "";
            handleCommandWrapper(value, historyState);
        }
    });
}

function attachCommandTriggers(historyState) {
    const elements = document.querySelectorAll("[data-command]");
    elements.forEach((element) => {
        element.addEventListener("click", (event) => {
            event.preventDefault();
            const command = element.getAttribute("data-command");
            const input = document.getElementById("terminalInput");
            if (!command || !input) return;
            handleCommandWrapper(command, historyState);
            input.value = "";
            input.focus();
        });
    });
}

async function fetchCustomStatsData() {
    const response = await fetch("custom_stats_data.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

async function fetchReviewStatsData() {
    const response = await fetch("review_stats_data.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

window.initCustomStats = function (data) {
    if (data) window.customStatsData = data;
    const payload = window.customStatsData;
    statsReady = !!(payload && Array.isArray(payload.futureDue));
    return statsReady;
};

async function bootstrapCustomStats() {
    if (window.initCustomStats && window.initCustomStats()) return true;
    try {
        const payload = await fetchCustomStatsData();
        if (window.initCustomStats) return window.initCustomStats(payload);
    } catch (error) {
        console.error("custom stats fetch failed", error);
    }
    return false;
}

async function bootstrapReviewStats() {
    try {
        const payload = await fetchReviewStatsData();
        if (payload && Array.isArray(payload.reviews)) {
            window.reviewStatsData = payload;
            return true;
        }
    } catch (error) {
        console.error("review stats fetch failed", error);
    }
    return false;
}

function initTerminal() {
    const terminalInput = document.getElementById("terminalInput");
    const historyState = { entries: [], index: 0 };

    if (terminalInput) {
        setupAutocomplete(terminalInput, historyState);
    }

    attachCommandTriggers(historyState);
    
    Promise.all([
        bootstrapCustomStats(),
        bootstrapReviewStats()
    ]).then(([customReady, reviewReady]) => {
        if (!customReady) {
            const empty = document.getElementById("runningAmountEmpty");
            if (empty) {
                empty.style.display = "block";
                empty.textContent = "データがありません。Anki を起動してからこのページを再読み込みしてください。";
            }
        }
    });
}

document.addEventListener("DOMContentLoaded", initTerminal);
