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
    const targetDates = globalSlice.map((d) => d.date);
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

      const paddedEntries = targetDates.map((date) => {
        if (entryMap.has(date)) {
          return entryMap.get(date);
        } else {
          // Empty entry
          return {
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
      });
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

    const total = entries.reduce(
      (sum, e) =>
        sum +
        (showTime
          ? e.time || 0
          : (e.count || 0) + (e.mature || 0) + (e.young || 0)),
      0,
    );

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
    // Convert global time to hours if cumulative, else minutes
    totalTimes = data.global.map((g) =>
      isCumulative
        ? Number(((g.time || 0) / 3600).toFixed(1))
        : Math.round((g.time || 0) / 60),
    );

    if (isCumulative) {
      let runSum = data.preSliceGlobalTime
        ? Number((data.preSliceGlobalTime / 3600).toFixed(1))
        : 0;
      totalTimes = totalTimes.map((t) => Number((runSum += t).toFixed(1)));
    }

    let datasetIndex = 0;
    const legendHTML = [];

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

      if (showTime) {
        // Time in hours if cumulative, else minutes
        deckData = deckEntries.map((e) =>
          isCumulative
            ? Number(((e.time || 0) / 3600).toFixed(1))
            : Math.round((e.time || 0) / 60),
        );
        preSum = isCumulative
          ? Number((deckPreSums.time / 3600).toFixed(1))
          : Math.round(deckPreSums.time / 60);
      } else {
        deckData = deckEntries.map((e) => e.count || 0);
        preSum = deckPreSums.count;
      }

      if (isCumulative) {
        let runningSum = preSum;
        deckData = deckData.map((val) =>
          Number((runningSum += val).toFixed(1)),
        );
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

      legendHTML.push(
        `<span data-dataset-index="${datasetIndex}"><i class="legend-color" style="background:${escapeHtml(color)}"></i> ${escapeHtml(deckName)}</span>`,
      );
      datasetIndex++;
    }

    if (legend) {
      legend.innerHTML = legendHTML.join("");
      legend.style.display = "flex";
      // Ensure wrap for many decks
      legend.style.flexWrap = "wrap";
      legend.style.rowGap = "8px";
    }
  } else {
    // Normal mature/young/etc
    if (legend) {
      legend.innerHTML = `
              <span data-dataset-index="0"><i class="legend-color color-mature"></i> Mature</span>
              <span data-dataset-index="1"><i class="legend-color color-young"></i> Young</span>
              <span data-dataset-index="2"><i class="legend-color color-relearn"></i> Relearn</span>
              <span data-dataset-index="3"><i class="legend-color color-learn"></i> Learn</span>
          `;
      legend.style.display = "flex";
      legend.style.flexWrap = "nowrap"; // reset
    }

    labels = data.map((entry) => entry.date);
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
    totalTimes = data.map((entry) =>
      isCumulative
        ? Number((entry.time / 3600).toFixed(1))
        : Math.round(entry.time / 60),
    );

    if (isCumulative) {
      let runSum = Number((preSumObj.time / 3600).toFixed(1));
      totalTimes = totalTimes.map((t) => Number((runSum += t).toFixed(1)));
    }

    let matureData, youngData, learnData, relearnData;
    if (showTime) {
      matureData = data.map((entry) =>
        isCumulative
          ? Number(((entry.time_mature || 0) / 3600).toFixed(1))
          : Math.round((entry.time_mature || 0) / 60),
      );
      youngData = data.map((entry) =>
        isCumulative
          ? Number(((entry.time_young || 0) / 3600).toFixed(1))
          : Math.round((entry.time_young || 0) / 60),
      );
      learnData = data.map((entry) =>
        isCumulative
          ? Number(((entry.time_learn || 0) / 3600).toFixed(1))
          : Math.round((entry.time_learn || 0) / 60),
      );
      relearnData = data.map((entry) =>
        isCumulative
          ? Number(((entry.time_relearn || 0) / 3600).toFixed(1))
          : Math.round((entry.time_relearn || 0) / 60),
      );
    } else {
      matureData = data.map((entry) => entry.mature || 0);
      youngData = data.map((entry) => entry.young || 0);
      learnData = data.map((entry) => entry.learn || 0);
      relearnData = data.map((entry) => entry.relearn || 0);
    }

    if (isCumulative) {
      let mSum = showTime
        ? Number((preSumObj.time_mature / 3600).toFixed(1))
        : preSumObj.mature;
      let ySum = showTime
        ? Number((preSumObj.time_young / 3600).toFixed(1))
        : preSumObj.young;
      let lSum = showTime
        ? Number((preSumObj.time_learn / 3600).toFixed(1))
        : preSumObj.learn;
      let rSum = showTime
        ? Number((preSumObj.time_relearn / 3600).toFixed(1))
        : preSumObj.relearn;
      matureData = matureData.map((val) => Number((mSum += val).toFixed(1)));
      youngData = youngData.map((val) => Number((ySum += val).toFixed(1)));
      learnData = learnData.map((val) => Number((lSum += val).toFixed(1)));
      relearnData = relearnData.map((val) => Number((rSum += val).toFixed(1)));
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
              title: (items) => items.map((item) => item.label).join("\n"),
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
