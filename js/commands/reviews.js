/**
 * Reviews Chart - Review History with Retention
 * Displays past review counts and retention rates
 */

export const DEFAULT_RANGE = "1m";

export const TIME_RANGES = {
  "1m": 30,
  "2m": 60,
  "3m": 90,
  "6m": 180,
  "1y": 365,
  "2y": 730,
  "3y": 1095,
  "5y": 1825,
  "10y": 3650,
  all: null,
};

let reviewsChart = null;
let retentionChart = null;

export function destroyCharts() {
  if (reviewsChart) {
    reviewsChart.destroy();
    reviewsChart = null;
  }
  if (retentionChart) {
    retentionChart.destroy();
    retentionChart = null;
  }
}

export function getReviewStatsData(rangeKey = DEFAULT_RANGE) {
  const payload = window.reviewStatsData || {};
  const allData = Array.isArray(payload.reviews) ? payload.reviews : [];

  const days = TIME_RANGES[rangeKey];
  if (days === null || days === undefined) {
    return allData;
  }

  // Get last N days of data
  return allData.slice(-Math.min(days, allData.length));
}

export function renderReviewsChart(data) {
  const canvas = document.getElementById("runningAmountCanvas");
  const section = document.getElementById("runningAmountSection");
  const legend = document.getElementById("chartLegend");

  if (!canvas || !section) {
    return { success: false, error: "Canvas or section not found" };
  }

  // Update legend for reviews chart (only reviews, no retention)
  if (legend) {
    legend.innerHTML = `
            <span><i class="legend-color color-reviews"></i> Reviews</span>
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
      empty.textContent = "レビューデータがありません。";
    }
    section.classList.remove("is-hidden");
    return { success: false, error: "No data" };
  }

  // Hide empty message
  const empty = document.getElementById("runningAmountEmpty");
  if (empty) empty.style.display = "none";

  const labels = data.map((entry) => entry.date);
  const counts = data.map((entry) => entry.count);
  const times = data.map((entry) => Math.round(entry.time / 60)); // minutes

  const ctx = canvas.getContext("2d");
  reviewsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Reviews",
          data: counts,
          backgroundColor: "rgba(73, 168, 236, 0.7)",
          borderRadius: 4,
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
          ticks: {
            color: "#a9b4d0",
            precision: 0,
            font: { family: "JetBrains Mono, monospace", size: 10 },
          },
          grid: { color: "rgba(255,255,255,0.1)" },
          title: {
            display: true,
            text: "Reviews",
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
              const time = times[ctx.dataIndex];
              return `${ctx.dataset.label}: ${ctx.raw} (${time} min)`;
            },
          },
        },
      },
    },
  });

  section.classList.remove("is-hidden");
  return { success: true };
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
            <span><i class="legend-color color-retention"></i> Retention Rate</span>
        `;
    legend.style.display = "flex";
  }

  // Destroy existing chart
  if (retentionChart) {
    retentionChart.destroy();
    retentionChart = null;
  }

  if (!Array.isArray(data) || data.length === 0) {
    const empty = document.getElementById("runningAmountEmpty");
    if (empty) {
      empty.style.display = "block";
      empty.textContent = " retention データがありません。";
    }
    section.classList.remove("is-hidden");
    return { success: false, error: "No data" };
  }

  // Hide empty message
  const empty = document.getElementById("runningAmountEmpty");
  if (empty) empty.style.display = "none";

  const labels = data.map((entry) => entry.date);
  const retentions = data.map((entry) => (entry.retention * 100).toFixed(1));

  const ctx = canvas.getContext("2d");
  retentionChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Retention %",
          data: retentions,
          borderColor: "rgba(240, 185, 11, 0.9)",
          backgroundColor: "rgba(240, 185, 11, 0.1)",
          borderWidth: 2,
          pointRadius: 2,
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
        tooltip: {
          backgroundColor: "rgba(2, 6, 20, 0.9)",
          titleFont: { family: "JetBrains Mono, monospace", size: 12 },
          bodyFont: { family: "JetBrains Mono, monospace", size: 11 },
          callbacks: {
            title: (items) => items.map((item) => item.label).join("\n"),
            label: (ctx) => `Retention: ${ctx.raw}%`,
          },
        },
      },
    },
  });

  section.classList.remove("is-hidden");
  return { success: true };
}

export function showReviews(rangeKey = DEFAULT_RANGE) {
  const data = getReviewStatsData(rangeKey);
  const rangeLabel = rangeKey || DEFAULT_RANGE;
  const days = TIME_RANGES[rangeLabel];
  const rangeText = days === null ? "all time" : `${days} days`;

  const result = renderReviewsChart(data);
  if (result.success) {
    return `Rendered review history chart (${rangeText}).`;
  }
  return result.error;
}

export function showRetention(rangeKey = DEFAULT_RANGE) {
  const data = getReviewStatsData(rangeKey);
  const rangeLabel = rangeKey || DEFAULT_RANGE;
  const days = TIME_RANGES[rangeLabel];
  const rangeText = days === null ? "all time" : `${days} days`;

  const result = renderRetentionChart(data);
  if (result.success) {
    return `Rendered retention rate chart (${rangeText}).`;
  }
  return result.error;
}

export function getReviewsHelp() {
  return [
    "reviews [range] - Render review history chart (bar chart)",
    "retention [range] - Render retention rate chart (line chart)",
    "",
    "Ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all",
    "",
    "Examples:",
    "  reviews            - Default: 1 month",
    "  reviews 6m         - 6 months",
    "  reviews all        - Full history",
    "  retention          - Default: 1 month",
    "  retention 1y       - 1 year retention trend",
    "",
    "Plot subcommands:",
    "  plot due [range]       - Due forecast",
    "  plot reviews [range]   - Review history",
    "  plot retention [range] - Retention rate",
  ];
}
