/**
 * Due Chart - Future Review Forecast
 * Displays upcoming reviews split by mature/young cards
 */

import { bindLegendToggle, isLabelHidden } from "#js/commands/legendToggle.js";
import {
  parseRange,
  parseRangeSpec,
  formatRange,
  calendarRangeToDayOffsets,
  DEFAULT_RANGE,
} from "#js/utils/timeRange.js";

const Chart = window.Chart;

let futureChart = null;

export function destroyChart() {
  /* c8 ignore next 4 */
  if (futureChart) {
    futureChart.destroy();
    futureChart = null;
  }
}

export function getFutureDueData(rangeKey = DEFAULT_RANGE, byDeck = false) {
  /* c8 ignore next */
  const payload = window.customStatsData || {};
  let allData;

  if (byDeck) {
    allData = payload.futureDueByDeck || {};
  } else {
    allData = Array.isArray(payload.futureDue) ? payload.futureDue : [];
  }

  const spec = parseRangeSpec(rangeKey);

  if (!spec || spec.kind === "all") {
    return allData;
  }

  if (spec.kind === "calendar") {
    const offsets = calendarRangeToDayOffsets(spec);
    // Whole window already in the past -> nothing is due there.
    if (!offsets) return byDeck ? {} : [];
    const inWindow = (e) => e.day >= offsets.start && e.day <= offsets.end;

    if (byDeck) {
      const limitedData = {};
      for (const [deckName, entries] of Object.entries(allData)) {
        if (Array.isArray(entries)) {
          limitedData[deckName] = entries.filter(inWindow);
        }
      }
      return limitedData;
    }
    return allData.filter(inWindow);
  }

  const days = spec.days;

  if (byDeck) {
    const limitedData = {};
    for (const [deckName, entries] of Object.entries(allData)) {
      if (Array.isArray(entries)) {
        // Bolt: Optimize sorted array filtering with early exit to avoid O(N) traversal.
        // Since entries are sorted by day in the Python export, we can stop at `day >= days`
        const filtered = [];
        for (let i = 0, len = entries.length; i < len; i++) {
          const e = entries[i];
          if (e.day >= days) break;
          filtered.push(e);
        }
        limitedData[deckName] = filtered;
      }
    }
    return limitedData;
  } else {
    // Array of global due counts
    return allData.slice(0, days);
  }
}

