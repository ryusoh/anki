/**
 * Reviews Chart - Review History
 * Displays past review counts as a stacked bar chart
 */

import { bindLegendToggle, isLabelHidden } from "#js/commands/legendToggle.js";
import { parseRange, DEFAULT_RANGE } from "#js/utils/timeRange.js";
import { escapeHtml } from "#js/transactions/utils.js";

const Chart = window.Chart;

let reviewsChart = null;

export function destroyCharts() {
  if (reviewsChart) {
    reviewsChart.destroy();
    reviewsChart = null;
  }
}

export function getReviewStatsData(rangeKey = DEFAULT_RANGE, byDeck = false) {
  const payload = window.reviewStatsData || {};

  const days = parseRange(rangeKey);

  if (byDeck) {
    const byDeckData = payload.reviewsByDeck || {};
    // Extract dates from global to ensure all dates are present
    const globalData = Array.isArray(payload.reviews) ? payload.reviews : [];
    let globalSlice = globalData;
    let sliceIndex = 0;
    if (days !== null && days !== undefined) {
      sliceIndex = Math.max(0, globalData.length - days);
      globalSlice = globalData.slice(sliceIndex);
    }

    // Bolt: Use pre-allocated array instead of .map() to reduce garbage collection pressure.
    // This optimization bypasses callback function overhead during layout calculations.
    const targetDates = new Array(globalSlice.length);
    for (let i = 0, len = globalSlice.length; i < len; i++) {
      targetDates[i] = globalSlice[i].date;
    }
    const firstTargetDate = targetDates.length > 0 ? targetDates[0] : null;

    let preSliceGlobalTime = 0;

    // For each deck, construct an array matching targetDates
    const processedByDeck = {};
    const preSliceSumsByDeck = {};
    for (const [deckName, deckEntries] of Object.entries(byDeckData)) {
      const entryMap = new Map();
      let preSliceCount = 0;
      let preSliceTime = 0;
      deckEntries.forEach((entry) => {
        if (firstTargetDate && entry.date < firstTargetDate) {
          preSliceCount += entry.count || 0;
          preSliceTime += entry.time || 0;
        }
        entryMap.set(entry.date, entry);
      });
      preSliceSumsByDeck[deckName] = {
        count: preSliceCount,
        time: preSliceTime,
      };

      // Bolt: Use a pre-allocated array and a native for loop to initialize padded entries.
      // Doing this minimizes Date instantiations and object allocations compared to .map() chains.
      const paddedEntries = new Array(targetDates.length);
      for (let i = 0, len = targetDates.length; i < len; i++) {
        const date = targetDates[i];
        if (entryMap.has(date)) {
          paddedEntries[i] = entryMap.get(date);
        } else {
          // Empty entry
          paddedEntries[i] = {
            date: date,
            count: 0,
            time: 0,
            time_mature: 0,
            time_young: 0,
            time_learn: 0,
            time_relearn: 0,
            time_filtered: 0,
            mature: 0,
            young: 0,
            again: 0,
            hard: 0,
            good: 0,
            easy: 0,
            learn: 0,
            review: 0,
            relearn: 0,
            filtered: 0,
          };
        }
      }
      processedByDeck[deckName] = paddedEntries;
    }

    // compute global pre-slice global
    let globalPreTime = 0;
    for (let i = 0; i < sliceIndex; i++) {
      globalPreTime += globalData[i].time || 0;
    }

    return {
      dates: targetDates,
      byDeck: processedByDeck,
      global: globalSlice,
      preSliceSumsByDeck,
      preSliceGlobalTime,
      allTimeByDeck: byDeckData,
    };
  }

  const allData = Array.isArray(payload.reviews) ? payload.reviews : [];
  if (days === null || days === undefined) {
    const arr = [...allData];
    arr.preSliceSum = {
      mature: 0,
      young: 0,
      learn: 0,
      relearn: 0,
      time_mature: 0,
      time_young: 0,
      time_learn: 0,
      time_relearn: 0,
      time: 0,
    };
    return arr;
  }

  const sliceIndex = Math.max(0, allData.length - days);
  const slice = allData.slice(sliceIndex);

  const preSliceSum = {
    mature: 0,
    young: 0,
    learn: 0,
    relearn: 0,
    time_mature: 0,
    time_young: 0,
    time_learn: 0,
    time_relearn: 0,
    time: 0,
  };
  for (let i = 0; i < sliceIndex; i++) {
    preSliceSum.mature += allData[i].mature || 0;
    preSliceSum.young += allData[i].young || 0;
    preSliceSum.learn += allData[i].learn || 0;
    preSliceSum.relearn += allData[i].relearn || 0;
    preSliceSum.time_mature += allData[i].time_mature || 0;
    preSliceSum.time_young += allData[i].time_young || 0;
    preSliceSum.time_learn += allData[i].time_learn || 0;
    preSliceSum.time_relearn += allData[i].time_relearn || 0;
    preSliceSum.time += allData[i].time || 0;
  }
  slice.preSliceSum = preSliceSum;
  return slice;
}

