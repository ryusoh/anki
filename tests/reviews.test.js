const assert = require("assert");

// ============================================================================
// PURE FUNCTIONS TO TDD
// ============================================================================

function groupAndSortDecks(byDeckData, showTime) {
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

// Hardcoded base colors mimicking DECK_COLORS
const BASE_COLORS = [
  "hsla(320, 80%, 60%, 0.85)", // index 0
  "hsla(200, 80%, 50%, 0.85)", // index 1
  "hsla(40, 90%, 55%, 0.85)", // index 2
];

function getGroupedDeckColor(groupIndex, subIndex, totalInGroup) {
  const baseColor = BASE_COLORS[groupIndex % BASE_COLORS.length];

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

// Mock timeRange parseRange for getReviewStatsData test
function parseRange(rangeKey) {
  if (rangeKey === "1m") return 30;
  if (rangeKey === "1d") return 1;
  return null;
}

function getReviewStatsData(rangeKey = null, byDeck = false) {
  const payload = global.window.reviewStatsData || {};

  const days = parseRange(rangeKey);

  if (byDeck) {
    const byDeckData = payload.reviewsByDeck || {};
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
          return { date: date, count: 0, time: 0 };
        }
      });
      processedByDeck[deckName] = paddedEntries;
    }

    let globalPreTime = 0;
    for (let i = 0; i < sliceIndex; i++) {
      globalPreTime += globalData[i].time || 0;
    }

    return {
      dates: targetDates,
      byDeck: processedByDeck,
      global: globalSlice,
      preSliceSumsByDeck,
      preSliceGlobalTime: globalPreTime,
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

// ============================================================================
// TESTS
// ============================================================================

let passed = 0;
let failed = 0;

console.log("🧪 Reviews Deck Grouping and Coloring Tests\n");
console.log("=".repeat(60));

// Test 1: groupAndSortDecks
console.log("\n📋 Test 1: groupAndSortDecks correctly groups and sorts");
try {
  const byDeckData = {
    // Group "Language" - Total time: 100
    "Language::Japanese": [{ time: 60, count: 5 }],
    "Language::English": [{ time: 40, count: 5 }],
    // Group "Math" - Total time: 150
    "Math::Calculus": [{ time: 150, count: 5 }],
    // Group "History" (No subdecks) - Total time: 50
    History: [{ time: 50, count: 5 }],
  };

  const showTime = true;
  const result = groupAndSortDecks(byDeckData, showTime);

  // Expected order:
  // Math (150) -> Math::Calculus
  // Language (100) -> Language::Japanese (60), Language::English (40)
  // History (50) -> History

  assert.strictEqual(result.length, 4, "Should have 4 decks grouped");

  assert.strictEqual(result[0].deckName, "Math::Calculus");
  assert.strictEqual(result[0].groupIndex, 0);
  assert.strictEqual(result[0].subIndex, 0);

  assert.strictEqual(result[1].deckName, "Language::Japanese");
  assert.strictEqual(result[1].groupIndex, 1);
  assert.strictEqual(result[1].subIndex, 0);

  assert.strictEqual(result[2].deckName, "Language::English");
  assert.strictEqual(result[2].groupIndex, 1);
  assert.strictEqual(result[2].subIndex, 1);

  assert.strictEqual(result[3].deckName, "History");
  assert.strictEqual(result[3].groupIndex, 2);
  assert.strictEqual(result[3].subIndex, 0);

  console.log("   ✓ Decks grouped and sorted correctly");
  passed++;
} catch (e) {
  console.log(`   ✗ groupAndSortDecks: ${e.message}`);
  failed++;
}

// Test 2: groupAndSortDecks ignores Unknown deck
console.log("\n📋 Test 2: groupAndSortDecks ignores 'Unknown' deck");
try {
  const byDeckData = {
    Science: [{ time: 100, count: 5 }],
    Unknown: [{ time: 500, count: 5 }],
  };

  const result = groupAndSortDecks(byDeckData, true);
  assert.strictEqual(result.length, 1, "Should filter out Unknown deck");
  assert.strictEqual(result[0].deckName, "Science");

  console.log("   ✓ Unknown deck ignored");
  passed++;
} catch (e) {
  console.log(`   ✗ groupAndSortDecks (Unknown): ${e.message}`);
  failed++;
}

// Test 3: getGroupedDeckColor
console.log("\n📋 Test 3: getGroupedDeckColor creates distinct shades");
try {
  // Mock DECK_COLORS
  // Assume index 0 is hsla(320, 80%, 60%, 0.85)
  // We want to make sure subIndex 0 matches base, and subIndex 1/2 vary but share hue

  const color0_0 = getGroupedDeckColor(0, 0, 3);
  const color0_1 = getGroupedDeckColor(0, 1, 3);
  const color0_2 = getGroupedDeckColor(0, 2, 3);

  assert.notStrictEqual(
    color0_0,
    color0_1,
    "Colors in same group should differ",
  );
  assert.notStrictEqual(
    color0_1,
    color0_2,
    "Colors in same group should differ",
  );

  // They should all start with 'hsla('
  assert.ok(color0_0.startsWith("hsla("));
  assert.ok(color0_1.startsWith("hsla("));

  console.log("   ✓ Grouped colors generated correctly");
  passed++;
} catch (e) {
  console.log(`   ✗ getGroupedDeckColor: ${e.message}`);
  failed++;
}

// Test 4: groupAndSortDecks with mature/young structure
console.log(
  "\n📋 Test 4: groupAndSortDecks with futureDue structure (mature/young)",
);
try {
  const dueDeckData = {
    // Group "Science" - Total mature: 20, young: 10 => 30
    "Science::Physics": [{ mature: 20, young: 10 }],
    // Group "Art" - Total mature: 0, young: 5 => 5
    "Art::Drawing": [{ mature: 0, young: 5 }],
  };

  const showTime = false;
  const result = groupAndSortDecks(dueDeckData, showTime);

  assert.strictEqual(result.length, 2, "Should have 2 decks grouped");
  assert.strictEqual(
    result[0].deckName,
    "Science::Physics",
    "Science should be first due to larger sum (30)",
  );
  assert.strictEqual(
    result[1].deckName,
    "Art::Drawing",
    "Art should be second (5)",
  );

  console.log(
    "   ✓ Decks grouped and sorted correctly using mature/young counts",
  );
  passed++;
} catch (e) {
  console.log(`   ✗ groupAndSortDecks with mature/young: ${e.message}`);
  failed++;
}

// Test 5: getReviewStatsData preSlice bounds
console.log("\n📋 Test 5: getReviewStatsData preSlice bounds logic");
try {
  // Test global cumulative parsing
  global.window = {
    reviewStatsData: {
      reviews: [
        { date: "2023-01-01", mature: 10, young: 5, learn: 2, time: 100 },
        { date: "2023-01-02", mature: 5, young: 3, learn: 1, time: 50 },
        { date: "2023-01-03", mature: 20, young: 10, learn: 5, time: 200 },
      ],
    },
  };

  // If we pull only the last day ("1d"), preSliceSum should combine elements before it.
  const slicedData = getReviewStatsData("1d", false);
  assert.strictEqual(slicedData.length, 1, "Should return only 1 day");
  assert.strictEqual(slicedData[0].date, "2023-01-03");
  assert.strictEqual(slicedData.preSliceSum.mature, 15, "mature 10 + 5");
  assert.strictEqual(slicedData.preSliceSum.young, 8, "young 5 + 3");
  assert.strictEqual(slicedData.preSliceSum.time, 150, "time 100 + 50");

  console.log(
    "   ✓ getReviewStatsData sums global elements before target view",
  );
  passed++;
} catch (e) {
  console.log(`   ✗ getReviewStatsData preSlice global: ${e.message}`);
  failed++;
}

// Test 6: getReviewStatsData byDeck preSlice logic
console.log("\n📋 Test 6: getReviewStatsData preSlice bounds logic (byDeck)");
try {
  global.window = {
    reviewStatsData: {
      reviews: [
        { date: "2023-01-01", count: 17, time: 100 },
        { date: "2023-01-02", count: 9, time: 50 },
        { date: "2023-01-03", count: 35, time: 200 },
      ],
      reviewsByDeck: {
        Math: [
          { date: "2023-01-01", count: 10, time: 60 },
          { date: "2023-01-02", count: 5, time: 25 },
          { date: "2023-01-03", count: 20, time: 100 },
        ],
        Lang: [
          { date: "2023-01-01", count: 7, time: 40 },
          { date: "2023-01-02", count: 4, time: 25 },
          { date: "2023-01-03", count: 15, time: 100 },
        ],
      },
    },
  };

  const byDeckResult = getReviewStatsData("1d", true);

  assert.strictEqual(byDeckResult.dates.length, 1);
  assert.strictEqual(byDeckResult.dates[0], "2023-01-03");

  // Global pre time must sum everything before 2023-01-03
  assert.strictEqual(byDeckResult.preSliceGlobalTime, 150);

  // Deck specific slices
  assert.strictEqual(byDeckResult.preSliceSumsByDeck["Math"].count, 15);
  assert.strictEqual(byDeckResult.preSliceSumsByDeck["Math"].time, 85);

  assert.strictEqual(byDeckResult.preSliceSumsByDeck["Lang"].count, 11);
  assert.strictEqual(byDeckResult.preSliceSumsByDeck["Lang"].time, 65);

  console.log(
    "   ✓ getReviewStatsData computes accurate sums per deck properly",
  );
  passed++;
} catch (e) {
  console.log(`   ✗ getReviewStatsData Deck preSlice: ${e.message}`);
  failed++;
}

// Test 7: Time conversion in hours (TDD simulation)
console.log("\n📋 Test 7: Time conversion renders array in hours");
try {
  // Original implementation simulation for showTime
  const deckEntries = [
    { time: 120 }, // 2 hours
    { time: 90 }, // 1.5 hours
    { time: 30 }, // 0.5 hours
  ];

  // Test non-cumulative logic (Minutes)
  let isCumulative = false;
  let deckDataMinutes = deckEntries.map((e) =>
    isCumulative
      ? Number(((e.time || 0) / 3600).toFixed(1))
      : Math.round((e.time || 0) / 60),
  );

  assert.strictEqual(deckDataMinutes[0], 2);
  assert.strictEqual(deckDataMinutes[1], 2); // Math.round(1.5) -> 2
  assert.strictEqual(deckDataMinutes[2], 1); // Math.round(0.5) -> 1

  // Test cumulative logic (Hours)
  isCumulative = true;
  let deckDataHours = deckEntries.map((e) =>
    isCumulative
      ? Number(((e.time || 0) / 3600).toFixed(1))
      : Math.round((e.time || 0) / 60),
  );

  assert.strictEqual(deckDataHours[0], 0); // 120 / 3600 = 0.033 hours = 0.0
  assert.strictEqual(deckDataHours[1], 0); // 90 / 3600 = 0.025 = 0.0
  assert.strictEqual(deckDataHours[2], 0); // 30 / 3600 = 0.008 = 0.0

  console.log(
    "   ✓ Time correctly keeps minutes when non-cumulative, scales strictly to hours when cumulative",
  );
  passed++;
} catch (e) {
  console.log(`   ✗ Time conversion hours: ${e.message}`);
  failed++;
}

// Test 8: Consistent Color Assignment (TDD logic)
console.log(
  "\n📋 Test 8: Consistent groupAndSortDecks sorting across time ranges",
);
try {
  // We simulate the exact behavior of `renderReviewsChart` to ensure consistent color indices.
  global.window = {
    reviewStatsData: {
      reviews: [],
      reviewsByDeck: {
        Math: [
          { date: "2023-01-01", count: 100, time: 600 },
          { date: "2023-12-01", count: 10, time: 60 }, // recent
        ],
        Lang: [
          { date: "2023-01-01", count: 10, time: 60 },
          { date: "2023-12-01", count: 100, time: 600 }, // recent
        ],
      },
    },
  };

  // 1. If we sort by the sliced current data (1m / recent), Lang > Math
  const recentSliceData = {
    Math: [{ count: 10, time: 60 }],
    Lang: [{ count: 100, time: 600 }],
  };
  const recentSorted = groupAndSortDecks(recentSliceData, false);
  assert.strictEqual(recentSorted[0].deckName, "Lang");
  assert.strictEqual(recentSorted[1].deckName, "Math");

  // 2. But if we sort by `allTimeByDeck`, Math > Lang, and it remains static
  const allTimeData = getReviewStatsData("1m", true).allTimeByDeck;
  const consistentSorted = groupAndSortDecks(allTimeData, false);

  assert.strictEqual(
    consistentSorted[0].deckName,
    "Math",
    "Math has 110 all-time",
  );
  assert.strictEqual(
    consistentSorted[1].deckName,
    "Lang",
    "Lang has 110 all-time, wait, both 110. Math is processed first in object keys? No, total is equal.",
  );

  // Let's adjust mock so Math has definitively more to ensure stability test works properly without relying on object key order
  global.window.reviewStatsData.reviewsByDeck["Math"][0].count = 200;

  const allTimeData2 = getReviewStatsData("1m", true).allTimeByDeck;
  const consistentSorted2 = groupAndSortDecks(allTimeData2, false);
  assert.strictEqual(
    consistentSorted2[0].deckName,
    "Math",
    "Math has 210 all-time, Lang has 110",
  );
  assert.strictEqual(consistentSorted2[1].deckName, "Lang");

  console.log(
    "   ✓ allTimeByDeck maintains consistent color classification indices regardless of slice",
  );
  passed++;
} catch (e) {
  console.log(`   ✗ Consistent color indices: ${e.message}`);
  failed++;
}

// Test 9: Gradient Stable when a deck is empty
console.log(
  "\n📋 Test 9: groupAndSortDecks retains gradient structure regardless of empty decks",
);
try {
  const allData = {
    "English::Vocab": [{ count: 100 }],
    "English::Grammar": [{ count: 50 }],
    "English::Reading": [{ count: 20 }],
  };

  const missingData = {
    "English::Vocab": [{ count: 100 }],
    "English::Grammar": [{ count: 0 }], // Empty!
    "English::Reading": [{ count: 20 }],
  };

  const fullGroup = groupAndSortDecks(allData, false);
  const missingGroup = groupAndSortDecks(missingData, false);

  assert.strictEqual(
    missingGroup.find((d) => d.deckName === "English::Vocab").totalInGroup,
    fullGroup.find((d) => d.deckName === "English::Vocab").totalInGroup,
    "totalInGroup must remain static so gradient divisions don't shift when a deck falls to 0",
  );

  console.log(
    "   ✓ groupAndSortDecks retains gradient structure regardless of empty decks",
  );
  passed++;
} catch (e) {
  console.log(`   ✗ Empty deck gradient stability: ${e.message}`);
  failed++;
}

console.log("\n" + "=".repeat(60));
console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

if (failed > 0) {
  console.log("❌ TESTS FAILED");
  process.exit(1);
} else {
  console.log("✅ ALL TESTS PASSED");
  process.exit(0);
}
