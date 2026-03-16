/**
 * Due Chart - Future Review Forecast
 * Displays upcoming reviews split by mature/young cards
 */

import { bindLegendToggle, isLabelHidden } from "#js/commands/legendToggle.js";
import { parseRange, DEFAULT_RANGE } from "#js/utils/timeRange.js";
import { escapeHtml } from "#js/transactions/utils.js";

const Chart = window.Chart;

let futureChart = null;

export function destroyChart() {
  if (futureChart) {
    futureChart.destroy();
    futureChart = null;
  }
}

export function getFutureDueData(rangeKey = DEFAULT_RANGE, byDeck = false) {
  const payload = window.customStatsData || {};
  let allData;

  if (byDeck) {
    allData = payload.futureDueByDeck || {};
  } else {
    allData = Array.isArray(payload.futureDue) ? payload.futureDue : [];
  }

  const days = parseRange(rangeKey);
  if (days === null || days === undefined) {
    return allData;
  }

  if (byDeck) {
    const limitedData = {};
    for (const [deckName, entries] of Object.entries(allData)) {
      if (Array.isArray(entries)) {
        // Find indices within the day range
        // Since entries are sorted by day in the Python export, we can stop at `day >= days`
        limitedData[deckName] = entries.filter((e) => e.day < days);
      }
    }
    return limitedData;
  } else {
    // Array of global due counts
    return allData.slice(0, days);
  }
}

