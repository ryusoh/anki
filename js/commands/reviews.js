/**
 * Reviews Chart - Review History
 * Displays past review counts as a stacked bar chart
 */

import { bindLegendToggle } from "@js/commands/legendToggle.js";
import { parseRange, DEFAULT_RANGE } from "@js/utils/timeRange.js";

const Chart = window.Chart;

let reviewsChart = null;

export function destroyCharts() {
  if (reviewsChart) {
    reviewsChart.destroy();
    reviewsChart = null;
  }
}

export function getReviewStatsData(rangeKey = DEFAULT_RANGE) {
  const payload = window.reviewStatsData || {};
  const allData = Array.isArray(payload.reviews) ? payload.reviews : [];

  const days = parseRange(rangeKey);
  if (days === null || days === undefined) {
    return allData;
  }

  // Get last N days of data
  return allData.slice(-Math.min(days, allData.length));
}

export function renderReviewsChart(data, showTime = false) {
  const canvas = document.getElementById("runningAmountCanvas");
  const section = document.getElementById("runningAmountSection");
  const legend = document.getElementById("chartLegend");

  if (!canvas || !section) {
    return { success: false, error: "Canvas or section not found" };
  }

  // Update legend for reviews chart (stacked by card status)
  if (legend) {
    legend.innerHTML = `
            <span data-dataset-index="0"><i class="legend-color color-mature"></i> Mature</span>
            <span data-dataset-index="1"><i class="legend-color color-young"></i> Young</span>
            <span data-dataset-index="2"><i class="legend-color color-relearn"></i> Relearn</span>
            <span data-dataset-index="3"><i class="legend-color color-learn"></i> Learn</span>
        `;
    legend.style.display = "flex";
  }

  // Destroy existing chart
  if (reviewsChart) {
    reviewsChart.destroy();
    reviewsChart = null;
  }

  if (!Array.isArray(data) || data.length === 0) {
    const empty = document.getElementById("runningAmountEmpty");
    if (empty) {
      empty.style.display = "block";
      empty.textContent = "No review data available.";
    }
    section.classList.remove("is-hidden");
    return { success: false, error: "No data" };
  }

  // Hide empty message
  const empty = document.getElementById("runningAmountEmpty");
  if (empty) empty.style.display = "none";

  const labels = data.map((entry) => entry.date);

  let matureData, youngData, learnData, relearnData;
  if (showTime) {
    matureData = data.map((entry) => Math.round((entry.time_mature || 0) / 60));
    youngData = data.map((entry) => Math.round((entry.time_young || 0) / 60));
    learnData = data.map((entry) => Math.round((entry.time_learn || 0) / 60));
    relearnData = data.map((entry) =>
      Math.round((entry.time_relearn || 0) / 60),
    );
  } else {
    matureData = data.map((entry) => entry.mature || 0);
    youngData = data.map((entry) => entry.young || 0);
    learnData = data.map((entry) => entry.learn || 0);
    relearnData = data.map((entry) => entry.relearn || 0);
  }

  const totalTimes = data.map((entry) => Math.round(entry.time / 60)); // total minutes

  const isDense = data.length > 100;
  const radius = isDense ? 0 : 4;

  const ctx = canvas.getContext("2d");
  try {
    reviewsChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Mature",
            data: matureData,
            backgroundColor: "rgba(72, 199, 142, 0.85)",
            borderRadius: radius,
            barPercentage: isDense ? 1.0 : 0.9,
            categoryPercentage: isDense ? 1.0 : 0.8,
            stack: "reviews",
          },
          {
            label: "Young",
            data: youngData,
            backgroundColor: "rgba(73, 168, 236, 0.85)",
            borderRadius: radius,
            barPercentage: isDense ? 1.0 : 0.9,
            categoryPercentage: isDense ? 1.0 : 0.8,
            stack: "reviews",
          },
          {
            label: "Relearn",
            data: relearnData,
            backgroundColor: "rgba(234, 67, 53, 0.85)",
            borderRadius: radius,
            barPercentage: isDense ? 1.0 : 0.9,
            categoryPercentage: isDense ? 1.0 : 0.8,
            stack: "reviews",
          },
          {
            label: "Learn",
            data: learnData,
            backgroundColor: "rgba(240, 185, 11, 0.85)",
            borderRadius: radius,
            barPercentage: isDense ? 1.0 : 0.9,
            categoryPercentage: isDense ? 1.0 : 0.8,
            stack: "reviews",
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
              font: { family: "JetBrains Mono, monospace", size: 9 },
              maxRotation: 45,
              minRotation: 45,
            },
            grid: { display: false },
          },
          y: {
            stacked: true,
            type: "linear",
            display: true,
            position: "left",
            ticks: {
              color: "#a9b4d0",
              precision: 0,
              font: { family: "JetBrains Mono, monospace", size: 10 },
            },
            grid: { color: "rgba(255,255,255,0.1)" },
            title: {
              display: true,
              text: showTime ? "Time (minutes)" : "Reviews",
              color: "#a9b4d0",
              font: { family: "JetBrains Mono, monospace", size: 10 },
            },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "rgba(2, 6, 20, 0.9)",
            titleFont: { family: "JetBrains Mono, monospace", size: 12 },
            bodyFont: { family: "JetBrains Mono, monospace", size: 11 },
            callbacks: {
              title: (items) => items.map((item) => item.label).join("\n"),
              label: (ctx) => {
                if (showTime) {
                  const hours = (ctx.raw / 60).toFixed(1);
                  return `${ctx.dataset.label}: ${ctx.raw} min (${hours} h)`;
                } else {
                  const time = totalTimes[ctx.dataIndex];
                  return `${ctx.dataset.label}: ${ctx.raw} (${time} min total)`;
                }
              },
            },
          },
        },
      },
    });
  } catch (error) {
    console.error("Failed to render reviews chart:", error);
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
  if (legend && reviewsChart) {
    bindLegendToggle(reviewsChart, legend);
  }

  return { success: true };
}

export function showReviews(rangeKey = DEFAULT_RANGE, showTime = false) {
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

  const result = renderReviewsChart(data, showTime);
  if (result.success) {
    return `Rendered review ${showTime ? "time " : ""}history chart (${rangeText}).`;
  }
  return result.error;
}

export function getReviewsHelp() {
  return [
    "reviews [range]      - Render review history chart (stacked bar chart)",
    "reviews time [range] - Render review time history chart (stacked bar chart)",
    "retention [range]    - Render retention rate chart (line chart)",
    "",
    "Ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all",
    "",
    "Examples:",
    "  reviews            - Default: 1 month",
    "  reviews 6m         - 6 months",
    "  reviews time 1y    - 1 year of time history",
    "  reviews all        - Full history",
    "  retention          - Default: 1 month",
    "  retention 1y       - 1 year retention trend",
    "",
    "Review chart shows stacked bars by card status:",
    "  🟢 Mature   - Cards with interval ≥ 21 days",
    "  🔵 Young    - Cards with interval < 21 days",
    "  🟡 Learn    - Cards in learning phase",
    "  🔴 Relearn  - Cards being relearned",
    "",
    "Plot subcommands:",
    "  plot due [range]          - Due forecast",
    "  plot reviews [range]      - Review history",
    "  plot reviews time [range] - Review time history",
    "  plot retention [range]    - Retention rate",
  ];
}