const DECK_COLORS = [
  "hsla(216, 85%, 65%, 0.85)", // Azure Blue
  "hsla(348, 83%, 67%, 0.85)", // Neon Pink
  "hsla(152, 72%, 53%, 0.85)", // Emerald Green
  "hsla(268, 79%, 69%, 0.85)", // Amethyst Purple
  "hsla(32,  93%, 66%, 0.85)", // Tangerine
  "hsla(190, 90%, 55%, 0.85)", // Cyan
  "hsla(316, 73%, 62%, 0.85)", // Magenta
  "hsla(10,  85%, 66%, 0.85)", // Coral Red
  "hsla(230, 80%, 72%, 0.85)", // Periwinkle
  "hsla(118, 60%, 58%, 0.85)", // Mint Green
  "hsla(45,  95%, 60%, 0.85)", // Golden Yellow
  "hsla(175, 75%, 50%, 0.85)", // Turquoise
  "hsla(200, 80%, 75%, 0.85)", // Light Blue
  "hsla(330, 75%, 70%, 0.85)", // Rose
  "hsla(25,  90%, 65%, 0.85)", // Peach
];

export function getDeckColor(index) {
  return DECK_COLORS[index % DECK_COLORS.length];
}

export function groupAndSortDecks(byDeckData, showTime) {
  const groups = {};

  // Group by top-level deck name
  for (const [deckName, entries] of Object.entries(byDeckData)) {
    if (deckName === "Unknown") continue;

    // Bolt: Replace reduce with a for loop to eliminate O(N) callback allocations
    let total = 0;
    for (let i = 0; i < entries.length; i++) {
      const e = entries[i];
      total += showTime
        ? e.time || 0
        : (e.count || 0) + (e.mature || 0) + (e.young || 0);
    }

    const topLevelName = deckName.split("::")[0];
    if (!groups[topLevelName]) {
      groups[topLevelName] = {
        total: 0,
        subDecks: [],
      };
    }

    groups[topLevelName].total += total;
    groups[topLevelName].subDecks.push({
      deckName,
      total,
    });
  }

  // Sort groups by descending total
  const sortedGroups = Object.keys(groups).sort(
    (a, b) => groups[b].total - groups[a].total,
  );

  const result = [];
  let groupIndex = 0;

  for (const topLevel of sortedGroups) {
    const group = groups[topLevel];
    // Sort sub-decks within group by descending total
    group.subDecks.sort((a, b) => b.total - a.total);

    let subIndex = 0;
    for (const subDeck of group.subDecks) {
      result.push({
        deckName: subDeck.deckName,
        groupIndex,
        subIndex,
        totalInGroup: group.subDecks.length,
      });
      subIndex++;
    }
    groupIndex++;
  }

  return result;
}