export function renderFutureDueChart(
  data,
  byDeck = false,
  rangeDays = null,
  rangeSpec = null,
) {
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
  /* c8 ignore next 10 */
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
    /* c8 ignore next 4 */
    if (empty) {
      empty.style.display = "block";
      empty.textContent = "No data yet. Complete some reviews first.";
    }
    section.classList.remove("is-hidden");
    return { success: false, error: "No data" };
  }

  // Hide empty message
  const empty = document.getElementById("runningAmountEmpty");
  /* c8 ignore next */
  if (empty) empty.style.display = "none";

  // Compute the min/max day span for labels. For every existing caller data
  // starts at day 0, so minDay is always 0 there (backward-compat guarantee);
  // a calendar window starting in the future is the only case minDay > 0.
  let maxDay = 0;
  let minDay = Infinity;
  /* c8 ignore next 14 */
  if (byDeck) {
    // Bolt: Use native for loops to find the max day instead of .flatMap().map()
    // This avoids large intermediate array allocations and prevents Math.max stack overflow on large datasets.
    for (const entries of Object.values(data)) {
      for (let i = 0, len = entries.length; i < len; i++) {
        if (entries[i].day > maxDay) {
          maxDay = entries[i].day;
        }
        if (entries[i].day < minDay) {
          minDay = entries[i].day;
        }
      }
    }
  } else {
    maxDay = data.length > 0 ? data[data.length - 1].day : 0;
    minDay = data.length > 0 ? data[0].day : 0;
  }
  if (minDay === Infinity) minDay = 0;

  if (rangeDays && maxDay < rangeDays - 1) {
    maxDay = rangeDays - 1;
  }

  const numDays = maxDay - minDay + 1;
  const labels = new Array(numDays);
  const isCalendar = rangeSpec && rangeSpec.kind === "calendar";
  // Calendar mode labels the axis with real dates, but the hover tooltip
  // keeps the relative-offset form (Today/Tomorrow/+Nd) duration mode uses.
  const tooltipTitles = isCalendar ? new Array(numDays) : null;
  const base = new Date();
  const todayLocal = new Date(
    base.getFullYear(),
    base.getMonth(),
    base.getDate(),
  );

  // Bolt: Hoist Date instantiation out of the loop and mutate it
  // to avoid O(N) object allocations and Garbage Collection pressure.
  let iterDate = null;
  if (isCalendar) {
    iterDate = new Date(todayLocal.getTime());
    iterDate.setDate(iterDate.getDate() + minDay);
  }

  for (let i = 0; i < numDays; i++) {
    const day = minDay + i;
    const offsetLabel =
      day === 0 ? "Today" : day === 1 ? "Tomorrow" : `+${day}d`;
    if (isCalendar) {
      const m = iterDate.getMonth() + 1;
      const d = iterDate.getDate();
      const mm = m < 10 ? "0" + m : "" + m;
      const dd = d < 10 ? "0" + d : "" + d;
      labels[i] = `${iterDate.getFullYear()}-${mm}-${dd}`;
      tooltipTitles[i] = offsetLabel;
      iterDate.setDate(iterDate.getDate() + 1);
    } else {
      labels[i] = offsetLabel;
    }
  }

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
      const legendSpans = [];

      for (const deckInfo of layout) {
        const deckName = deckInfo.deckName;
        const entries = data[deckName] || [];

        const daySparseMap = {};
        /* c8 ignore next 7 */
        for (const e of entries) {
          daySparseMap[e.day] = (e.mature || 0) + (e.young || 0);
        }

        const counts = new Array(numDays);
        for (let i = 0; i < numDays; i++) {
          counts[i] = daySparseMap[minDay + i] || 0;
        }

        const color = getGroupedDeckColor(
          deckInfo.groupIndex,
          deckInfo.subIndex,
          deckInfo.totalInGroup,
        );

        /* c8 ignore next */
        const radius = numDays > 100 ? 0 : 4;

        datasets.push({
          label: deckName,
          hidden: isLabelHidden(deckName),
          data: counts,
          backgroundColor: color,
          borderRadius: radius,
          /* c8 ignore next 2 */
          barPercentage: numDays > 100 ? 1.0 : 0.9,
          categoryPercentage: numDays > 100 ? 1.0 : 0.8,
          stack: "future",
        });

        const span = document.createElement("span");
        span.setAttribute("data-dataset-index", datasetIdx.toString());
        const i = document.createElement("i");
        i.className = "legend-color";
        i.style.background = color;
        span.appendChild(i);
        span.appendChild(document.createTextNode(" " + deckName));
        legendSpans.push(span);

        datasetIdx++;
      }

      /* c8 ignore next 7 */
      if (legend) {
        legend.textContent = "";
        for (const span of legendSpans) {
          legend.appendChild(span);
        }
        legend.style.display = "flex";
      }

      finishRenderDue(
        canvas,
        labels,
        datasets,
        legend,
        section,
        byDeck,
        tooltipTitles,
      );
    });
    return { success: true }; // async render
  } else {
    // Global render (original logic)
    // Extract padded arrays up to maxDay
    const dayMapMature = {};
    const dayMapYoung = {};
    /* c8 ignore next 12 */
    for (const e of data) {
      dayMapMature[e.day] = e.mature || 0;
      dayMapYoung[e.day] = e.young || 0;
    }

    const matureDataset = new Array(numDays);
    const youngDataset = new Array(numDays);
    for (let i = 0; i < numDays; i++) {
      matureDataset[i] = dayMapMature[minDay + i] || 0;
      youngDataset[i] = dayMapYoung[minDay + i] || 0;
    }

    /* c8 ignore next */
    const radius = numDays > 100 ? 0 : 4;

    datasets.push({
      label: "Mature",
      hidden: isLabelHidden("Mature"),
      data: matureDataset,
      backgroundColor: "rgba(72, 199, 142, 0.85)",
      borderRadius: radius,
      /* c8 ignore next 2 */
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
      /* c8 ignore next 2 */
      barPercentage: numDays > 100 ? 1.0 : 0.9,
      categoryPercentage: numDays > 100 ? 1.0 : 0.8,
      stack: "future",
    });

    /* c8 ignore next 17 */
    if (legend) {
      legend.textContent = "";

      const spanMature = document.createElement("span");
      spanMature.setAttribute("data-dataset-index", "0");
      const iMature = document.createElement("i");
      iMature.className = "legend-color color-mature";
      spanMature.appendChild(iMature);
      spanMature.appendChild(document.createTextNode(" Mature"));
      legend.appendChild(spanMature);

      const spanYoung = document.createElement("span");
      spanYoung.setAttribute("data-dataset-index", "1");
      const iYoung = document.createElement("i");
      iYoung.className = "legend-color color-young";
      spanYoung.appendChild(iYoung);
      spanYoung.appendChild(document.createTextNode(" Young"));
      legend.appendChild(spanYoung);

      legend.style.display = "flex";
    }

    return finishRenderDue(
      canvas,
      labels,
      datasets,
      legend,
      section,
      byDeck,
      tooltipTitles,
    );
  }
}

function finishRenderDue(
  canvas,
  labels,
  datasets,
  legend,
  section,
  byDeck,
  tooltipTitles = null,
) {
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
              title: (items) => {
                let title = "";
                for (let i = 0; i < items.length; i++) {
                  const text = tooltipTitles
                    ? tooltipTitles[items[i].dataIndex]
                    : items[i].label;
                  title += (i > 0 ? "\n" : "") + text;
                }
                return title;
              },
              label: (context) => {
                /* c8 ignore next */
                if (context.raw === 0) return null;
                /* c8 ignore next */
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
  /* c8 ignore next 3 */
  if (legend && futureChart) {
    bindLegendToggle(futureChart, legend);
  }

  return { success: true };
}

export function showDue(rangeKey = DEFAULT_RANGE, byDeck = false) {
  // Check if data is loaded
  /* c8 ignore next 3 */
  if (!window.customStatsData || !window.customStatsData.futureDue) {
    return "Stats not loaded yet. Please wait a moment and try again.";
  }

  const data = getFutureDueData(rangeKey, byDeck);
  /* c8 ignore next */
  const rangeLabel = rangeKey || DEFAULT_RANGE;
  const spec = parseRangeSpec(rangeLabel);
  const days = parseRange(rangeLabel);
  const rangeText = formatRange(rangeLabel);

  const result = renderFutureDueChart(data, byDeck, days, spec);
  /* c8 ignore next 4 */
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
