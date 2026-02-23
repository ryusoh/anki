const PROMPT = "lz@anki:~$";
let statsReady = false;
let futureChart = null;

// Time range filters (in days)
const TIME_RANGES = {
    "1m": 30,
    "2m": 60,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "2y": 730,
    "3y": 1095,
    "5y": 1825,
    "10y": 3650,
    "all": null  // No limit
};

const DEFAULT_RANGE = "1m";

// Focus terminal input when clicking anywhere on the terminal
document.addEventListener("DOMContentLoaded", () => {
    const terminal = document.getElementById("terminal");
    const terminalInput = document.getElementById("terminalInput");
    
    if (terminal && terminalInput) {
        terminal.addEventListener("click", (e) => {
            // Don't steal focus if clicking directly on the input
            if (e.target !== terminalInput) {
                terminalInput.focus();
            }
        });
    }
});

function formatDayLabel(day) {
    if (day === 0) return "今日";
    if (day === 1) return "明日";
    return `${day}日後`;
}

function setChartEmpty(message) {
    const empty = document.getElementById("runningAmountEmpty");
    if (!empty) {
        return;
    }
    empty.style.display = "block";
    empty.textContent = message;
}

function hideChartEmpty() {
    const empty = document.getElementById("runningAmountEmpty");
    if (!empty) {
        return;
    }
    empty.style.display = "none";
}

function renderFutureDueChart(data) {
    const canvas = document.getElementById("runningAmountCanvas");
    const section = document.getElementById("runningAmountSection");
    if (!canvas || !section) {
        return;
    }

    if (!Array.isArray(data) || !data.some((d) => (d.mature || 0) + (d.young || 0) > 0)) {
        setChartEmpty("まだデータがありません。復習を進めてください。");
        section.classList.remove("is-hidden");
        if (futureChart) {
            futureChart.destroy();
            futureChart = null;
        }
        return;
    }

    hideChartEmpty();
    const labels = data.map((entry) => formatDayLabel(entry.day));
    const matureDataset = data.map((entry) => entry.mature || 0);
    const youngDataset = data.map((entry) => entry.young || 0);

    const ctx = canvas.getContext("2d");
    if (futureChart) {
        futureChart.destroy();
    }

    futureChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "習熟済み",
                    data: matureDataset,
                    backgroundColor: "rgba(72, 199, 142, 0.85)",
                    borderRadius: 4,
                    stack: "future",
                },
                {
                    label: "未習熟",
                    data: youngDataset,
                    backgroundColor: "rgba(73, 168, 236, 0.85)",
                    borderRadius: 4,
                    stack: "future",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    ticks: {
                        color: "#a9b4d0",
                        font: { family: "JetBrains Mono, monospace", size: 10 },
                    },
                    grid: { display: false },
                },
                y: {
                    stacked: true,
                    ticks: {
                        color: "#a9b4d0",
                        precision: 0,
                        font: { family: "JetBrains Mono, monospace", size: 10 },
                    },
                    grid: {
                        color: "rgba(255,255,255,0.1)",
                    },
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(2, 6, 20, 0.9)",
                    titleFont: { family: "JetBrains Mono, monospace", size: 12 },
                    bodyFont: { family: "JetBrains Mono, monospace", size: 12 },
                    callbacks: {
                        title: (items) => items.map((item) => item.label).join("\n"),
                    },
                },
            },
        },
    });

    section.classList.remove("is-hidden");
}

function getFutureDueData(rangeKey = DEFAULT_RANGE) {
    const payload = window.customStatsData || {};
    const allData = Array.isArray(payload.futureDue) ? payload.futureDue : [];
    
    const days = TIME_RANGES[rangeKey];
    if (days === null || days === undefined) {
        return allData;  // "all" or invalid key returns everything
    }
    
    return allData.slice(0, Math.min(days, allData.length));
}

function showFutureDue(rangeKey = DEFAULT_RANGE) {
    if (!statsReady) {
        appendLine("Stats are still syncing. Keep Anki open and try again.", "warn");
        return;
    }
    
    const rangeLabel = rangeKey || DEFAULT_RANGE;
    const days = TIME_RANGES[rangeLabel];
    const rangeText = days === null ? "all time" : `${days} days`;
    
    const data = getFutureDueData(rangeLabel);
    if (!data.length) {
        setChartEmpty("データがありません。Anki を起動してからこのページを再読み込みしてください。");
    }
    renderFutureDueChart(data);
    appendLine(`Rendered upcoming reviews chart (${rangeText}).`, "success");
}