export function getGroupedDeckColor(groupIndex, subIndex, totalInGroup) {
  const baseColor = DECK_COLORS[groupIndex % DECK_COLORS.length];

  if (totalInGroup <= 1 || subIndex === 0) return baseColor;

  // Expected format: "hsla(H, S%, L%, A)"
  const match = baseColor.match(
    /hsla\((\d+),\s*(\d+)%,\s*([\d.]+)%,\s*([\d.]+)\)/,
  );
  if (!match) return baseColor;

  let h = parseInt(match[1], 10);
  const s = parseInt(match[2], 10);
  let l = parseFloat(match[3]);
  const a = match[4];

  // Prime-number length offset arrays guarantee unique combinations
  // without cumulatively drifting into mathematical maximums (clamping).
  // Total unique combos within the family = 5 * 7 * 3 = 105 distinct colors.
  const hueOffsets = [0, 9, -9, 16, -16]; // Length 5
  const lightOffsets = [0, 18, -18, 10, -10, 26, -26]; // Length 7
  const satOffsets = [0, -25, -12]; // Length 3

  h = (h + hueOffsets[subIndex % hueOffsets.length] + 360) % 360;
  l = Math.max(
    25,
    Math.min(85, l + lightOffsets[subIndex % lightOffsets.length]),
  );

  const newS = Math.max(
    40,
    Math.min(100, s + satOffsets[subIndex % satOffsets.length]),
  );

  return `hsla(${Math.round(h)}, ${Math.round(newS)}%, ${Math.round(l)}%, ${a})`;
}

