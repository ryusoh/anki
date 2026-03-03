/**
 * Due Chart - Future Review Forecast
 * Displays upcoming reviews split by mature/young cards
 */

const Chart = window.Chart;

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

  const days = TIME_RANGES[rangeKey];
  if (days === null || days === undefined) {
    return allData;
  }

  return allData.slice(0, Math.min(days, allData.length));
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
            <span><i class="legend-color color-young"></i> 未習熟</span>
            <span><i class="legend-color color-mature"></i> 習熟済み</span>
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
      empty.textContent = "まだデータがありません。復習を進めてください。";
    }
    section.classList.remove("is-hidden");
    return { success: false, error: "No data" };
  }

  // Hide empty message
  const empty = document.getElementById("runningAmountEmpty");
  if (empty) empty.style.display = "none";

  const labels = data.map((entry, i) => {
    if (i === 0) return "今日";
    if (i === 1) return "明日";
    return `${entry.day}日後`;
  });

  const matureDataset = data.map((entry) => entry.mature || 0);
  const youngDataset = data.map((entry) => entry.young || 0);

  const ctx = canvas.getContext("2d");
  try {
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
  const days = TIME_RANGES[rangeLabel];
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
