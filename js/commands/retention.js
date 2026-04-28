/**
 * Retention Chart - Retention Rate Over Time
 * Displays daily retention rates as a line chart
 */

import { bindLegendToggle, isLabelHidden } from "#js/commands/legendToggle.js";
import { getReviewStatsData } from "#js/commands/reviews.js";
import { parseRange, DEFAULT_RANGE } from "#js/utils/timeRange.js";

const Chart = window.Chart;

let retentionChart = null;

export function destroyRetentionChart() {
  if (retentionChart) {
    retentionChart.destroy();
    retentionChart = null;
  }
}

export function renderRetentionChart(data) {
  const canvas = document.getElementById("runningAmountCanvas");
  const section = document.getElementById("runningAmountSection");
  const legend = document.getElementById("chartLegend");

  if (!canvas || !section) {
    return { success: false, error: "Canvas or section not found" };
  }

  // Update legend for retention chart
  if (legend) {
    legend.innerHTML = `
            <span data-dataset-index="0"><i class="legend-color color-retention"></i> Retention Rate</span>
        `;
    legend.style.display = "flex";
  }

  // Destroy existing chart
  destroyRetentionChart();

  if (!Array.isArray(data) || data.length === 0) {
    const empty = document.getElementById("runningAmountEmpty");
    if (empty) {
      empty.style.display = "block";
      empty.textContent = "No retention data available.";
    }
    section.classList.remove("is-hidden");
    return { success: false, error: "No data" };
  }

  // Hide empty message
  const empty = document.getElementById("runningAmountEmpty");
  if (empty) empty.style.display = "none";

  // Bolt: Replace multiple array maps with a single loop to reduce O(N) allocations and GC pressure
  const len = data.length;
  const labels = new Array(len);
  const retentions = new Array(len);
  for (let i = 0; i < len; i++) {
    const entry = data[i];
    labels[i] = entry.date;
    retentions[i] = (entry.retention * 100).toFixed(1);
  }

  const isDense = data.length > 200;
  const borderWidth = isDense ? 1 : 2;
  const pointRadius = isDense ? 0 : 2;

  const ctx = canvas.getContext("2d");
  try {
    retentionChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Retention %",
            hidden: isLabelHidden("Retention %"),
            data: retentions,
            borderColor: "rgba(240, 185, 11, 0.9)",
            backgroundColor: "rgba(240, 185, 11, 0.1)",
            hoverBackgroundColor: "rgba(240, 185, 11, 0.1)",
            hoverBorderColor: "rgba(240, 185, 11, 0.9)",
            borderWidth: borderWidth,
            pointRadius: pointRadius,
            pointHoverRadius: 4,
            tension: 0.3,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: {
              color: "#a9b4d0",
              font: { family: "JetBrains Mono, monospace", size: 9 },
              maxRotation: 45,
              minRotation: 45,
            },
            grid: { display: false },
          },
          y: {
            type: "linear",
            display: true,
            position: "left",
            min: 0,
            max: 100,
            ticks: {
              color: "#f0b90b",
              font: { family: "JetBrains Mono, monospace", size: 10 },
              callback: (value) => value + "%",
            },
            grid: { color: "rgba(255,255,255,0.1)" },
            title: {
              display: true,
              text: "Retention Rate",
              color: "#f0b90b",
              font: { family: "JetBrains Mono, monospace", size: 10 },
            },
          },
        },
        plugins: {
          legend: { display: false },
          colors: false,
          tooltip: {
            backgroundColor: "rgba(2, 6, 20, 0.9)",
            titleFont: { family: "JetBrains Mono, monospace", size: 12 },
            bodyFont: { family: "JetBrains Mono, monospace", size: 11 },
            callbacks: {
              title: (items) => {
                let title = "";
                for (let i = 0; i < items.length; i++) {
                  title += (i > 0 ? "\n" : "") + items[i].label;
                }
                return title;
              },
              label: (ctx) => `Retention: ${ctx.raw}%`,
            },
          },
        },
      },
    });
  } catch (error) {
    console.error("Failed to render retention chart:", error);
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
  if (legend && retentionChart) {
    bindLegendToggle(retentionChart, legend);
  }

  return { success: true };
}

export function showRetention(rangeKey = DEFAULT_RANGE) {
  // Check if data is loaded
  if (
    !window.reviewStatsData ||
    !Array.isArray(window.reviewStatsData.reviews)
  ) {
    return "Review stats not loaded yet. Please wait a moment and try again.";
  }

  const data = getReviewStatsData(rangeKey);
  const rangeLabel = rangeKey || DEFAULT_RANGE;
  const days = parseRange(rangeLabel);
  const rangeText = days === null ? "all time" : `${days} days`;

  const result = renderRetentionChart(data);
  if (result.success) {
    return `Rendered retention rate chart (${rangeText}).`;
  }
  return result.error;
}