function appendLine(text, variant = "info") {
    const terminalOutput = document.getElementById("terminalOutput");
    if (!terminalOutput) {
        return;
    }
    const line = document.createElement("div");
    line.className = `terminal-line variant-${variant}`;
    line.textContent = text;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function printPrompt(command) {
    appendLine(`${PROMPT} ${command}`, "prompt");
}

function showHelp() {
    appendLine("Available commands:", "muted");
    appendLine(" - help: show this message", "muted");
    appendLine(" - charts: list available charts", "muted");
    appendLine(" - due [range]: render upcoming reviews chart", "muted");
    appendLine(" - clear: clear terminal output", "muted");
    appendLine("", "muted");
    appendLine("Time ranges for 'due':", "muted");
    appendLine("  1m, 2m, 3m, 6m (months)", "muted");
    appendLine("  1y, 2y, 3y, 5y, 10y (years)", "muted");
    appendLine("  all (full forecast)", "muted");
    appendLine("", "muted");
    appendLine("Examples:", "muted");
    appendLine("  due        - Default: 1 month", "muted");
    appendLine("  due 3m     - 3 months", "muted");
    appendLine("  due 1y     - 1 year", "muted");
    appendLine("  due all    - Full forecast", "muted");
}

function listCharts() {
    appendLine("Charts available:", "muted");
    appendLine(" - due [range]: stacked mature vs. young cards", "muted");
    appendLine("", "muted");
    appendLine("Time ranges:", "muted");
    appendLine("  1m, 2m, 3m, 6m | 1y, 2y, 3y, 5y, 10y | all", "muted");
    appendLine("", "muted");
    appendLine("Examples:", "muted");
    appendLine("  due        - Next 30 days (default)", "muted");
    appendLine("  due 3m     - Next 3 months", "muted");
    appendLine("  due 1y     - Next 1 year", "muted");
    appendLine("  due all    - Full forecast", "muted");
}

function clearTerminal() {
    const terminalOutput = document.getElementById("terminalOutput");
    if (terminalOutput) {
        terminalOutput.innerHTML = "";
    }
}

function handleCommand(rawInput, historyState) {
    const input = (rawInput || "").trim();
    printPrompt(input);
    if (!input) {
        return;
    }

    historyState.entries.push(input);
    historyState.index = historyState.entries.length;

    const normalized = input.toLowerCase();
    if (normalized === "help" || normalized === "?") {
        showHelp();
        return;
    }
    if (normalized === "charts" || normalized === "list") {
        listCharts();
        return;
    }
    if (normalized === "clear" || normalized === "cls") {
        clearTerminal();
        return;
    }
    
    // Handle "due" command with optional range
    if (normalized === "due" || normalized === "future" || normalized === "reviews") {
        showFutureDue(DEFAULT_RANGE);
        return;
    }
    
    // Handle "due [range]" command
    const dueMatch = normalized.match(/^(due|future|reviews)\s+(.+)$/);
    if (dueMatch) {
        const [, , range] = dueMatch;
        if (range in TIME_RANGES) {
            showFutureDue(range);
        } else {
            appendLine(`Unknown range: ${range}`, "warn");
            appendLine("Valid ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all", "muted");
        }
        return;
    }
    
    // Handle "show due [range]" command
    if (normalized.startsWith("show ")) {
        const parts = normalized.split(/\s+/);
        if (parts[1] === "due" || parts[1] === "future" || parts[1] === "reviews") {
            const range = parts[2] || DEFAULT_RANGE;
            if (range in TIME_RANGES) {
                showFutureDue(range);
            } else {
                appendLine(`Unknown range: ${range}`, "warn");
                appendLine("Valid ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all", "muted");
            }
        } else {
            appendLine(`Unknown chart: ${parts[1]}`, "warn");
        }
        return;
    }

    appendLine(`Unknown command: ${input}`, "error");
}

function setupHistoryNavigation(input, historyState) {
    input.addEventListener("keydown", (event) => {
        if (event.key === "ArrowUp") {
            if (!historyState.entries.length) {
                return;
            }
            event.preventDefault();
            historyState.index = Math.max(0, historyState.index - 1);
            input.value = historyState.entries[historyState.index] ?? "";
        } else if (event.key === "ArrowDown") {
            if (!historyState.entries.length) {
                return;
            }
            event.preventDefault();
            historyState.index = Math.min(historyState.entries.length, historyState.index + 1);
            input.value = historyState.entries[historyState.index] ?? "";
        } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "l") {
            event.preventDefault();
            clearTerminal();
        } else if (event.key === "Enter") {
            const value = input.value;
            input.value = "";
            handleCommand(value, historyState);
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
            if (!command || !input) {
                return;
            }
            handleCommand(command, historyState);
            input.value = "";
            input.focus();
        });
    });
}

async function fetchCustomStatsData() {
    const response = await fetch("custom_stats_data.json", { cache: "no-store" });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
}

window.initCustomStats = function (data) {
    if (data) {
        window.customStatsData = data;
    }
    const payload = window.customStatsData;
    statsReady = !!(payload && Array.isArray(payload.futureDue));
    return statsReady;
};

async function bootstrapCustomStats() {
    if (window.initCustomStats && window.initCustomStats()) {
        return true;
    }
    try {
        const payload = await fetchCustomStatsData();
        if (window.initCustomStats) {
            return window.initCustomStats(payload);
        }
    } catch (error) {
        console.error("custom stats fetch failed", error);
        return false;
    }
    return false;
}

function initTerminal() {
    const terminalInput = document.getElementById("terminalInput");
    const historyState = { entries: [], index: 0 };
    if (terminalInput) {
        setupHistoryNavigation(terminalInput, historyState);
    }
    attachCommandTriggers(historyState);
    bootstrapCustomStats().then((ready) => {
        if (!ready) {
            // appendLine removed per request
            setChartEmpty("データがありません。Anki を起動してからこのページを再読み込みしてください。");
        }
    });
}

document.addEventListener("DOMContentLoaded", initTerminal);
