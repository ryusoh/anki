
const assert = require("assert");

// Mock the DOM environment
const defaultGetElementById = (id) => {
    const mockElement = {
        getContext: () => ({}),
        classList: { remove: () => {}, add: () => {}, contains: () => false },
        style: {},
        innerHTML: '',
        querySelectorAll: () => [],
        appendChild: () => {},
        getBoundingClientRect: () => ({ top: 0, bottom: 100, height: 100 }),
        clientHeight: 100,
        scrollTop: 0,
        scrollHeight: 0,
        dataset: {}
    };

    if (id === 'chartLegend') return { style: {}, innerHTML: '', querySelectorAll: () => [] };
    if (id === 'terminal') return mockElement;
    if (id === 'terminalOutput') return mockElement;
    if (id === 'mainContainer') return mockElement;
    if (id === 'helpModal') return mockElement;
    if (id === 'terminalSection') return mockElement;
    if (id === 'dateRanges') return mockElement;
    return mockElement;
};

global.document = {
  querySelector: () => null,
  getElementById: defaultGetElementById,
  querySelectorAll: () => []
};

global.window = {
  Chart: class {
    constructor(ctx, config) {
      this.config = config || {};
      this.data = this.config.data || { datasets: [] };
    }
    destroy() {}
    update() {}
  },
  innerWidth: 1024,
  customStatsData: { decks: [] },
  reviewStatsData: { reviews: [], reviewsByDeck: {} },
  setTimeout: setTimeout
};

global.gsap = {
  timeline: () => ({ to: function() { return this; }, call: function(fn) { if(fn) fn(); return this; } })
};

async function runTests() {
  const { renderReviewsChart, getReviewStatsData } = await import('../js/commands/reviews.js');
  const { handleCommand, clearCurrentChart } = await import('../js/commands/handler.js');
  const { toggleZoom } = await import('../js/commands/zoom.js');

  let passed = 0;
  let failed = 0;

  console.log("Handler Coverage Tests\n");
  console.log("=".repeat(60));

  const runTest = async (name, testFn) => {
    console.log(`\nTest: ${name}`);
    try {
      await testFn();
      console.log(`   PASS: ${name}`);
      passed++;
    } catch (e) {
      console.log(`   FAIL: ${e.message}`);
      failed++;
    }
  };

  await runTest("getReviewStatsData processes empty entries securely", async () => {
      global.window.reviewStatsData = {
          reviews: [{ date: "2023-01-01", count: 5, time: 10 }, { date: "2023-01-02", count: 5, time: 10 }],
          reviewsByDeck: {
              "Deck1": [{ date: "2023-01-01", count: 2, time: 5 }]
          }
      };
      const result = getReviewStatsData("1d", true);
      assert.ok(result.byDeck["Deck1"], "Deck1 should exist");
      assert.strictEqual(result.byDeck["Deck1"][0].count, 0, "Missing dates should be padded with 0 counts");
  });

  await runTest("renderReviewsChart correctly handles preSliceSum with fallback", async () => {
      const dataWithoutPreSum = [{ date: "2023-01-01", time_mature: 60, time_young: 60, time_learn: 60, time_relearn: 60, time: 240 }];
      Object.defineProperty(dataWithoutPreSum, 'preSliceSum', { get: () => undefined });
      const res = renderReviewsChart(dataWithoutPreSum, true, false, true);
      assert.strictEqual(res.success, true, "Should render chart successfully even without preSliceSum");
  });

  await runTest("clearCurrentChart forces unzoom if terminal is zoomed", async () => {
      await toggleZoom();
      let removedClass = false;
      global.document.getElementById = (id) => {
          return {
             getContext: () => ({}),
             classList: { remove: (cls) => { if(cls==='zoomed') removedClass=true; }, add: () => {}, contains: () => false },
             style: {}, innerHTML: '', querySelectorAll: () => [], dataset: {}
          };
      }
      clearCurrentChart();
      assert.strictEqual(removedClass, true, "Should have called classList.remove('zoomed') on the section element");
      global.document.getElementById = defaultGetElementById;
  });

  await runTest("Unknown and partial commands correctly error", async () => {
      const result1 = handleCommand("show reviews unknownrange", () => {});
      const result2 = handleCommand("reviews unknownrange", () => {});
      assert.strictEqual(result1.error, "invalid range", "Should throw invalid range error");
      assert.strictEqual(result2.error, "invalid range", "Should throw invalid range on shortcut toggles");
  });

  await runTest("Due shortcuts correctly switch current chart state", async () => {
      const resPd = handleCommand("pd", () => {});
      const resPdd = handleCommand("pdd", () => {});
      assert.strictEqual(resPd.command, "plot-due", "Shortcut 'pd' should trigger plot-due");
      assert.strictEqual(resPdd.command, "due-deck", "Shortcut 'pdd' should trigger due-deck");
  });

  console.log("\n" + "=".repeat(60));
  console.log(`\nResults: ${passed} passed, ${failed} failed\n`);

  if (failed > 0) {
    console.log("TESTS FAILED");
    process.exit(1);
  } else {
    console.log("ALL TESTS PASSED");
  }
}

runTests().catch(err => {
  console.error(err);
  process.exit(1);
});
