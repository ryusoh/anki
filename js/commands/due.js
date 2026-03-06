/**
 * Due Chart - Future Review Forecast
 * Displays upcoming reviews split by mature/young cards
 */

import { bindLegendToggle } from "@js/commands/legendToggle.js";
import { parseRange, DEFAULT_RANGE } from "@js/utils/timeRange.js";

const Chart = window.Chart;

let futureChart = null;

export function destroyChart() {
  if (futureChart) {
    futureChart.destroy();
    futureChart = null;
  }
}

export function getFutureDueData(rangeKey = DEFAULT_RANGE) {
  const payload = window.customStatsData || {};
  const allData = Array.isArray(payload.futureDue) ? payload.futureDue : [];

  const days = parseRange(rangeKey);
  if (days === null || days === undefined) {
    return allData;
  }

  return allData.slice(0, days);
}

export function renderFutureDueChart(data) {
  const canvas = document.getElementById("runningAmountCanvas");
  const section = document.getElementById("runningAmountSection");
  const legend = document.getElementById("chartLegend");

  if (!canvas || !section) {
    return { success: false, error: "Canvas or section not found" };
  }

  // Update legend for due chart
  if (legend) {
    legend.innerHTML = `
            <span data-dataset-index="0"><i class="legend-color color-mature"></i> Mature</span>
            <span data-dataset-index="1"><i class="legend-color color-young"></i> Young</span>
        `;
    legend.style.display = "flex";
  }

  // Destroy existing chart
  if (futureChart) {
    futureChart.destroy();
    futureChart = null;
  }

  if (
    !Array.isArray(data) ||
    !data.some((d) => (d.mature || 0) + (d.young || 0) > 0)
  ) {
    const empty = document.getElementById("runningAmountEmpty");
    if (empty) {
      empty.style.display = "block";
      empty.textContent = "No data yet. Complete some reviews first.";
    }
    section.classList.remove("is-hidden");
    return { success: false, error: "No data" };
  }

  // Hide empty message
  const empty = document.getElementById("runningAmountEmpty");
  if (empty) empty.style.display = "none";

  const labels = data.map((entry, i) => {
    if (i === 0) return "Today";
    if (i === 1) return "Tomorrow";
    return `+${entry.day}d`;
  });

  const matureDataset = data.map((entry) => entry.mature || 0);
  const youngDataset = data.map((entry) => entry.young || 0);

  const isDense = data.length > 100;
  const radius = isDense ? 0 : 4;

  const ctx = canvas.getContext("2d");
  try {
    futureChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Mature",
            data: matureDataset,
            backgroundColor: "rgba(72, 199, 142, 0.85)",
            borderRadius: radius,
            barPercentage: isDense ? 1.0 : 0.9,
            categoryPercentage: isDense ? 1.0 : 0.8,
            stack: "future",
          },
          {
            label: "Young",
            data: youngDataset,
            backgroundColor: "rgba(73, 168, 236, 0.85)",
            borderRadius: radius,
            barPercentage: isDense ? 1.0 : 0.9,
            categoryPercentage: isDense ? 1.0 : 0.8,
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
            grid: { color: "rgba(255,255,255,0.1)" },
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
  } catch (error) {
    console.error("Failed to render due chart:", error);
    const empty = document.getElementById("runningAmountEmpty");
    if (empty) {
      empty.style.display = "block";
      empty.textContent = "Chart rendering failed: " + error.message;
    }
    section.classList.remove("is-hidden");
    return { success: false, error: error.message };
  }

  section.classList.remove("is-hidden");

  // Wire click-to-toggle on bottom legend
  if (legend && futureChart) {
    bindLegendToggle(futureChart, legend);
  }

  return { success: true };
}

export function showDue(rangeKey = DEFAULT_RANGE) {
  // Check if data is loaded
  if (
    !window.customStatsData ||
    !Array.isArray(window.customStatsData.futureDue)
  ) {
    return "Stats not loaded yet. Please wait a moment and try again.";
  }

  const data = getFutureDueData(rangeKey);
  const rangeLabel = rangeKey || DEFAULT_RANGE;
  const days = parseRange(rangeLabel);
  const rangeText = days === null ? "all time" : `${days} days`;

  const result = renderFutureDueChart(data);
  if (result.success) {
    return `Rendered upcoming reviews chart (${rangeText}).`;
  }
  return result.error;
}

export function getDueHelp() {
  return [
    "due [range] - Render upcoming reviews chart",
    "",
    "Ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all",
    "",
    "Examples:",
    "  due        - Default: 1 month",
    "  due 3m     - 3 months",
    "  due all    - Full forecast",
  ];
}