export function renderFutureDueChart(data, byDeck = false, rangeDays = null) {
  const canvas = document.getElementById("runningAmountCanvas");
  const section = document.getElementById("runningAmountSection");
  const legend = document.getElementById("chartLegend");

  if (!canvas || !section) {
    return { success: false, error: "Canvas or section not found" };
  }

  // Destroy existing chart
  if (futureChart) {
    futureChart.destroy();
    futureChart = null;
  }

  if (!data) {
    return { success: false, error: "No data" };
  }

  let hasData = false;
  if (byDeck) {
    hasData = Object.values(data).some(
      (entries) =>
        entries.length > 0 && entries.some((e) => e.mature > 0 || e.young > 0),
    );
  } else {
    hasData =
      Array.isArray(data) &&
      data.some((d) => (d.mature || 0) + (d.young || 0) > 0);
  }

  if (!hasData) {
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

  // Compute maximum day for labels
  let maxDay = 0;
  if (byDeck) {
    const allDays = Object.values(data).flatMap((entries) =>
      entries.map((e) => e.day),
    );
    if (allDays.length > 0) {
      maxDay = Math.max(...allDays);
    }
  } else {
    maxDay = data.length > 0 ? data[data.length - 1].day : 0;
  }

  if (rangeDays && maxDay < rangeDays - 1) {
    maxDay = rangeDays - 1;
  }

  const numDays = maxDay + 1;
  const labels = Array.from({ length: numDays }, (_, i) => {
    if (i === 0) return "Today";
    if (i === 1) return "Tomorrow";
    return `+${i}d`;
  });

  const datasets = [];

  if (byDeck) {
    // Dynamically import helpers so we don't duplicate logic
    import("#js/commands/reviews.js").then((reviewsModule) => {
      const { groupAndSortDecks, getGroupedDeckColor } = reviewsModule;

      const layout = groupAndSortDecks(
        window.customStatsData.futureDueByDeck,
        false,
      );

      let datasetIdx = 0;
      let legendHtml = "";

      for (const deckInfo of layout) {
        const deckName = deckInfo.deckName;
        const entries = data[deckName] || [];

        const daySparseMap = {};
        for (const e of entries) {
          daySparseMap[e.day] = (e.mature || 0) + (e.young || 0);
        }

        const counts = Array.from(
          { length: numDays },
          (_, i) => daySparseMap[i] || 0,
        );

        const color = getGroupedDeckColor(
          deckInfo.groupIndex,
          deckInfo.subIndex,
          deckInfo.totalInGroup,
        );

        datasets.push({
          label: deckName,
          hidden: isLabelHidden(deckName),
          data: counts,
          backgroundColor: color,
          borderRadius: numDays > 100 ? 0 : 4,
          barPercentage: numDays > 100 ? 1.0 : 0.9,
          categoryPercentage: numDays > 100 ? 1.0 : 0.8,
          stack: "future",
        });

        legendHtml += `<span data-dataset-index="${datasetIdx}"><i class="legend-color" style="background:${color};"></i> ${escapeHtml(deckName)}</span>`;
        datasetIdx++;
      }

      if (legend) {
        legend.innerHTML = legendHtml;
        legend.style.display = "flex";
      }

      finishRenderDue(canvas, labels, datasets, legend, section, byDeck);
    });
    return { success: true }; // async render
  } else {
    // Global render (original logic)
    // Extract padded arrays up to maxDay
    const dayMapMature = {};
    const dayMapYoung = {};
    for (const e of data) {
      dayMapMature[e.day] = e.mature || 0;
      dayMapYoung[e.day] = e.young || 0;
    }

    const matureDataset = Array.from(
      { length: numDays },
      (_, i) => dayMapMature[i] || 0,
    );
    const youngDataset = Array.from(
      { length: numDays },
      (_, i) => dayMapYoung[i] || 0,
    );

    const radius = numDays > 100 ? 0 : 4;

    datasets.push({
      label: "Mature",
      hidden: isLabelHidden("Mature"),
      data: matureDataset,
      backgroundColor: "rgba(72, 199, 142, 0.85)",
      borderRadius: radius,
      barPercentage: numDays > 100 ? 1.0 : 0.9,
      categoryPercentage: numDays > 100 ? 1.0 : 0.8,
      stack: "future",
    });
    datasets.push({
      label: "Young",
      hidden: isLabelHidden("Young"),
      data: youngDataset,
      backgroundColor: "rgba(73, 168, 236, 0.85)",
      borderRadius: radius,
      barPercentage: numDays > 100 ? 1.0 : 0.9,
      categoryPercentage: numDays > 100 ? 1.0 : 0.8,
      stack: "future",
    });

    if (legend) {
      legend.innerHTML = `
        <span data-dataset-index="0"><i class="legend-color color-mature"></i> Mature</span>
        <span data-dataset-index="1"><i class="legend-color color-young"></i> Young</span>
      `;
      legend.style.display = "flex";
    }

    return finishRenderDue(canvas, labels, datasets, legend, section, byDeck);
  }
}

function finishRenderDue(canvas, labels, datasets, legend, section, byDeck) {
  const ctx = canvas.getContext("2d");
  try {
    futureChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets,
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
          colors: false,
          tooltip: {
            backgroundColor: "rgba(2, 6, 20, 0.9)",
            titleFont: { family: "JetBrains Mono, monospace", size: 12 },
            bodyFont: { family: "JetBrains Mono, monospace", size: 12 },
            callbacks: {
              title: (items) => items.map((item) => item.label).join("\n"),
              label: (context) => {
                if (context.raw === 0) return null;
                if (byDeck) return `${context.dataset.label}: ${context.raw}`;
                return `${context.dataset.label}: ${context.raw}`;
              },
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

export function showDue(rangeKey = DEFAULT_RANGE, byDeck = false) {
  // Check if data is loaded
  if (!window.customStatsData || !window.customStatsData.futureDue) {
    return "Stats not loaded yet. Please wait a moment and try again.";
  }

  const data = getFutureDueData(rangeKey, byDeck);
  const rangeLabel = rangeKey || DEFAULT_RANGE;
  const days = parseRange(rangeLabel);
  const rangeText = days === null ? "all time" : `${days} days`;

  const result = renderFutureDueChart(data, byDeck, days);
  if (result.success) {
    return `Rendered upcoming reviews chart (${rangeText}).`;
  }
  return result.error;
}

export function getDueHelp() {
  return [
    "due [range] - Render upcoming reviews chart",
    "due deck [range] - Render upcoming reviews by deck",
    "",
    "Ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all",
    "",
    "Examples:",
    "  due        - Default: 1 month",
    "  due 3m     - 3 months",
    "  due deck   - Broken down by deck",
  ];
}
