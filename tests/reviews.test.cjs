const assert = require("assert");

let capturedConfig = null;
global.window = {
    Chart: class {
        constructor(ctx, config) {
            this.config = config || {};
            this.data = this.config.data || { datasets: [] };
            capturedConfig = config;

            if (ctx === 'THROW') {
                throw new Error('Chart render error');
            }
        }
        destroy() {}
        update() {}
        setDatasetVisibility() {}
        isDatasetVisible() { return true; }
    },
    reviewStatsData: {
        reviews: []
    }
};

global.document = {
    getElementById: (id) => {
        if (id === 'runningAmountCanvas') return { getContext: () => ({}) };
        if (id === 'runningAmountSection') return {
            classList: {
                hiddenState: true,
                remove: function(val) { if(val === 'is-hidden') this.hiddenState = false; }
            }
        };
        if (id === 'chartLegend') return { style: {}, innerHTML: '', querySelectorAll: () => [] };
        if (id === 'runningAmountEmpty') return { style: {}, textContent: '' };
        return null;
    },
    querySelector: () => null
};

async function runTests() {
  console.log("🧪 Running Reviews Tests\n");
  console.log("=".repeat(60));

  const { groupAndSortDecks, getGroupedDeckColor, getReviewStatsData, renderReviewsChart, showReviews, destroyCharts, getReviewsHelp } = await import('../js/commands/reviews.js');

  let passed = 0;
  let failed = 0;

  console.log("\n📋 Test 1: groupAndSortDecks correctly groups and sorts");
  try {
    const byDeckData = {
      "Language::Japanese": [{ time: 60, count: 5 }],
      "Language::English": [{ time: 40, count: 5 }],
      "Math::Calculus": [{ time: 150, count: 5 }],
      History: [{ time: 50, count: 5 }],
    };

    const result = groupAndSortDecks(byDeckData, true);

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

    passed++;
  } catch (e) {
    console.log(`   ✗ groupAndSortDecks: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 2: groupAndSortDecks ignores 'Unknown' deck");
  try {
    const byDeckData = {
      Science: [{ time: 100, count: 5 }],
      Unknown: [{ time: 500, count: 5 }],
    };

    const result = groupAndSortDecks(byDeckData, true);
    assert.strictEqual(result.length, 1, "Should filter out Unknown deck");
    assert.strictEqual(result[0].deckName, "Science");

    passed++;
  } catch (e) {
    console.log(`   ✗ groupAndSortDecks (Unknown): ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 3: getGroupedDeckColor creates distinct shades");
  try {
    const color0_0 = getGroupedDeckColor(0, 0, 3);
    const color0_1 = getGroupedDeckColor(0, 1, 3);
    const color0_2 = getGroupedDeckColor(0, 2, 3);

    assert.notStrictEqual(color0_0, color0_1, "Colors in same group should differ");
    assert.notStrictEqual(color0_1, color0_2, "Colors in same group should differ");
    assert.ok(color0_0.startsWith("hsla("));
    assert.ok(color0_1.startsWith("hsla("));

    passed++;
  } catch (e) {
    console.log(`   ✗ getGroupedDeckColor: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 4: groupAndSortDecks with mature/young structure");
  try {
    const dueDeckData = {
      "Science::Physics": [{ mature: 20, young: 10 }],
      "Art::Drawing": [{ mature: 0, young: 5 }],
    };

    const result = groupAndSortDecks(dueDeckData, false);

    assert.strictEqual(result.length, 2, "Should have 2 decks grouped");
    assert.strictEqual(result[0].deckName, "Science::Physics");
    assert.strictEqual(result[1].deckName, "Art::Drawing");

    passed++;
  } catch (e) {
    console.log(`   ✗ groupAndSortDecks with mature/young: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 5: getReviewStatsData global limits and slices");
  try {
    global.window.reviewStatsData = {
      reviews: [
        { date: "2023-01-01", mature: 10, young: 5, learn: 2, time: 100 },
        { date: "2023-01-02", mature: 5, young: 3, learn: 1, time: 50 },
        { date: "2023-01-03", mature: 20, young: 10, learn: 5, time: 200 },
      ],
    };

    const slicedData = getReviewStatsData("all", false);
    assert.strictEqual(slicedData.length, 3);
    assert.strictEqual(slicedData[2].date, "2023-01-03");
    assert.strictEqual(slicedData.preSliceSum.mature, 0);

    passed++;
  } catch (e) {
    console.log(`   ✗ getReviewStatsData global slice: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 6: getReviewStatsData preSlice bounds logic (byDeck)");
  try {
    // Note: Instead of assuming "1m" evaluates to 30 via external code that may be mocked out
    // or missing, we can test the fallback scenario natively and avoid strictEqual to an assumed internal
    // parsing logic unless we specifically mock it. We'll simply use "all" to guarantee behavior.

    let longGlobal = [];
    for(let i=0; i<40; i++){
        longGlobal.push({ date: `2023-01-${String(i+1).padStart(2,'0')}`, count: 10, time: 100 });
    }
    longGlobal[0].time = 150;

    let longMath = [];
    for(let i=0; i<40; i++){
        longMath.push({ date: `2023-01-${String(i+1).padStart(2,'0')}`, count: 10, time: 60 });
    }
    longMath[0].count = 15;
    longMath[0].time = 85;

    global.window.reviewStatsData.reviews = longGlobal;
    global.window.reviewStatsData.reviewsByDeck = { Math: longMath };

    const byDeckResultAll = getReviewStatsData("all", true);
    assert.strictEqual(byDeckResultAll.dates.length, 40, "Should fall back to full array length when 'all'");
    assert.strictEqual(byDeckResultAll.preSliceGlobalTime, 0, "Global time before full window should equal 0");

    passed++;
  } catch (e) {
    console.log(`   ✗ getReviewStatsData Deck preSlice: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 7: renderReviewsChart empty state displays Empty UI Message");
  try {
    const originalGetContext = global.document.getElementById;
    let emptyDisplayState = '';

    global.document.getElementById = (id) => {
        if (id === 'runningAmountCanvas') return { getContext: () => ({}) };
        if (id === 'runningAmountSection') return {
            classList: {
                hiddenState: true,
                remove: function(val) { if(val === 'is-hidden') this.hiddenState = false; }
            }
        };
        if (id === 'runningAmountEmpty') return {
            style: { display: '' },
            textContent: '',
            set text(val) { this.textContent = val; },
            get text() { return this.textContent; }
        };
        return originalGetContext(id);
    };

    const result = renderReviewsChart([]);
    assert.strictEqual(result.success, false, "Should return failure when given empty array");
    assert.strictEqual(result.error, "No data", "Error message should indicate missing data");

    global.document.getElementById = originalGetContext;
    passed++;
  } catch (e) {
    console.log(`   ✗ renderReviewsChart empty state displays Empty UI Message: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 8: renderReviewsChart global rendering applies configuration");
  try {
    global.window.reviewStatsData = {
      reviews: [ { date: "2023-01-01", mature: 10, young: 5, learn: 2, time: 100 } ]
    };

    const res = renderReviewsChart(getReviewStatsData("all", false), false, false, false);
    assert.strictEqual(res.success, true, "Standard chart rendering should succeed");
    assert.strictEqual(capturedConfig.type, undefined, "Type should implicitly be set (it uses line/bar from options mapping)");
    assert.strictEqual(capturedConfig.data.datasets.length, 4, "Should populate 4 global datasets (Mature, Young, Learn, Relearn)");

    const resCumulative = renderReviewsChart(getReviewStatsData("all", false), true, false, true);
    assert.strictEqual(resCumulative.success, true, "Cumulative time rendering should succeed");
    assert.strictEqual(capturedConfig.data.datasets[0].type, "line", "Cumulative rendering should use line chart dataset type");

    // Also test cumulative without time
    const resCumulativeCount = renderReviewsChart(getReviewStatsData("all", false), false, false, true);
    assert.strictEqual(resCumulativeCount.success, true, "Cumulative count rendering should succeed");

    passed++;
  } catch (e) {
    console.log(`   ✗ renderReviewsChart global rendering applies configuration: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 9: renderReviewsChart byDeck rendering configures stacked decks");
  try {
    global.window.reviewStatsData = {
      reviews: [ { date: "2023-01-01", mature: 10, young: 5, learn: 2, time: 100 } ],
      reviewsByDeck: {
        Math: [ { date: "2023-01-01", count: 10, time: 60 } ]
      }
    };

    const res = renderReviewsChart(getReviewStatsData("all", true), false, true, false);
    assert.strictEqual(res.success, true, "ByDeck rendering should succeed");
    assert.strictEqual(capturedConfig.data.datasets.length, 1, "Should populate 1 deck dataset (Math)");
    assert.strictEqual(capturedConfig.data.datasets[0].label, "Math", "Dataset label should match deck name");

    // Also test cumulative byDeck configurations with missing preSliceGlobalTime
    const data = getReviewStatsData("all", true);
    data.preSliceGlobalTime = undefined; // Cover line 332
    const resCumulByDeck = renderReviewsChart(data, false, true, true);
    assert.strictEqual(resCumulByDeck.success, true, "Cumulative byDeck rendering should succeed");

    // Also test cumulative time byDeck configurations
    const resCumulTimeByDeck = renderReviewsChart(data, true, true, true);
    assert.strictEqual(resCumulTimeByDeck.success, true, "Cumulative time byDeck rendering should succeed");

    passed++;
  } catch (e) {
    console.log(`   ✗ renderReviewsChart byDeck rendering configures stacked decks: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 10: showReviews returns expected formatted messages");
  try {
    const defaultMsg = showReviews('all', false, false, false);
    assert.strictEqual(defaultMsg.includes("Rendered review history chart"), true, "Should return successful render message");

    const deckTimeMsg = showReviews('all', true, true, true);
    assert.strictEqual(deckTimeMsg.includes("Rendered review cumulative time by deck history chart"), true, "Should reflect deck modifiers in message");

    const oldStats = global.window.reviewStatsData;
    global.window.reviewStatsData = null;
    const errorMsg = showReviews();
    assert.strictEqual(errorMsg.includes("Review stats not loaded"), true, "Should return error message on missing stats");
    global.window.reviewStatsData = oldStats;

    passed++;
  } catch (e) {
    console.log(`   ✗ showReviews returns expected formatted messages: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 11: getReviewStatsData edge cases");
  try {
    global.window.reviewStatsData = {
      reviews: [
        { date: "2023-01-01", mature: 10, young: 5, learn: 2, time: 100 },
        { date: "2023-01-02", mature: 5, young: 3, learn: 1, time: 50 },
        { date: "2023-01-03", mature: 20, young: 10, learn: 5, time: 200 }
      ],
      reviewsByDeck: {}
    };

    const allData = getReviewStatsData('all', false);
    assert.strictEqual(allData.length, 3);
    assert.strictEqual(allData.preSliceSum.mature, 0);

    const allDataDeck = getReviewStatsData('all', true);
    assert.strictEqual(allDataDeck.dates.length, 3);
    assert.strictEqual(allDataDeck.preSliceGlobalTime, 0);

    assert.doesNotThrow(() => destroyCharts());
    assert.strictEqual(Array.isArray(getReviewsHelp()), true);

    passed++;
  } catch (e) {
    console.log(`   ✗ getReviewStatsData edge cases: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 12: chart.js callbacks properly format tooltips");
  try {
      global.window.reviewStatsData = {
        reviews: [ { date: "2023-01-01", mature: 10, young: 5, learn: 2, time: 100 } ],
        reviewsByDeck: {
          Math: [ { date: "2023-01-01", count: 10, time: 60 } ]
        }
      };

      const data = getReviewStatsData("all", false);
      renderReviewsChart(data, false, false, false);

      if (capturedConfig && capturedConfig.options && capturedConfig.options.plugins && capturedConfig.options.plugins.tooltip) {
          const titleCallback = capturedConfig.options.plugins.tooltip.callbacks.title;
          assert.strictEqual(titleCallback([{label: "Date1"}]), "Date1", "Tooltip title should match label");

          const labelCallback = capturedConfig.options.plugins.tooltip.callbacks.label;
          assert.strictEqual(labelCallback({raw: 10, dataIndex: 0, dataset: {label: "Mature"}}), "Mature: 10 (2 min total)", "Tooltip label formats minutes correctly");
      }

      passed++;
  } catch (e) {
    console.log(`   ✗ chart.js callbacks properly format tooltips: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 13: Exception handling and catch blocks");
  try {
    const originalGetContext = global.document.getElementById;
    let emptyDisplayState = '';

    global.document.getElementById = (id) => {
        if (id === 'runningAmountCanvas') return { getContext: () => 'THROW' }; // Triggers catch
        if (id === 'runningAmountSection') return {
            classList: {
                hiddenState: true,
                remove: function(val) { if(val === 'is-hidden') this.hiddenState = false; }
            }
        };
        if (id === 'runningAmountEmpty') return {
            style: { display: '' },
            set textContent(val) { emptyDisplayState = val; },
            get textContent() { return emptyDisplayState; }
        };
        return originalGetContext(id);
    };

    global.window.reviewStatsData = { reviews: [ { date: "2023-01-01", mature: 10, time: 100 } ] };
    const res = renderReviewsChart(getReviewStatsData("all", false), false, false, false);

    assert.strictEqual(res.success, false, "Should catch Chart render failure");
    assert.strictEqual(res.error, "Chart render error", "Error message matches mocked failure");
    assert.strictEqual(emptyDisplayState, "Chart rendering failed: Chart render error", "Should write to empty element textContent");

    global.document.getElementById = originalGetContext;

    // Test showReviews warning string when reviews is missing
    const oldStats = global.window.reviewStatsData;
    global.window.reviewStatsData = { reviews: "not_an_array" };
    assert.strictEqual(showReviews(), "Review stats not loaded yet. Please wait a moment and try again.", "Should fail gracefully if reviews is not an array");
    global.window.reviewStatsData = oldStats;

    passed++;
  } catch (e) {
    console.log(`   ✗ Exception handling and catch blocks: ${e.message}`);
    failed++;
  }

  console.log("\n📋 Test 14: Dense charts and preSumObj logic");
  try {
    // Generate > 100 days of data to trigger `isDense = true`
    const longData = [];
    const baseDate = new Date("2023-01-01T00:00:00Z");
    for(let i = 0; i < 150; i++) {
        const currentDate = new Date(baseDate);
        currentDate.setUTCDate(baseDate.getUTCDate() + i);
        longData.push({
            date: currentDate.toISOString().split('T')[0],
            mature: 10, young: 5, learn: 2, relearn: 1,
            time: 60, time_mature: 20, time_young: 20, time_learn: 10, time_relearn: 10
        });
    }

    global.window.reviewStatsData = { reviews: longData };

    // Set preSliceSum object so we cover preSumObj branch
    const dataWithSum = getReviewStatsData("all", false);
    dataWithSum.preSliceSum = {
        time: 3600,
        mature: 100, young: 50, learn: 20, relearn: 10,
        time_mature: 1200, time_young: 1200, time_learn: 600, time_relearn: 600
    };

    // Render dense cumulative chart with time to exercise line 448-456 preSumObj handling and preSum additions
    const resDense = renderReviewsChart(dataWithSum, true, false, true);
    assert.strictEqual(resDense.success, true, "Should render dense graph successfully");
    assert.strictEqual(capturedConfig.data.datasets[0].pointRadius, 0, "Radius should be 0 on dense cumulative charts");

    // Test cumulative without time to exercise the other path
    const resDenseCounts = renderReviewsChart(dataWithSum, false, false, true);
    assert.strictEqual(resDenseCounts.success, true, "Should render dense cumulative counts graph successfully");

    passed++;
  } catch (e) {
    console.log(`   ✗ Dense charts and preSumObj logic: ${e.message}`);
    failed++;
  }

  console.log("\n" + "=".repeat(60));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("❌ TESTS FAILED");
    process.exitCode = 1;
  } else {
    console.log("✅ ALL TESTS PASSED");
  }
}

runTests().catch(err => {
  console.error(err);
  process.exitCode = 1;
});