export function renderReviewsChart(
  data,
  showTime = false,
  byDeck = false,
  isCumulative = false,
) {
  const canvas = document.getElementById("runningAmountCanvas");
  const section = document.getElementById("runningAmountSection");
  const legend = document.getElementById("chartLegend");

  if (!canvas || !section) {
    return { success: false, error: "Canvas or section not found" };
  }

  // Destroy existing chart
  if (reviewsChart) {
    reviewsChart.destroy();
    reviewsChart = null;
  }

  // Validate data presence
  let hasData = false;
  if (byDeck) {
    hasData = data && data.dates && data.dates.length > 0;
  } else {
    hasData = Array.isArray(data) && data.length > 0;
  }

  if (!hasData) {
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

  const ctx = canvas.getContext("2d");

  let labels = [];
  let datasets = [];
  let totalTimes = [];
  let isDense = false;

  if (byDeck) {
    labels = data.dates;
    isDense = labels.length > 100;
    const radius = isDense ? 0 : 4;
    // Bolt: Use pre-allocated array and single loop instead of chained maps
    totalTimes = new Array(data.global.length);
    let runSum = isCumulative
      ? data.preSliceGlobalTime
        ? Number((data.preSliceGlobalTime / 3600).toFixed(1))
        : 0
      : 0;

    for (let i = 0; i < data.global.length; i++) {
      const g = data.global[i];
      const val = isCumulative
        ? Number(((g.time || 0) / 3600).toFixed(1))
        : Math.round((g.time || 0) / 60);

      if (isCumulative) {
        totalTimes[i] = Number((runSum += val).toFixed(1));
      } else {
        totalTimes[i] = val;
      }
    }

    let datasetIndex = 0;
    const legendSpans = [];

    const groupedDecks = groupAndSortDecks(data.allTimeByDeck, showTime);

    for (const deckInfo of groupedDecks) {
      const deckName = deckInfo.deckName;
      // Fetch padded slice data
      const deckEntries = data.byDeck[deckName];
      if (!deckEntries) continue;

      let deckData;
      let preSum = 0;
      const deckPreSums =
        data.preSliceSumsByDeck && data.preSliceSumsByDeck[deckName]
          ? data.preSliceSumsByDeck[deckName]
          : { count: 0, time: 0 };

      // Bolt: Use pre-allocated array and single loop instead of chained maps
      deckData = new Array(deckEntries.length);
      if (showTime) {
        preSum = isCumulative
          ? Number((deckPreSums.time / 3600).toFixed(1))
          : Math.round(deckPreSums.time / 60);
      } else {
        preSum = deckPreSums.count;
      }

      let runningSum = isCumulative ? preSum : 0;

      for (let i = 0; i < deckEntries.length; i++) {
        const e = deckEntries[i];
        let val;
        if (showTime) {
          val = isCumulative
            ? Number(((e.time || 0) / 3600).toFixed(1))
            : Math.round((e.time || 0) / 60);
        } else {
          val = e.count || 0;
        }

        if (isCumulative) {
          deckData[i] = Number((runningSum += val).toFixed(1));
        } else {
          deckData[i] = val;
        }
      }

      // Assign a related color dynamically based on group category
      const color = getGroupedDeckColor(
        deckInfo.groupIndex,
        deckInfo.subIndex,
        deckInfo.totalInGroup,
      );

      const datasetParams = isCumulative
        ? {
            type: "line",
            fill: true,
            stepped: true,
            tension: 0,
            pointRadius: 0,
            pointHoverRadius: 4,
            borderWidth: 0,
          }
        : {
            type: "bar",
            borderRadius: radius,
            barPercentage: isDense ? 1.0 : 0.9,
            categoryPercentage: isDense ? 1.0 : 0.8,
          };

      const resolvedBorderColor = isCumulative
        ? color.replace(/[\d.]+\)$/, "1)")
        : "transparent";

      datasets.push({
        label: deckName,
        hidden: isLabelHidden(deckName),
        data: deckData,
        backgroundColor: color,
        borderColor: resolvedBorderColor,
        hoverBackgroundColor: color,
        hoverBorderColor: resolvedBorderColor,
        stack: "reviews",
        ...datasetParams,
      });

      const span = document.createElement("span");
      span.setAttribute("data-dataset-index", datasetIndex.toString());
      const i = document.createElement("i");
      i.className = "legend-color";
      i.style.background = color;
      span.appendChild(i);
      span.appendChild(document.createTextNode(" " + deckName));
      legendSpans.push(span);

      datasetIndex++;
    }

    if (legend) {
      legend.textContent = "";
      for (const span of legendSpans) {
        legend.appendChild(span);
      }
      legend.style.display = "flex";
      // Ensure wrap for many decks
      legend.style.flexWrap = "wrap";
      legend.style.rowGap = "8px";
    }
  } else {
    // Normal mature/young/etc
    if (legend) {
      legend.textContent = "";

      const categories = [
        { id: "0", name: "Mature", cls: "legend-color color-mature" },
        { id: "1", name: "Young", cls: "legend-color color-young" },
        { id: "2", name: "Relearn", cls: "legend-color color-relearn" },
        { id: "3", name: "Learn", cls: "legend-color color-learn" },
      ];

      for (const cat of categories) {
        const span = document.createElement("span");
        span.setAttribute("data-dataset-index", cat.id);
        const i = document.createElement("i");
        i.className = cat.cls;
        span.appendChild(i);
        span.appendChild(document.createTextNode(" " + cat.name));
        legend.appendChild(span);
      }

      legend.style.display = "flex";
      legend.style.flexWrap = "nowrap"; // reset
    }

    // Bolt: Use pre-allocated array instead of .map() to reduce garbage collection pressure.
    labels = new Array(data.length);
    for (let i = 0, len = data.length; i < len; i++) {
      labels[i] = data[i].date;
    }
    isDense = labels.length > 100;
    const radius = isDense ? 0 : 4;
    const preSumObj = data.preSliceSum || {
      time: 0,
      mature: 0,
      young: 0,
      learn: 0,
      relearn: 0,
      time_mature: 0,
      time_young: 0,
      time_learn: 0,
      time_relearn: 0,
    };
    // Bolt: Replace multiple array maps with a single loop to reduce O(N) array allocations and GC pressure
    totalTimes = new Array(data.length);
    let matureData = new Array(data.length);
    let youngData = new Array(data.length);
    let learnData = new Array(data.length);
    let relearnData = new Array(data.length);

    let runSum = isCumulative ? Number((preSumObj.time / 3600).toFixed(1)) : 0;
    let mSum = isCumulative
      ? showTime
        ? Number((preSumObj.time_mature / 3600).toFixed(1))
        : preSumObj.mature
      : 0;
    let ySum = isCumulative
      ? showTime
        ? Number((preSumObj.time_young / 3600).toFixed(1))
        : preSumObj.young
      : 0;
    let lSum = isCumulative
      ? showTime
        ? Number((preSumObj.time_learn / 3600).toFixed(1))
        : preSumObj.learn
      : 0;
    let rSum = isCumulative
      ? showTime
        ? Number((preSumObj.time_relearn / 3600).toFixed(1))
        : preSumObj.relearn
      : 0;

    for (let i = 0; i < data.length; i++) {
      const entry = data[i];

      let tTime = isCumulative
        ? Number((entry.time / 3600).toFixed(1))
        : Math.round(entry.time / 60);

      let tMature = showTime
        ? isCumulative
          ? Number(((entry.time_mature || 0) / 3600).toFixed(1))
          : Math.round((entry.time_mature || 0) / 60)
        : entry.mature || 0;

      let tYoung = showTime
        ? isCumulative
          ? Number(((entry.time_young || 0) / 3600).toFixed(1))
          : Math.round((entry.time_young || 0) / 60)
        : entry.young || 0;

      let tLearn = showTime
        ? isCumulative
          ? Number(((entry.time_learn || 0) / 3600).toFixed(1))
          : Math.round((entry.time_learn || 0) / 60)
        : entry.learn || 0;

      let tRelearn = showTime
        ? isCumulative
          ? Number(((entry.time_relearn || 0) / 3600).toFixed(1))
          : Math.round((entry.time_relearn || 0) / 60)
        : entry.relearn || 0;

      if (isCumulative) {
        runSum += tTime;
        tTime = Number(runSum.toFixed(1));

        mSum += tMature;
        ySum += tYoung;
        lSum += tLearn;
        rSum += tRelearn;

        tMature = Number(mSum.toFixed(1));
        tYoung = Number(ySum.toFixed(1));
        tLearn = Number(lSum.toFixed(1));
        tRelearn = Number(rSum.toFixed(1));
      }

      totalTimes[i] = tTime;
      matureData[i] = tMature;
      youngData[i] = tYoung;
      learnData[i] = tLearn;
      relearnData[i] = tRelearn;
    }

    const baselineParams = isCumulative
      ? {
          type: "line",
          fill: true,
          stepped: true,
          tension: 0,
          pointRadius: 0,
          pointHoverRadius: 4,
          borderWidth: 0,
        }
      : {
          type: "bar",
          borderRadius: radius,
          barPercentage: isDense ? 1.0 : 0.9,
          categoryPercentage: isDense ? 1.0 : 0.8,
          borderWidth: 0,
        };

    datasets = [
      {
        label: "Mature",
        hidden: isLabelHidden("Mature"),
        data: matureData,
        backgroundColor: "rgba(72, 199, 142, 0.85)",
        borderColor: isCumulative ? "rgba(72, 199, 142, 1)" : "transparent",
        hoverBackgroundColor: "rgba(72, 199, 142, 0.85)",
        hoverBorderColor: isCumulative
          ? "rgba(72, 199, 142, 1)"
          : "transparent",
        stack: "reviews",
        ...baselineParams,
      },
      {
        label: "Young",
        hidden: isLabelHidden("Young"),
        data: youngData,
        backgroundColor: "rgba(73, 168, 236, 0.85)",
        borderColor: isCumulative ? "rgba(73, 168, 236, 1)" : "transparent",
        hoverBackgroundColor: "rgba(73, 168, 236, 0.85)",
        hoverBorderColor: isCumulative
          ? "rgba(73, 168, 236, 1)"
          : "transparent",
        stack: "reviews",
        ...baselineParams,
      },
      {
        label: "Relearn",
        hidden: isLabelHidden("Relearn"),
        data: relearnData,
        backgroundColor: "rgba(234, 67, 53, 0.85)",
        borderColor: isCumulative ? "rgba(234, 67, 53, 1)" : "transparent",
        hoverBackgroundColor: "rgba(234, 67, 53, 0.85)",
        hoverBorderColor: isCumulative ? "rgba(234, 67, 53, 1)" : "transparent",
        stack: "reviews",
        ...baselineParams,
      },
      {
        label: "Learn",
        hidden: isLabelHidden("Learn"),
        data: learnData,
        backgroundColor: "rgba(240, 185, 11, 0.85)",
        borderColor: isCumulative ? "rgba(240, 185, 11, 1)" : "transparent",
        hoverBackgroundColor: "rgba(240, 185, 11, 0.85)",
        hoverBorderColor: isCumulative
          ? "rgba(240, 185, 11, 1)"
          : "transparent",
        stack: "reviews",
        ...baselineParams,
      },
    ];
  }

  try {
    reviewsChart = new Chart(ctx, {
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
              text: showTime
                ? isCumulative
                  ? "Cumulative Time (hours)"
                  : "Time (minutes)"
                : isCumulative
                  ? "Cumulative Reviews"
                  : "Reviews",
              color: "#a9b4d0",
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
              label: (ctx) => {
                const unit = isCumulative ? "h" : "min";
                if (showTime) {
                  return `${ctx.dataset.label}: ${ctx.raw} ${unit}`;
                } else {
                  const time = totalTimes[ctx.dataIndex];
                  return `${ctx.dataset.label}: ${ctx.raw} (${time} ${unit} total)`;
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

export function showReviews(
  rangeKey = DEFAULT_RANGE,
  showTime = false,
  byDeck = false,
  isCumulative = false,
) {
  // Check if data is loaded
  if (
    !window.reviewStatsData ||
    !Array.isArray(window.reviewStatsData.reviews)
  ) {
    return "Review stats not loaded yet. Please wait a moment and try again.";
  }

  const data = getReviewStatsData(rangeKey, byDeck);
  const rangeLabel = rangeKey || DEFAULT_RANGE;
  const days = parseRange(rangeLabel);
  const rangeText = days === null ? "all time" : `${days} days`;

  const result = renderReviewsChart(data, showTime, byDeck, isCumulative);
  if (result.success) {
    let modeText = showTime ? "time " : "";
    if (byDeck) modeText += "by deck ";
    if (isCumulative) modeText = "cumulative " + modeText;
    return `Rendered review ${modeText}history chart (${rangeText}).`;
  }
  return result.error;
}

export function getReviewsHelp() {
  return [
    "reviews [range]           - Render review history chart (stacked bar chart)",
    "reviews time [range]      - Render review time history chart",
    "reviews deck [range]      - Render review history chart broken down by deck",
    "reviews time deck [range] - Render review time history broken down by deck",
    "retention [range]         - Render retention rate chart (line chart)",
    "",
    "Modifiers:",
    "  cumulative (c)          - Toggle cumulative view for any review chart",
    "",
    "Ranges: 1m, 2m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all",
    "",
    "Examples:",
    "  reviews                 - Default: 1 month",
    "  reviews deck 6m         - 6 months, broken down by deck",
    "  reviews time 1y         - 1 year of time history",
    "  reviews time cumulative - Cumulative review time history",
    "  reviews all             - Full history",
    "  retention               - Default: 1 month",
    "  retention 1y            - 1 year retention trend",
    "",
    "Review chart shows stacked bars by card status:",
    "  🟢 Mature   - Cards with interval ≥ 21 days",
    "  🔵 Young    - Cards with interval < 21 days",
    "  🟡 Learn    - Cards in learning phase",
    "  🔴 Relearn  - Cards being relearned",
    "",
    "Plot subcommands:",
    "  plot due [range]               - Due forecast",
    "  plot reviews [range]           - Review history by maturity",
    "  plot reviews time [range]      - Review time track by maturity",
    "  plot reviews deck [range]      - Review history by deck",
    "  plot reviews time deck [range] - Review time track by deck",
    "  plot \u003Cchart\u003E cumulative [range] - Cumulative version of review charts",
    "  plot retention [range]         - Retention rate",
  ];
}
